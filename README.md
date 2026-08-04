# Mini E-Commerce Backend

## 项目简介

Mini E-Commerce Backend 是一个基于 Django REST Framework 的轻量级电商后端系统，用于展示 Python 后端求职中常见的 API 设计、认证权限、数据库建模、库存一致性、Redis 缓存、Redis 锁、Celery 消息队列和 Docker 部署能力。

项目只提供后端 API，不包含前端页面。核心业务链路为：用户注册登录、浏览商品、加入购物车、从购物车创建订单、扣减库存、模拟支付、取消待支付订单并恢复库存。

## 技术栈

- Python 3.12
- Django 5.2
- Django REST Framework
- djangorestframework-simplejwt
- MySQL 8.0
- Redis 7
- Celery 5.6
- Gunicorn
- Nginx
- Docker Compose
- Django APITestCase

## 核心功能

- 用户注册、登录、刷新 Token、获取当前用户
- 自定义用户模型，支持 `user/admin` 业务角色
- 分类和商品管理
- 匿名商品列表与商品详情查询
- 管理员商品和分类 CRUD
- 商品详情 Redis 缓存
- 购物车添加、修改数量、删除、清空
- 从购物车创建订单
- 订单创建时事务扣减库存
- 订单创建时使用 Redis 锁防止重复提交
- 模拟支付订单
- 取消待支付订单并恢复库存
- Celery 自动取消超时未支付订单，并通过定时扫描补偿丢失消息
- Docker Compose 启动 Django、MySQL、Redis、Celery Worker、Celery Beat、Nginx

## 项目亮点

1. 使用 Django REST Framework 设计 RESTful API，完成用户、商品、购物车、订单核心业务链路。
2. 订单创建过程使用 `transaction.atomic` 与 `select_for_update` 实现库存扣减一致性，避免并发下单导致超卖。
3. 使用 Redis 缓存商品详情数据，降低数据库查询压力。
4. 使用 Redis 用户级短锁拦截短时间重复提交，降低重复创建订单的概率。
5. 订单提交后发送 Celery ETA 消息，消费者在事务中锁定订单并幂等取消；Celery Beat 定时补偿 MQ 故障期间的漏投订单。
6. 使用 Docker Compose 编排 Django、MySQL、Redis、Celery Worker、Celery Beat、Nginx，实现项目一键部署。

## 数据库模型说明

主要表：

- `accounts_user`：自定义用户表，扩展 `phone` 和 `role`
- `products_category`：商品分类
- `products_product`：商品、价格、库存、销量、上下架状态
- `carts_cartitem`：购物车项，约束同一用户同一商品唯一
- `orders_order`：订单主表，记录订单号、用户、金额、状态
- `orders_orderitem`：订单明细，保存商品名称和价格快照

订单和订单明细拆分后，可以支持一个订单包含多个商品；订单明细保存商品快照，可以避免商品后续改名或改价影响历史订单。

详细说明见 [docs/database.md](docs/database.md)。

## API 路由说明

认证：

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`

商品：

- `GET /api/categories/`
- `GET /api/products/`
- `GET /api/products/{id}/`
- `POST /api/admin/categories/`
- `PATCH /api/admin/categories/{id}/`
- `DELETE /api/admin/categories/{id}/`
- `POST /api/admin/products/`
- `PATCH /api/admin/products/{id}/`
- `DELETE /api/admin/products/{id}/`

购物车：

- `GET /api/cart/`
- `POST /api/cart/items/`
- `PATCH /api/cart/items/{id}/`
- `DELETE /api/cart/items/{id}/`
- `DELETE /api/cart/clear/`

订单：

- `GET /api/orders/`
- `POST /api/orders/`
- `GET /api/orders/{id}/`
- `POST /api/orders/{id}/pay/`
- `POST /api/orders/{id}/cancel/`

详细请求和响应见 [docs/api.md](docs/api.md)。

## 本地启动方式

复制环境变量：

```powershell
Copy-Item .env.example .env
```

本地非 Docker 运行时，将 `.env` 中服务地址改为：

```env
DB_HOST=127.0.0.1
REDIS_HOST=127.0.0.1
```

安装依赖并启动：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

另开两个 PowerShell 终端启动异步消费者和补偿调度器：

```powershell
celery -A config worker --loglevel=info --pool=solo
celery -A config beat --loglevel=info
```

Windows 本地 Worker 使用 `--pool=solo`；Docker 中运行在 Linux 容器内，使用 Compose 已配置的并发 Worker。

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/
```

## Docker 启动方式

```powershell
Copy-Item .env.example .env
docker compose up --build
```

启动后访问：

```text
http://127.0.0.1:8080/api/health/
http://127.0.0.1:8080/api/products/
```

常用命令：

```powershell
docker compose ps
docker compose logs -f web
docker compose exec web python manage.py createsuperuser
docker compose down
```

本项目默认将 Nginx 映射到本机 `8080`，避免 Windows 上常见的 80 端口占用或保留问题。

完整 Docker 操作流程、端口冲突处理和 Compose 配置解释见 [docs/docker.md](docs/docker.md)。订单超时取消资料分为：

- [消息队列入门设计文档](docs/order_timeout_mq_design.md)：概念、设计流程、关键代码和并发边界。
- [订单超时运行文档](docs/order_timeout.md)：配置、启动、观察和故障处理。

## 测试账号

普通用户可以通过注册接口创建：

```json
{
  "username": "testuser",
  "password": "Test123456",
  "password_confirm": "Test123456",
  "email": "test@example.com",
  "phone": "13800000000"
}
```

管理员账号可以通过 Django shell 创建：

```powershell
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.create_user(username="admin", password="Admin123456", role="admin", is_staff=True)
```

## 测试

项目测试命令：

```powershell
python manage.py test
```

测试环境会自动使用 SQLite 和本地内存缓存，避免本机没有 MySQL 或 Redis 时无法执行测试。Docker 和正式运行仍使用 MySQL 与 Redis。

## 面试讲解

这个项目重点讲三个问题：库存一致性、接口防重复提交和订单超时释放库存。创建订单时，服务层在 `transaction.atomic()` 中使用 `select_for_update()` 锁定商品行，检查库存后扣减库存、创建订单和订单明细，任何一步失败都会回滚。为了拦截用户重复点击，创建订单前使用 Redis `cache.add()` 加用户级短期锁。待支付订单在事务提交后发送 Celery ETA 消息；任务到期后再次锁定订单并重检状态，只有仍为 `pending` 且超过 `expires_at` 才取消并恢复库存，Celery Beat 负责漏消息补偿。

完整讲解稿和常见面试问题见 [docs/interview.md](docs/interview.md)。

## 可扩展方向

- 秒杀接口和并发压测
- Swagger / OpenAPI 文档
- 操作日志表
- 优惠券和订单金额计算
- 支付回调和支付流水表
- 商品列表缓存和热门商品缓存
- CI 测试流水线
