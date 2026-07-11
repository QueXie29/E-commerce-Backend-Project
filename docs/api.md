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
| 40100 | 未认证 |
| 40300 | 无权限 |
| 40400 | 资源不存在 |
| 40900 | 重复提交 |
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

### 登录

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

### 刷新 Token

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

```json
{
  "remark": "请尽快发货"
}
```

创建订单只购买购物车中 `selected=true` 的商品。服务层会：

- 使用 Redis 用户级锁防止重复提交
- 使用数据库事务包裹订单创建
- 使用 `select_for_update()` 锁定商品行
- 检查商品状态和库存
- 扣减库存并增加销量
- 创建订单和订单明细
- 删除对应购物车项

重复提交响应：

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

只有 `pending` 订单可以支付。

### 取消订单

`POST /api/orders/{id}/cancel/`

只有 `pending` 订单可以取消。取消时使用事务和商品行锁恢复库存，并回退销量。
