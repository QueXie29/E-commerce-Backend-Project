# 数据库设计

## 设计目标

数据库设计围绕真实电商交易链路展开，重点保证用户、商品、购物车、订单和订单明细之间的关系清晰，并为库存扣减一致性提供模型基础。

## 表关系概览

```text
accounts.User 1 --- N carts.CartItem
accounts.User 1 --- N orders.Order
products.Category 1 --- N products.Product
products.Product 1 --- N carts.CartItem
orders.Order 1 --- N orders.OrderItem
products.Product 1 --- N orders.OrderItem
```

## accounts.User

继承 `AbstractUser`。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| username | CharField | 用户名，唯一 |
| email | EmailField | 邮箱，可为空 |
| phone | CharField | 手机号，可为空 |
| role | CharField | `user/admin` |
| is_staff | BooleanField | Django 管理后台权限 |
| is_superuser | BooleanField | 超级管理员 |
| date_joined | DateTimeField | 注册时间 |

权限规则：

- `is_superuser=True` 拥有全部权限
- `role=admin` 可以管理商品和查看订单
- `role=user` 只能管理自己的购物车和订单

## products.Category

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| name | CharField | 分类名称，唯一 |
| slug | SlugField | URL 友好标识，唯一 |
| is_active | BooleanField | 是否启用 |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

索引：

- `slug` 唯一索引
- `is_active` 普通索引

## products.Product

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| category | ForeignKey | 所属分类 |
| name | CharField | 商品名称 |
| slug | SlugField | 商品标识，唯一 |
| description | TextField | 商品描述 |
| price | DecimalField | 价格 |
| stock | PositiveIntegerField | 库存 |
| sales_count | PositiveIntegerField | 销量 |
| status | CharField | `active/inactive` |
| image_url | URLField | 图片地址 |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

业务规则：

- 普通用户只能看到上架商品
- 下架商品不能加入购物车
- 库存不足不能下单
- 商品被更新、下架、扣库存或恢复库存时，删除商品详情缓存

## carts.CartItem

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| user | ForeignKey | 用户 |
| product | ForeignKey | 商品 |
| quantity | PositiveIntegerField | 数量 |
| selected | BooleanField | 是否选中 |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

约束：

- `unique_user_product_cart_item`：同一用户同一商品只能有一条购物车记录
- `cart_item_quantity_gte_1`：数量必须大于等于 1

购物车放 MySQL 的原因：

- 购物车是用户长期状态，不应该因为 Redis 缓存淘汰而丢失
- 需要支持跨设备登录后查看同一份购物车
- 后续可以和订单、商品做关联查询

## orders.Order

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| order_no | CharField | 订单号，唯一 |
| user | ForeignKey | 下单用户 |
| total_amount | DecimalField | 订单总金额 |
| status | CharField | `pending/paid/cancelled` |
| remark | CharField | 备注 |
| created_at | DateTimeField | 创建时间 |
| expires_at | DateTimeField | 固定的支付截止时间 |
| paid_at | DateTimeField | 支付时间 |
| cancelled_at | DateTimeField | 取消时间 |
| updated_at | DateTimeField | 更新时间 |

状态流转：

```text
pending -> paid
pending -> cancelled
```

禁止：

```text
paid -> cancelled
cancelled -> paid
cancelled -> pending
paid -> pending
```

## orders.OrderItem

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| order | ForeignKey | 所属订单 |
| product | ForeignKey | 商品 |
| product_name | CharField | 商品名称快照 |
| product_price | DecimalField | 商品价格快照 |
| quantity | PositiveIntegerField | 数量 |
| subtotal | DecimalField | 小计 |
| created_at | DateTimeField | 创建时间 |

保存商品快照的原因：

- 商品后续改名不会影响历史订单
- 商品后续改价不会影响历史订单金额
- 订单明细可以作为交易发生时的证据

## 库存一致性

创建订单时使用：

```python
with transaction.atomic():
    product = Product.objects.select_for_update().get(id=product_id)
```

关键点：

- `transaction.atomic()` 保证订单、订单明细、库存扣减、购物车删除要么全部成功，要么全部回滚
- `select_for_update()` 锁定商品行，避免并发请求同时扣减同一库存
- Redis 锁只用于防止同一用户重复提交，数据库事务和行锁才是库存一致性的最终保障
- 超时任务、支付和人工取消先锁定订单行再重检 `status`，保证同一订单只有一个状态迁移可以恢复库存

超时扫描使用 `(status, expires_at)` 联合索引定位已到期的 `pending` 订单。`expires_at` 存在 MySQL 中，消息只负责触发处理，不能代替订单状态和截止时间这个业务事实。

## Redis 设计

商品详情缓存：

```text
key: product:detail:{product_id}
ttl: 300 seconds
```

订单重复提交锁：

```text
key: lock:order:create:user:{user_id}
ttl: 10 seconds
```

释放锁前检查 value，避免误删其他请求创建的锁。
