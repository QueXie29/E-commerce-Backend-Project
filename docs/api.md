# API 文档

## 通用响应

成功：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

失败：

```json
{
  "code": 40001,
  "message": "商品库存不足",
  "data": null
}
```

分页：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 100,
    "next": null,
    "previous": null,
    "results": []
  }
}
```

常用错误码：

| code | 含义 |
|---|---|
| 0 | 成功 |
| 40000 | 请求参数错误 |
| 40001 | 库存不足 |
| 40002 | 商品已下架 |
| 40003 | 购物车为空 |
| 40004 | 订单状态不允许该操作 |
| 40005 | 订单已超时取消 |
| 40100 | 未认证 |
| 40300 | 无权限 |
| 40400 | 资源不存在 |
| 40900 | 重复提交 |
| 40901 | Idempotency-Key 请求内容冲突 |
| 50000 | 服务器内部错误 |

## 认证

### 注册

`POST /api/auth/register/`

```json
{
  "username": "testuser",
  "password": "Test123456",
  "password_confirm": "Test123456",
  "email": "test@example.com",
  "phone": "13800000000"
}
```

### 通用 JWT 登录

`POST /api/auth/login/`

```json
{
  "username": "testuser",
  "password": "Test123456"
}
```

返回：

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

### 通用 JWT 刷新 Token

`POST /api/auth/refresh/`

```json
{
  "refresh": "jwt_refresh_token"
}
```

### 当前用户

`GET /api/auth/me/`

Header：

```http
Authorization: Bearer <access_token>
```

上面的 `/api/auth/login/` 和 `/api/auth/refresh/` 会在 JSON 中返回 refresh token，适合命令行、移动端或其他能够安全保管令牌的客户端。Vue 浏览器前端使用下面的 Cookie + CSRF 接口；通用 JWT 接口继续保留，二者不要混用刷新流程。

## 浏览器认证：Cookie + CSRF 契约

浏览器认证采用以下分工：

- access token 由登录或刷新响应返回，前端只保存在 JavaScript 内存中
- refresh token 由服务端写入 HttpOnly Cookie，前端代码不能读取
- 调用受保护业务接口时仍使用 `Authorization: Bearer <access_token>`
- 浏览器登录、刷新和退出都是写操作，必须同时发送 CSRF Cookie 和 `X-CSRFToken` 请求头
- 浏览器请求需要携带 Cookie；同域部署和 Vite 开发代理均可使用 `credentials: same-origin`

### 1. 初始化 CSRF

`GET /api/auth/browser/csrf/`

该接口设置 `csrftoken` Cookie，并在响应数据中返回一个可用于请求头的 CSRF token：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "csrfToken": "csrf_token"
  }
}
```

Cookie 中的值与响应数据中的掩码 token 不要求文本相同，Django 都可以校验。当前 Vue 前端从 `csrftoken` Cookie 读取值；后续调用浏览器认证写接口时必须发送：

```http
Cookie: csrftoken=<csrf_token>
X-CSRFToken: <csrf_token>
```

如果缺少或无法通过 CSRF 校验，服务端返回 HTTP `403`。

### 2. 浏览器登录

`POST /api/auth/browser/login/`

请求必须带上上一节的 CSRF Cookie 和请求头，请求体与通用登录相同：

```json
{
  "username": "testuser",
  "password": "Test123456"
}
```

响应体只返回 access token，不会把 refresh token 暴露给 JavaScript：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access": "jwt_access_token"
  }
}
```

同时，响应通过 `Set-Cookie` 写入 refresh token。默认 Cookie 契约为：

```text
名称：refresh_token
HttpOnly：true
Secure：false（生产 HTTPS 环境应设为 true）
SameSite：Lax
Path：/api/auth/browser/
Max-Age：604800 秒
```

Cookie 名称、有效期、路径、`Secure` 和 `SameSite` 都可以通过环境变量调整。

### 3. 浏览器刷新

`POST /api/auth/browser/refresh/`

请求体可以为空对象，refresh token 不放在 JSON 中，而是由浏览器自动发送 HttpOnly Cookie：

```http
Cookie: refresh_token=<jwt_refresh_token>; csrftoken=<csrf_token>
X-CSRFToken: <csrf_token>
Content-Type: application/json
```

```json
{}
```

成功响应只包含新的 access token：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access": "new_jwt_access_token"
  }
}
```

默认 `JWT_ROTATE_REFRESH_TOKENS=False`，原 refresh Cookie 保持不变。开启轮换后，响应会写入新的 refresh Cookie；如果同时开启黑名单，旧 refresh token 会失效。Cookie 缺失、无效、过期或已进入黑名单时返回 HTTP `401`。

### 4. 浏览器退出

`POST /api/auth/browser/logout/`

请求体可以为空对象，并且同样需要 CSRF Cookie 与 `X-CSRFToken`。服务端会尽可能把 refresh token 加入黑名单，然后通过相同的 Cookie 路径删除它。接口是幂等的：Cookie 已过期、无效或已被注销时，仍会完成删除操作。

```json
{}
```

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

前端收到响应后还应清除内存中的 access token。退出后再次调用浏览器刷新接口会返回 `401`。

### 5. 浏览器会话恢复顺序

Vue 前端刷新页面后内存 access token 会丢失，恢复会话的顺序为：

1. 确保浏览器已有 `csrftoken`；没有时先调用 CSRF 初始化接口。
2. 调用浏览器刷新接口，让浏览器自动携带 HttpOnly refresh Cookie。
3. 将返回的 access token 保存在内存中。
4. 使用 Bearer access token 调用 `GET /api/auth/me/` 获取当前用户。

业务请求遇到 `401` 时，前端只发起一个并发共享的刷新请求，然后将失败请求重试一次，避免多个请求同时轮换 refresh token。

相关环境变量：

| 环境变量 | 默认值 | 作用 |
|---|---|---|
| `JWT_REFRESH_COOKIE_NAME` | `refresh_token` | refresh Cookie 名称 |
| `JWT_REFRESH_COOKIE_SECURE` | `False` | 是否只允许 HTTPS 传输；生产环境应设为 `True` |
| `JWT_REFRESH_COOKIE_SAMESITE` | `Lax` | Cookie SameSite 策略 |
| `JWT_REFRESH_COOKIE_MAX_AGE_SECONDS` | `604800` | Cookie 有效秒数 |
| `JWT_REFRESH_COOKIE_PATH` | `/api/auth/browser/` | Cookie 发送路径 |
| `CSRF_TRUSTED_ORIGINS` | 包含本地 `8080` 和 `5173` 地址 | Django 接受的浏览器来源 |

## 商品和分类

### 分类列表

`GET /api/categories/`

只返回启用分类。

### 商品列表

`GET /api/products/`

支持参数：

```text
page
page_size
category
keyword
min_price
max_price
ordering=-created_at|-price|-sales_count
```

匿名和普通用户只看到 `status=active` 且分类启用的商品。

### 商品详情

`GET /api/products/{id}/`

商品详情使用 Redis 缓存：

```text
key: product:detail:{id}
ttl: 300 seconds
```

### 管理员分类接口

```http
POST /api/admin/categories/
PATCH /api/admin/categories/{id}/
DELETE /api/admin/categories/{id}/
```

### 管理员商品接口

`POST /api/admin/products/`

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

```http
PATCH /api/admin/products/{id}/
DELETE /api/admin/products/{id}/
```

`DELETE` 商品会将商品下架，不做物理删除。

## 购物车

购物车接口都需要登录。

### 查看购物车

`GET /api/cart/`

### 添加购物车

`POST /api/cart/items/`

```json
{
  "product_id": 1,
  "quantity": 2
}
```

规则：

- 商品必须上架
- 数量必须大于等于 1
- 数量不能超过库存
- 同一用户同一商品只保留一条购物车记录，再次添加会累加数量

### 修改购物车项

`PATCH /api/cart/items/{id}/`

```json
{
  "quantity": 3,
  "selected": true
}
```

### 删除购物车项

`DELETE /api/cart/items/{id}/`

### 清空购物车

`DELETE /api/cart/clear/`

## 订单

订单接口都需要登录。

### 创建订单

`POST /api/orders/`

请求头必须携带一个新的订单提交幂等键：

```http
Idempotency-Key: 0d17cd55-4904-4ef2-b4a9-cce6e2066a12
```

幂等键长度为 1～64 个字符，只能包含字母、数字、点、下划线、冒号和短横线；服务端会统一转换为小写，避免 MySQL 与 SQLite 的大小写比较规则不同。每次新的下单意图使用新 key；网络超时或响应丢失后的同一次重试必须复用原 key。

```json
{
  "remark": "请尽快发货",
  "cart_signature": "12:8:2|15:11:1"
}
```

`cart_signature` 是可选的客户端结算意图签名。Vue 前端会根据当前勾选购物车项的“购物车项 ID、商品 ID、数量”生成稳定签名；同一次网络重试保持不变，勾选项或数量改变时随之改变。它会和备注一起进入服务端请求摘要，避免购物车已经变化时错误重放旧订单。未提供该字段的旧客户端仍保持兼容。

创建订单只购买购物车中 `selected=true` 的商品。服务层会：

- 使用 Redis 用户级锁防止重复提交
- 在订单表保存 `idempotency_key` 和请求摘要
- 使用 `(user_id, idempotency_key)` 数据库唯一约束保证成功订单身份唯一
- 使用数据库事务包裹订单创建
- 使用 `select_for_update()` 锁定商品行
- 检查商品状态和库存
- 扣减库存并增加销量
- 创建订单和订单明细
- 删除对应购物车项
- 写入固定的支付截止时间 `expires_at`
- 数据库提交后发送 Celery 超时任务

相同用户使用同一 key、相同备注和相同购物车签名重试时，接口返回同一个订单 ID，并增加响应头：

```http
Idempotency-Replayed: true
```

相同 key 对应不同 `remark` 时返回：

```json
{
  "code": 40901,
  "message": "Idempotency-Key 已用于其他订单请求",
  "data": null
}
```

请求仍在处理且 Redis 用户级锁被占用时返回：

```json
{
  "code": 40900,
  "message": "订单正在处理中，请勿重复提交",
  "data": null
}
```

### 订单列表

`GET /api/orders/`

支持：

```text
status=pending|paid|cancelled
page=1
page_size=10
```

普通用户只能查看自己的订单，管理员可查看所有订单。

### 订单详情

`GET /api/orders/{id}/`

### 模拟支付

`POST /api/orders/{id}/pay/`

只有未超过 `expires_at` 的 `pending` 订单可以支付。即使消息队列处理延迟，支付接口也会按数据库中的截止时间取消过期订单并返回 `40005`。

### 取消订单

`POST /api/orders/{id}/cancel/`

只有 `pending` 订单可以取消。取消时使用事务和商品行锁恢复库存，并回退销量。

订单到达 `expires_at` 后也会由 Celery Worker 自动执行同一条取消链路。消息重复投递、用户手动取消和支付请求都会先锁定订单行并重检状态，因此库存只恢复一次。
