# 订单超时取消设计

## 1. 目标与业务规则

待支付订单会先扣减库存。如果用户一直不支付，库存不能永久占用。本项目默认给新订单 30 分钟支付时间，截止时间写入 `orders_order.expires_at`。

核心规则：

- 只有 `status=pending` 且 `expires_at <= now` 的订单可被超时取消。
- 超时取消、人工取消和支付必须串行竞争同一条订单记录。
- 重复消息不能重复恢复库存。
- MySQL 保存订单状态和截止时间；消息队列只负责触发，不是业务事实来源。
- Broker 临时不可用不能让已提交订单永久失去超时处理机会。

## 2. 组件职责

| 组件 | 职责 |
|---|---|
| Django Web | 创建订单、写入 `expires_at`，事务提交后发布 ETA 消息 |
| MySQL | 保存订单状态、截止时间、订单明细和库存 |
| Redis DB 1 | Celery Broker；与默认缓存 DB 0 分离 |
| Celery Worker | 消费单个订单的超时取消任务 |
| Celery Beat | 每分钟触发一次漏消息补偿扫描 |

## 3. 完整调用链

```text
POST /api/orders/
  -> create_order_from_cart()
  -> transaction.atomic()
       -> 锁定商品行
       -> 扣库存、创建订单/明细
       -> 写入 expires_at
       -> 注册 transaction.on_commit()
  -> 数据库提交
  -> cancel_expired_order.apply_async(eta=expires_at)
  -> Redis Broker
  -> Celery Worker 到期消费
  -> expire_order(order_id)
       -> transaction.atomic()
       -> select_for_update() 锁定订单
       -> 重检 pending 和 expires_at
       -> 按商品 ID 顺序锁定商品
       -> 恢复库存、回退销量
       -> status = cancelled
```

投递放在 `transaction.on_commit()` 中，避免数据库回滚后队列里仍存在一个无效订单任务。

## 4. 并发与幂等

超时任务不直接执行无条件 `UPDATE`，而是先锁定订单行：

1. 支付先获得锁：订单变为 `paid`；超时任务随后看到终态并退出。
2. 超时任务先获得锁：到期订单变为 `cancelled` 并恢复库存；支付随后被拒绝。
3. 同一消息重复消费：第一条完成取消；后续任务看到 `cancelled` 后退出。
4. 用户与任务同时取消：只有先获得订单锁的一方执行库存恢复。

订单行锁保护“订单只能完成一次合法状态迁移”；商品行锁保护“库存恢复与订单取消在一个事务内完成”。消息队列本身不提供这两个数据库不变量。

支付接口也会检查 `expires_at`。这是为了覆盖 Worker 堵塞的窗口：已经过期但消息尚未消费的订单不能继续支付。

## 5. 为什么还有补偿扫描

数据库提交与 MQ 发布之间没有分布式事务：

```text
MySQL COMMIT 成功 -> Redis Broker 暂时不可用 -> ETA 消息发布失败
```

`schedule_order_timeout()` 会记录异常但不把已成功下单响应改成 500。Celery Beat 每分钟发送 `dispatch_expired_orders`，任务使用 `(status, expires_at)` 联合索引查询到期订单，再把每个订单重新入队。

因此系统允许“至少一次”投递，而消费者通过订单行锁和状态重检实现幂等。

## 6. 配置

```env
CELERY_BROKER_DB=1
ORDER_PAYMENT_TIMEOUT_SECONDS=1800
ORDER_TIMEOUT_SWEEP_INTERVAL_SECONDS=60
ORDER_TIMEOUT_SWEEP_BATCH_SIZE=200
```

- 修改支付时长只影响新订单；已创建订单使用自己已保存的 `expires_at`。
- 补偿扫描每批最多处理 200 个订单，下一轮继续处理剩余记录。
- Redis Broker 的 `visibility_timeout` 至少为支付时长加 10 分钟，且不低于 1 小时。

## 7. 启动与观察

Docker：

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f celery_worker celery_beat
```

Windows 本地开发：

```powershell
celery -A config worker --loglevel=info --pool=solo
celery -A config beat --loglevel=info
```

为了快速验收，可在 `.env` 临时设置：

```env
ORDER_PAYMENT_TIMEOUT_SECONDS=30
ORDER_TIMEOUT_SWEEP_INTERVAL_SECONDS=10
```

重启 `web`、`celery_worker`、`celery_beat` 后创建订单，30 秒后查询订单详情，应看到 `status=cancelled`，商品库存和销量已恢复。验收后恢复正式配置。

## 8. 故障边界

| 故障 | 当前行为 |
|---|---|
| 创建订单事务回滚 | 不发送消息 |
| 提交后 Broker 不可用 | 记录错误；Beat 后续补偿 |
| Worker 停机 | 消息保留或由补偿扫描重新入队 |
| 消息重复 | 状态重检后安全退出 |
| 消息提前执行 | 截止时间重检后安全退出 |
| Worker 堵塞导致过期支付 | 支付接口按 `expires_at` 取消并拒绝 |
| Beat 多实例 | 会产生重复消息，但消费者幂等；部署仍应只运行一个 Beat |

## 9. 关键文件

- `config/celery.py`：Celery 应用初始化与任务发现。
- `config/settings.py`：Broker、ETA 可见性时间和 Beat 周期配置。
- `apps/orders/models.py`：`expires_at` 与联合索引。
- `apps/orders/services.py`：事务后投递、支付截止校验和幂等取消。
- `apps/orders/tasks.py`：单订单消费者与补偿扫描任务。
- `docker-compose.yml`：Worker 和 Beat 服务。

## 10. 参考

- [Celery：Django 集成](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)
- [Celery：ETA 与 countdown](https://docs.celeryq.dev/en/stable/userguide/calling.html#eta-and-countdown)
- [Celery：Redis visibility timeout](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html#visibility-timeout)
