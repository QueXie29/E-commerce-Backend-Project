# Mini E-Commerce Backend System — Codex 项目生成规范

> 目标：使用 Codex 生成一个适合 Python 后端开发求职的 Django REST Framework 电商后端项目。项目需要覆盖用户认证、商品、购物车、订单、库存扣减、Redis 缓存、Redis 锁、Docker 部署、基础测试和面试讲解材料。

---

## 0. 给 Codex 的总指令

请严格按照本文档实现项目，不要自由扩展无关功能，不要生成前端页面。本项目是一个后端求职项目，重点是：

1. API 设计清晰；
2. 数据库表结构合理；
3. 订单和库存逻辑正确；
4. Redis 使用有明确业务场景；
5. Docker 可一键启动；
6. README 能支撑面试讲解。

实现时请按“第 12 节：Codex 开发顺序”逐步完成。每完成一个阶段，给出：

- 本阶段完成内容；
- 新增/修改文件；
- 如何运行或测试；
- 下一阶段建议。

不要一次性生成大量不可验证代码。优先保证项目可运行、接口可测试、逻辑可解释。

---

## 1. 项目定位

### 1.1 项目名称

`mini_ecommerce_backend`

### 1.2 一句话描述

基于 Django REST Framework 构建的轻量级电商后端系统，支持用户认证、商品管理、购物车、订单创建、库存扣减、Redis 缓存优化和 Docker 部署，重点模拟真实电商交易链路中的库存一致性与接口设计问题。

### 1.3 面向岗位

- Python 后端开发工程师；
- Django 后端开发工程师；
- 初级后端开发工程师；
- 后端实习 / 应届后端岗位。

### 1.4 项目目标

7 天内完成一个可写入简历、可用于面试讲解、可本地启动测试的后端项目。

项目必须体现以下知识点：

- Python 后端工程结构；
- Django + DRF；
- RESTful API；
- JWT 登录认证；
- MySQL 表设计；
- ORM 关联查询；
- 数据库事务；
- 库存扣减；
- Redis 缓存；
- Redis 分布式锁简化实现；
- Docker Compose 多服务编排；
- Nginx 反向代理；
- 项目 README 与面试表达。

---

## 2. 技术栈要求

### 2.1 后端

- Python 3.12+
- Django >= 5.2, < 6.0
- Django REST Framework >= 3.15, < 4.0
- djangorestframework-simplejwt >= 5.3, < 6.0
- django-cors-headers >= 4.4, < 5.0
- python-dotenv >= 1.0, < 2.0

### 2.2 数据库与缓存

- MySQL 8.x
- Redis 7.x
- mysqlclient 或 PyMySQL，优先使用 `mysqlclient`，如果 Windows 安装困难则使用 `PyMySQL`。

### 2.3 部署

- Docker
- Docker Compose
- Nginx
- Gunicorn

### 2.4 测试

- Django TestCase / APITestCase
- pytest 可选，不强制

---

## 3. 项目功能边界

### 3.1 必须实现

1. 用户注册、登录、刷新 Token、获取当前用户信息；
2. 商品分类；
3. 商品列表、商品详情；
4. 管理员商品 CRUD；
5. 购物车添加、修改数量、删除、清空；
6. 从购物车创建订单；
7. 订单列表、订单详情；
8. 模拟支付订单；
9. 取消待支付订单并恢复库存；
10. 商品详情 Redis 缓存；
11. 商品列表 Redis 缓存；
12. 创建订单时使用 Redis 锁防重复提交；
13. 创建订单时使用数据库事务保证库存扣减一致性；
14. Docker Compose 启动 Django、MySQL、Redis、Nginx；
15. README 提供启动方式、接口说明、项目亮点、面试讲解。

### 3.2 可选加分

1. 秒杀模拟接口；
2. 热门商品接口；
3. 操作日志表；
4. 自定义管理命令生成测试数据；
5. 单元测试覆盖核心订单逻辑；
6. Swagger / OpenAPI 文档。

### 3.3 不做的内容

不要实现以下内容：

- 前端页面；
- 真实支付；
- 第三方登录；
- 复杂优惠券；
- 物流系统；
- 微服务拆分；
- Kafka / RabbitMQ；
- 分库分表；
- Kubernetes。

---

## 4. 推荐目录结构

```text
mini_ecommerce_backend/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── Dockerfile
├── docker-compose.yml
├── nginx/
│   └── default.conf
├── scripts/
│   └── entrypoint.sh
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── __init__.py
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests.py
│   ├── products/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── tests.py
│   ├── carts/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests.py
│   ├── orders/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── tests.py
│   └── common/
│       ├── __init__.py
│       ├── exceptions.py
│       ├── permissions.py
│       ├── responses.py
│       ├── pagination.py
│       └── utils.py
└── docs/
    ├── api.md
    ├── database.md
    └── interview.md
```

要求：

- 所有业务 app 放在 `apps/` 目录下；
- 不允许把业务逻辑全部堆在 `views.py`；
- 订单创建、库存扣减、缓存处理尽量放到 `services.py`；
- 通用响应、分页、权限、异常处理放到 `apps/common/`。

---

## 5. 环境变量规范

创建 `.env.example`：

```env
DEBUG=True
SECRET_KEY=replace-me
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=mini_ecommerce
DB_USER=mini_ecommerce_user
DB_PASSWORD=mini_ecommerce_password
DB_HOST=mysql
DB_PORT=3306

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

本地非 Docker 开发时可将：

```env
DB_HOST=127.0.0.1
REDIS_HOST=127.0.0.1
```

---

## 6. 数据库模型设计

### 6.1 用户模型：`accounts.User`

必须使用自定义用户模型，避免后期扩展困难。

继承：

```python
AbstractUser
```

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| username | CharField | 用户名，唯一 |
| email | EmailField | 邮箱，可为空 |
| phone | CharField | 手机号，可为空 |
| role | CharField | user/admin |
| date_joined | DateTimeField | Django 默认 |
| is_active | BooleanField | Django 默认 |
| is_staff | BooleanField | Django 默认 |
| is_superuser | BooleanField | Django 默认 |

角色枚举：

```text
user: 普通用户
admin: 业务管理员
```

权限判断规则：

- 超级管理员拥有所有权限；
- `role=admin` 可管理商品和订单；
- `role=user` 只能管理自己的购物车和订单。

`settings.py` 中必须设置：

```python
AUTH_USER_MODEL = "accounts.User"
```

代码中引用用户模型时必须使用：

```python
from django.conf import settings
from django.contrib.auth import get_user_model
```

不要写死：

```python
from django.contrib.auth.models import User
```

---

### 6.2 商品分类模型：`products.Category`

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| name | CharField | 分类名称，唯一 |
| slug | SlugField | URL 友好标识，唯一 |
| is_active | BooleanField | 是否启用 |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

索引：

- `slug` 唯一索引；
- `is_active` 普通索引。

---

### 6.3 商品模型：`products.Product`

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| category | ForeignKey(Category) | 所属分类 |
| name | CharField | 商品名称 |
| slug | SlugField | 商品标识，唯一 |
| description | TextField | 商品描述 |
| price | DecimalField | 价格，max_digits=10, decimal_places=2 |
| stock | PositiveIntegerField | 库存 |
| sales_count | PositiveIntegerField | 销量，默认 0 |
| status | CharField | active/inactive |
| image_url | URLField | 商品图片地址，可为空 |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

状态枚举：

```text
active: 上架
inactive: 下架
```

索引：

- `slug` 唯一索引；
- `status` 普通索引；
- `category` 普通索引；
- `created_at` 普通索引。

业务规则：

- 普通用户只能查看 `status=active` 的商品；
- 管理员可以查看所有商品；
- 下架商品不能加入购物车；
- 库存小于等于 0 时不能下单。

---

### 6.4 购物车模型：`carts.CartItem`

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| user | ForeignKey(User) | 用户 |
| product | ForeignKey(Product) | 商品 |
| quantity | PositiveIntegerField | 数量 |
| selected | BooleanField | 是否选中，默认 True |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

约束：

- 同一个用户的同一个商品在购物车中只能有一条记录。

Django 约束：

```python
models.UniqueConstraint(fields=["user", "product"], name="unique_user_product_cart_item")
```

业务规则：

- `quantity >= 1`；
- 添加购物车时商品必须上架；
- 添加或更新数量时不能超过当前库存；
- 用户只能查看和修改自己的购物车。

---

### 6.5 订单模型：`orders.Order`

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| order_no | CharField | 订单号，唯一 |
| user | ForeignKey(User) | 下单用户 |
| total_amount | DecimalField | 订单总金额 |
| status | CharField | pending/paid/cancelled |
| remark | CharField | 备注，可为空 |
| created_at | DateTimeField | 创建时间 |
| paid_at | DateTimeField | 支付时间，可为空 |
| cancelled_at | DateTimeField | 取消时间，可为空 |
| updated_at | DateTimeField | 更新时间 |

状态枚举：

```text
pending: 待支付
paid: 已支付
cancelled: 已取消
```

索引：

- `order_no` 唯一索引；
- `user` 普通索引；
- `status` 普通索引；
- `created_at` 普通索引。

状态流转：

```text
pending -> paid
pending -> cancelled
```

禁止状态流转：

```text
paid -> cancelled
cancelled -> paid
cancelled -> pending
paid -> pending
```

---

### 6.6 订单明细模型：`orders.OrderItem`

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| order | ForeignKey(Order) | 所属订单 |
| product | ForeignKey(Product) | 商品 |
| product_name | CharField | 商品名称快照 |
| product_price | DecimalField | 下单时价格快照 |
| quantity | PositiveIntegerField | 数量 |
| subtotal | DecimalField | 小计 |
| created_at | DateTimeField | 创建时间 |

业务规则：

- 订单明细必须保存商品名称和价格快照；
- 即使商品后续改名或改价格，历史订单金额不变；
- `subtotal = product_price * quantity`。

---

### 6.7 操作日志模型：`common.OperationLog`（可选但建议实现）

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BigAutoField | 主键 |
| user | ForeignKey(User, null=True) | 操作用户 |
| action | CharField | 操作类型 |
| target_type | CharField | 目标类型 |
| target_id | CharField | 目标 ID |
| ip_address | GenericIPAddressField | IP |
| created_at | DateTimeField | 创建时间 |

可记录：

- 创建订单；
- 支付订单；
- 取消订单；
- 管理员修改商品；
- 库存扣减失败。

---

## 7. API 设计规范

### 7.1 通用响应格式

所有接口统一返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

失败响应：

```json
{
  "code": 40001,
  "message": "商品库存不足",
  "data": null
}
```

分页响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 100,
    "next": "http://127.0.0.1:8000/api/products/?page=2",
    "previous": null,
    "results": []
  }
}
```

### 7.2 错误码建议

| 错误码 | 含义 |
|---|---|
| 0 | 成功 |
| 40000 | 请求参数错误 |
| 40001 | 库存不足 |
| 40002 | 商品已下架 |
| 40003 | 购物车为空 |
| 40004 | 订单状态不允许该操作 |
| 40100 | 未认证 |
| 40300 | 无权限 |
| 40400 | 资源不存在 |
| 40900 | 重复提交 |
| 50000 | 服务器内部错误 |

---

## 8. API 路由清单

### 8.1 认证模块

#### 注册

```http
POST /api/auth/register/
```

请求体：

```json
{
  "username": "testuser",
  "password": "Test123456",
  "password_confirm": "Test123456",
  "email": "test@example.com",
  "phone": "13800000000"
}
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com"
  }
}
```

校验规则：

- username 必填且唯一；
- password 至少 8 位；
- password 与 password_confirm 必须一致。

#### 登录

```http
POST /api/auth/login/
```

请求体：

```json
{
  "username": "testuser",
  "password": "Test123456"
}
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access": "jwt_access_token",
    "refresh": "jwt_refresh_token"
  }
}
```

#### 刷新 Token

```http
POST /api/auth/refresh/
```

请求体：

```json
{
  "refresh": "jwt_refresh_token"
}
```

#### 当前用户信息

```http
GET /api/auth/me/
Authorization: Bearer <access_token>
```

---

### 8.2 分类模块

#### 分类列表

```http
GET /api/categories/
```

说明：普通用户只能看到启用分类。

#### 创建分类（管理员）

```http
POST /api/admin/categories/
Authorization: Bearer <admin_token>
```

#### 修改分类（管理员）

```http
PATCH /api/admin/categories/{id}/
Authorization: Bearer <admin_token>
```

#### 删除分类（管理员）

```http
DELETE /api/admin/categories/{id}/
Authorization: Bearer <admin_token>
```

---

### 8.3 商品模块

#### 商品列表

```http
GET /api/products/
```

支持查询参数：

```text
?page=1&page_size=10&category=1&keyword=iphone&ordering=-created_at
```

普通用户只返回：

```text
status=active
```

#### 商品详情

```http
GET /api/products/{id}/
```

要求：

- 详情接口使用 Redis 缓存；
- 缓存 key：`product:detail:{id}`；
- TTL：300 秒；
- 商品更新后删除该缓存。

#### 热门商品

```http
GET /api/products/hot/
```

排序规则：

```text
sales_count DESC, created_at DESC
```

#### 创建商品（管理员）

```http
POST /api/admin/products/
Authorization: Bearer <admin_token>
```

请求体：

```json
{
  "category": 1,
  "name": "MacBook Pro 14",
  "slug": "macbook-pro-14",
  "description": "Apple laptop",
  "price": "12999.00",
  "stock": 50,
  "status": "active",
  "image_url": "https://example.com/macbook.jpg"
}
```

#### 修改商品（管理员）

```http
PATCH /api/admin/products/{id}/
Authorization: Bearer <admin_token>
```

#### 删除商品（管理员）

```http
DELETE /api/admin/products/{id}/
Authorization: Bearer <admin_token>
```

建议逻辑：

- 不推荐物理删除商品；
- DELETE 可实现为下架，即 `status=inactive`。

---

### 8.4 购物车模块

所有购物车接口都需要登录。

#### 查看购物车

```http
GET /api/cart/
Authorization: Bearer <access_token>
```

响应示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "product": {
          "id": 10,
          "name": "MacBook Pro 14",
          "price": "12999.00",
          "stock": 50
        },
        "quantity": 2,
        "selected": true,
        "subtotal": "25998.00"
      }
    ],
    "total_amount": "25998.00"
  }
}
```

#### 添加购物车

```http
POST /api/cart/items/
Authorization: Bearer <access_token>
```

请求体：

```json
{
  "product_id": 10,
  "quantity": 2
}
```

规则：

- 如果该商品已在购物车，则增加数量；
- 最终数量不能超过库存；
- 商品必须上架。

#### 修改购物车数量

```http
PATCH /api/cart/items/{id}/
Authorization: Bearer <access_token>
```

请求体：

```json
{
  "quantity": 3,
  "selected": true
}
```

#### 删除购物车商品

```http
DELETE /api/cart/items/{id}/
Authorization: Bearer <access_token>
```

#### 清空购物车

```http
DELETE /api/cart/clear/
Authorization: Bearer <access_token>
```

---

### 8.5 订单模块

所有订单接口都需要登录。

#### 从购物车创建订单

```http
POST /api/orders/
Authorization: Bearer <access_token>
```

请求体：

```json
{
  "remark": "请尽快发货"
}
```

核心要求：

1. 只购买购物车中 `selected=true` 的商品；
2. 购物车不能为空；
3. 商品必须上架；
4. 库存必须充足；
5. 创建订单和扣减库存必须在同一个数据库事务中完成；
6. 使用 `select_for_update()` 锁定商品行，避免并发超卖；
7. 使用 Redis 锁防止用户重复点击提交订单；
8. 创建成功后清除对应购物车项；
9. 订单金额以数据库当前商品价格为准；
10. 订单明细保存商品名称和价格快照。

Redis 锁建议：

```text
key: lock:order:create:user:{user_id}
value: random_uuid
ttl: 10 seconds
```

可使用：

```python
cache.add(lock_key, lock_value, timeout=10)
```

如果加锁失败，返回：

```json
{
  "code": 40900,
  "message": "订单正在处理中，请勿重复提交",
  "data": null
}
```

伪代码：

```python
def create_order_from_cart(user, remark):
    lock_key = f"lock:order:create:user:{user.id}"
    lock_value = str(uuid.uuid4())

    if not cache.add(lock_key, lock_value, timeout=10):
        raise BusinessException("订单正在处理中，请勿重复提交", code=40900)

    try:
        with transaction.atomic():
            cart_items = CartItem.objects.select_related("product").filter(
                user=user,
                selected=True
            )

            if not cart_items.exists():
                raise BusinessException("购物车为空", code=40003)

            order = Order.objects.create(...)

            for item in cart_items:
                product = Product.objects.select_for_update().get(id=item.product_id)

                if product.status != Product.Status.ACTIVE:
                    raise BusinessException("商品已下架", code=40002)

                if product.stock < item.quantity:
                    raise BusinessException("商品库存不足", code=40001)

                product.stock -= item.quantity
                product.sales_count += item.quantity
                product.save(update_fields=["stock", "sales_count", "updated_at"])

                OrderItem.objects.create(...)

            order.total_amount = total_amount
            order.save(update_fields=["total_amount", "updated_at"])
            cart_items.delete()
            return order
    finally:
        if cache.get(lock_key) == lock_value:
            cache.delete(lock_key)
```

#### 订单列表

```http
GET /api/orders/
Authorization: Bearer <access_token>
```

普通用户：只看自己的订单。

管理员：可看所有订单。

支持参数：

```text
?status=pending&page=1&page_size=10
```

#### 订单详情

```http
GET /api/orders/{id}/
Authorization: Bearer <access_token>
```

权限：

- 普通用户只能看自己的订单；
- 管理员可看所有订单。

#### 模拟支付

```http
POST /api/orders/{id}/pay/
Authorization: Bearer <access_token>
```

规则：

- 只有 `pending` 订单可以支付；
- 支付后状态变为 `paid`；
- 设置 `paid_at`。

#### 取消订单

```http
POST /api/orders/{id}/cancel/
Authorization: Bearer <access_token>
```

规则：

- 只有 `pending` 订单可以取消；
- 取消后状态变为 `cancelled`；
- 设置 `cancelled_at`；
- 需要恢复库存；
- 恢复库存必须使用数据库事务；
- 已支付订单不能取消。

伪代码：

```python
with transaction.atomic():
    order = Order.objects.select_for_update().get(id=order_id)
    if order.status != Order.Status.PENDING:
        raise BusinessException("订单状态不允许取消", code=40004)

    for item in order.items.select_related("product"):
        product = Product.objects.select_for_update().get(id=item.product_id)
        product.stock += item.quantity
        product.sales_count = max(product.sales_count - item.quantity, 0)
        product.save(update_fields=["stock", "sales_count", "updated_at"])

    order.status = Order.Status.CANCELLED
    order.cancelled_at = timezone.now()
    order.save(update_fields=["status", "cancelled_at", "updated_at"])
```

---

### 8.6 秒杀模拟接口（加分）

```http
POST /api/orders/flash-buy/
Authorization: Bearer <access_token>
```

请求体：

```json
{
  "product_id": 10,
  "quantity": 1
}
```

要求：

- 不走购物车，直接购买单个商品；
- 使用 Redis 锁限制同一个商品的并发扣减；
- 最终库存扣减仍然以数据库事务和 `select_for_update()` 为准；
- Redis 锁只是削峰和防重复的辅助手段，数据库事务是最终一致性保障。

锁 key：

```text
lock:flash_buy:product:{product_id}
```

---

## 9. Redis 设计规范

### 9.1 商品详情缓存

缓存 key：

```text
product:detail:{product_id}
```

TTL：

```text
300 seconds
```

读流程：

```text
先查 Redis -> 命中直接返回 -> 未命中查 MySQL -> 写入 Redis -> 返回
```

写流程：

```text
商品更新/下架/删除 -> 删除 product:detail:{id} 缓存
```

### 9.2 商品列表缓存

缓存 key：

```text
product:list:{md5(query_params)}
```

TTL：

```text
120 seconds
```

说明：

- 商品列表缓存可选，但建议实现；
- 查询参数不同，缓存 key 不同；
- 商品被创建、修改、下架时，简单做法是删除所有商品列表缓存；
- 简化实现可以维护一个 key 集合：`product:list:keys`。

### 9.3 热门商品缓存

缓存 key：

```text
product:hot:list
```

TTL：

```text
300 seconds
```

### 9.4 订单重复提交锁

缓存 key：

```text
lock:order:create:user:{user_id}
```

TTL：

```text
10 seconds
```

要求：

- 加锁失败返回重复提交；
- 加锁成功后必须在 finally 中释放；
- 释放前检查 value，避免误删别人的锁。

### 9.5 秒杀商品锁

缓存 key：

```text
lock:flash_buy:product:{product_id}
```

TTL：

```text
5 seconds
```

---

## 10. DRF 实现要求

### 10.1 View 选择

推荐使用：

- ViewSet / ModelViewSet：商品、分类、订单；
- APIView：登录注册、当前用户、购物车聚合接口；
- `@action`：订单支付、取消、热门商品、秒杀。

### 10.2 Serializer 要求

必须区分：

- 列表 Serializer；
- 详情 Serializer；
- 创建 Serializer；
- 更新 Serializer。

示例：

```text
ProductListSerializer
ProductDetailSerializer
ProductCreateUpdateSerializer
OrderListSerializer
OrderDetailSerializer
OrderCreateSerializer
```

### 10.3 Permission 要求

实现：

```text
IsAdminOrReadOnly
IsOwnerOrAdmin
IsAdminRole
```

权限规则：

- 商品读取允许匿名；
- 商品写入只允许管理员；
- 购物车必须登录且只能操作自己的；
- 订单必须登录且只能看自己的，管理员除外。

### 10.4 Pagination 要求

默认分页：

```text
page_size = 10
max_page_size = 100
```

支持：

```text
?page=1&page_size=20
```

### 10.5 Filter / Search / Ordering

商品列表支持：

```text
category
keyword
min_price
max_price
ordering
```

排序字段：

```text
created_at
price
sales_count
```

---

## 11. 配置要求

### 11.1 `settings.py`

必须包含：

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.accounts",
    "apps.products",
    "apps.carts",
    "apps.orders",
]
```

中间件中加入：

```python
"corsheaders.middleware.CorsMiddleware"
```

REST Framework 配置：

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 10,
}
```

Redis 缓存配置：

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://redis:6379/0",
    }
}
```

数据库配置必须从环境变量读取。

---

## 12. Codex 开发顺序

请按以下顺序生成和提交代码。

### 阶段 1：初始化项目

目标：项目能启动。

任务：

1. 创建 Django 项目 `config`；
2. 创建 `apps` 目录；
3. 创建 `accounts/products/carts/orders/common` app；
4. 配置 `settings.py`；
5. 配置 `.env.example`；
6. 配置 `requirements.txt`；
7. 配置基础 URL 路由。

验收：

```bash
python manage.py check
```

通过。

---

### 阶段 2：用户认证模块

目标：完成注册、登录、当前用户。

任务：

1. 自定义 `User` 模型；
2. 配置 `AUTH_USER_MODEL`；
3. 创建注册 Serializer；
4. 使用 SimpleJWT 完成登录和刷新；
5. 实现 `/api/auth/me/`。

验收：

- 可以注册用户；
- 可以登录获取 access 和 refresh；
- 带 access token 可以获取当前用户。

---

### 阶段 3：商品模块

目标：完成分类和商品 CRUD。

任务：

1. 创建 `Category` 模型；
2. 创建 `Product` 模型；
3. 创建 Serializer；
4. 创建 ViewSet；
5. 匿名可查看商品；
6. 管理员可创建、修改、下架商品；
7. 实现商品详情缓存。

验收：

- 商品列表可访问；
- 商品详情可访问；
- 管理员可以创建商品；
- 普通用户不能创建商品；
- 商品详情第二次访问走缓存。

---

### 阶段 4：购物车模块

目标：完成购物车完整逻辑。

任务：

1. 创建 `CartItem` 模型；
2. 添加唯一约束；
3. 实现添加购物车；
4. 实现查看购物车；
5. 实现修改数量；
6. 实现删除商品；
7. 实现清空购物车。

验收：

- 不能添加下架商品；
- 数量不能超过库存；
- 同一用户同一商品不重复生成购物车记录；
- 用户只能操作自己的购物车。

---

### 阶段 5：订单模块

目标：完成订单创建、支付、取消。

任务：

1. 创建 `Order` 模型；
2. 创建 `OrderItem` 模型；
3. 实现订单号生成；
4. 实现从购物车创建订单；
5. 实现事务扣库存；
6. 实现 Redis 锁防重复提交；
7. 实现订单列表；
8. 实现订单详情；
9. 实现模拟支付；
10. 实现取消订单并恢复库存。

验收：

- 库存不足不能下单；
- 订单创建成功后库存减少；
- 订单创建成功后购物车对应项删除；
- 重复点击创建订单会被 Redis 锁拦截；
- 取消待支付订单会恢复库存；
- 已支付订单不能取消。

---

### 阶段 6：秒杀模拟接口（加分）

目标：实现单商品快速购买。

任务：

1. 创建 `/api/orders/flash-buy/`；
2. 校验商品状态和库存；
3. 使用 Redis 商品锁；
4. 使用数据库事务和行锁扣库存；
5. 创建订单和订单明细。

验收：

- 库存不足不能购买；
- 同一商品并发请求不会出现负库存；
- 创建成功后生成待支付订单。

---

### 阶段 7：Docker 部署

目标：一键启动项目。

任务：

1. 编写 `Dockerfile`；
2. 编写 `docker-compose.yml`；
3. 配置 MySQL 服务；
4. 配置 Redis 服务；
5. 配置 Django web 服务；
6. 配置 Nginx 反向代理；
7. 编写 `entrypoint.sh` 自动迁移；
8. README 写清楚启动步骤。

验收：

```bash
docker compose up --build
```

服务启动后：

```text
http://127.0.0.1/api/products/
```

可访问。

---

### 阶段 8：测试与文档

目标：项目可展示、可面试。

任务：

1. 编写核心 API 测试；
2. 编写订单库存测试；
3. 编写 `README.md`；
4. 编写 `docs/api.md`；
5. 编写 `docs/database.md`；
6. 编写 `docs/interview.md`。

验收：

```bash
python manage.py test
```

通过。

---

## 13. Docker 要求

### 13.1 `docker-compose.yml` 服务

必须包含：

```text
web
mysql
redis
nginx
```

### 13.2 服务说明

#### web

- Django 应用；
- 使用 Gunicorn 启动；
- 依赖 mysql 和 redis；
- 暴露内部端口 8000。

#### mysql

- 镜像：`mysql:8.0`
- 数据卷：`mysql_data`
- 环境变量：从 `.env` 读取。

#### redis

- 镜像：`redis:7-alpine`
- 数据卷可选。

#### nginx

- 监听 80；
- 反向代理到 web:8000。

### 13.3 Gunicorn 启动命令

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

### 13.4 entrypoint 行为

`entrypoint.sh` 需要执行：

```bash
python manage.py migrate
python manage.py collectstatic --noinput
exec "$@"
```

---

## 14. README 必须包含的内容

`README.md` 必须包含以下部分：

1. 项目简介；
2. 技术栈；
3. 核心功能；
4. 项目亮点；
5. 数据库模型说明；
6. API 路由说明；
7. 本地启动方式；
8. Docker 启动方式；
9. 测试账号；
10. 面试讲解；
11. 可扩展方向。

### 14.1 README 中的项目亮点写法

```text
1. 使用 Django REST Framework 设计 RESTful API，完成用户、商品、购物车、订单核心业务链路。
2. 订单创建过程使用 transaction.atomic 与 select_for_update 实现库存扣减一致性，避免并发下单导致超卖。
3. 使用 Redis 缓存商品详情与热门商品数据，降低数据库查询压力。
4. 使用 Redis 锁限制订单重复提交，提升接口幂等性与稳定性。
5. 使用 Docker Compose 编排 Django、MySQL、Redis、Nginx，实现项目一键部署。
```

---

## 15. 简历写法

项目名称：

```text
轻量级电商后端系统
```

简历描述：

```text
基于 Django REST Framework 开发轻量级电商后端系统，实现用户认证、商品管理、购物车、订单创建、库存扣减、模拟支付与订单取消等核心业务功能。项目使用 MySQL 进行关系型数据建模，使用 Redis 缓存商品热点数据并实现订单重复提交锁，通过数据库事务与行级锁保证库存扣减一致性，最终使用 Docker Compose 编排 Django、MySQL、Redis、Nginx 完成容器化部署。
```

项目亮点：

```text
- 使用 JWT 实现前后端分离认证，并基于角色区分普通用户与管理员权限。
- 设计商品、购物车、订单、订单明细等核心表结构，支持完整交易链路。
- 使用 transaction.atomic + select_for_update 处理订单创建和库存扣减，避免并发超卖。
- 使用 Redis 缓存商品详情和热门商品，提升查询性能。
- 使用 Redis 锁防止用户重复提交订单，增强接口幂等性。
- 使用 Docker Compose 完成 Django + MySQL + Redis + Nginx 一键部署。
```

---

## 16. 面试讲解稿

### 16.1 1 分钟版本

```text
我做的是一个轻量级电商后端系统，主要模拟真实电商中的用户、商品、购物车和订单交易流程。技术上使用 Django REST Framework 开发 API，使用 MySQL 存储业务数据，Redis 用于商品详情缓存和订单重复提交锁。项目中我重点处理了订单创建时的库存一致性问题，通过数据库事务和 select_for_update 行级锁保证扣库存和生成订单的一致性，避免并发情况下出现超卖。最后我使用 Docker Compose 编排 Django、MySQL、Redis 和 Nginx，实现项目一键启动和部署。
```

### 16.2 3 分钟版本

```text
这个项目是一个轻量级电商后端系统，业务链路包括用户注册登录、商品浏览、加入购物车、创建订单、库存扣减、模拟支付和取消订单。

在技术选型上，我使用 Django REST Framework 作为 API 框架，SimpleJWT 实现 JWT 登录认证，MySQL 存储用户、商品、购物车、订单和订单明细数据，Redis 负责商品缓存和订单重复提交锁，最后使用 Docker Compose 编排 Django、MySQL、Redis 和 Nginx。

这个项目中我重点关注两个后端常见问题。第一个是库存一致性。创建订单时，我没有简单地先查库存再扣库存，而是在 transaction.atomic 事务中使用 select_for_update 锁定商品行，检查库存充足后再扣减库存、创建订单和订单明细，保证这些操作要么全部成功，要么全部回滚。这样可以避免并发下单导致库存扣成负数。

第二个是接口幂等和重复提交问题。用户可能连续点击提交订单，所以我在创建订单接口前加了 Redis 锁，key 根据 user_id 生成，并设置较短过期时间。如果锁已存在，就返回重复提交提示。订单处理结束后再释放锁。

此外，我还给商品详情和热门商品接口加了 Redis 缓存，采用 Cache Aside 模式：先查缓存，未命中再查数据库并回写缓存；商品更新或下架时删除相关缓存，避免读到旧数据。

整体来说，这个项目虽然是轻量级项目，但覆盖了后端开发中常见的认证、权限、数据库建模、事务、缓存、接口设计和部署能力。
```

---

## 17. 必须准备的面试问题

### 17.1 Django / DRF

1. Django 和 DRF 的关系是什么？
2. Serializer 的作用是什么？
3. ViewSet 和 APIView 有什么区别？
4. DRF 的认证和权限流程是什么？
5. JWT 和 Session 有什么区别？

### 17.2 MySQL

1. 为什么订单和订单明细要拆成两张表？
2. 商品价格为什么要在订单明细中保存快照？
3. 什么是数据库事务？
4. `select_for_update()` 的作用是什么？
5. 如何避免库存超卖？

### 17.3 Redis

1. 为什么商品详情适合做缓存？
2. 什么是 Cache Aside Pattern？
3. 商品更新后如何保证缓存一致性？
4. Redis 锁如何防止重复提交？
5. Redis 锁有什么问题？如何优化？

### 17.4 项目设计

1. 为什么购物车数据放 MySQL，而不是全部放 Redis？
2. 创建订单为什么要使用事务？
3. 如果用户取消订单，库存如何恢复？
4. 如果支付成功后还能取消，会有什么问题？
5. 项目如何扩展优惠券、支付、物流？

---

## 18. 验收清单

项目完成后必须满足：

### 18.1 启动验收

```bash
python manage.py check
python manage.py migrate
python manage.py runserver
```

可成功运行。

Docker：

```bash
docker compose up --build
```

可成功运行。

### 18.2 API 验收

必须能完成以下流程：

1. 注册用户；
2. 登录获取 Token；
3. 管理员创建分类；
4. 管理员创建商品；
5. 普通用户查看商品列表；
6. 普通用户加入购物车；
7. 普通用户创建订单；
8. 创建订单后库存减少；
9. 创建订单后购物车清空；
10. 普通用户支付订单；
11. 普通用户取消待支付订单；
12. 取消订单后库存恢复；
13. 下架商品不能加入购物车；
14. 库存不足不能下单；
15. 非管理员不能创建商品。

### 18.3 代码质量验收

1. 没有把所有逻辑堆在 `views.py`；
2. 核心业务逻辑放在 `services.py`；
3. 所有金额使用 Decimal；
4. 不在代码中硬编码数据库密码；
5. 不直接写死 Django 默认 User；
6. 订单创建使用事务；
7. 库存扣减使用行级锁；
8. Redis 锁有过期时间；
9. 商品更新后有缓存失效逻辑；
10. README 能让别人启动项目。

---

## 19. Codex 最终执行提示词

将下面这段话发给 Codex：

```text
请读取并严格按照 `ecommerce_backend_codex_spec.md` 实现项目。

项目目标：生成一个可用于 Python 后端求职的 Django REST Framework 电商后端系统。

要求：
1. 不要生成前端页面，只生成后端 API；
2. 按文档中的阶段逐步实现，不要一次性乱生成；
3. 每个阶段完成后说明新增/修改的文件、运行命令、测试方法；
4. 重点保证订单创建、库存扣减、Redis 缓存、Redis 锁、Docker 部署正确；
5. 代码要能运行，不要只写伪代码；
6. 如果某个功能实现复杂，优先实现文档中的必须功能，可选功能放到最后；
7. 最终必须生成 README.md、docs/api.md、docs/database.md、docs/interview.md。

现在从“阶段 1：初始化项目”开始执行。
```

---

## 20. 技术依据参考

- Django 官方文档：https://docs.djangoproject.com/
- Django REST Framework 官方文档：https://www.django-rest-framework.org/
- Simple JWT 官方文档：https://django-rest-framework-simplejwt.readthedocs.io/
- Docker 官方文档：https://docs.docker.com/

