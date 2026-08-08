# Mini E-Commerce Backend：Apifox 双角色接口测试完整手册

> 适用项目：`D:\AI-learning\E-commerce Backend Project`  
> 角色：业务管理员 `admin`、普通用户 `user`  
> 推荐运行方式：Docker Compose，接口基础地址 `http://127.0.0.1:8080`  
> 文档依据：当前仓库的 URL、Serializer、View、Service 和自动化测试，核对日期为 2026-07-11。

## 1. 测试目标与当前 API 边界

本手册用于指导你在 Apifox 中手动完成以下链路：

```text
启动服务
  -> 注册管理员候选账号和普通用户
  -> 将管理员候选账号提升为 admin
  -> 分别登录并保存 JWT Token
  -> 管理员创建分类和商品
  -> 普通用户浏览商品
  -> 普通用户操作购物车
  -> 普通用户创建、查看、支付和取消订单
  -> 管理员查看全部订单和任意订单详情
  -> 验证普通用户越权失败
  -> 下架商品、停用分类
```

当前项目并不是所有资源都提供完全相同的 CRUD：

| 模块 | 当前支持的操作 |
|---|---|
| 认证 | 注册、登录、刷新 Token、获取当前用户 |
| 分类 | 管理员增删改查；匿名、普通用户可读取启用分类 |
| 商品 | 管理员增删改查；匿名、普通用户可读取上架商品 |
| 购物车 | 查看、添加、修改、删除单项、清空 |
| 订单 | 创建、列表、详情、支付、取消 |
| 订单通用修改/删除 | 不支持，`PUT/PATCH/DELETE /api/orders/{id}/` 返回 HTTP `405` |

分类和商品的 DELETE 都是软删除：

- 删除商品：将 `status` 改为 `inactive`，不物理删除数据库记录。
- 删除分类：将 `is_active` 改为 `false`，不物理删除数据库记录。

### 1.1 统一响应格式

成功响应：

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
    "count": 1,
    "next": null,
    "previous": null,
    "results": []
  }
}
```

测试时要区分：

- HTTP 状态码：例如 `200`、`201`、`400`、`401`、`403`、`404`、`405`、`409`。
- 业务状态码：响应 JSON 中的 `code`，成功通常为 `0`。

### 1.2 常用业务错误码

| 业务 code | 含义 | 常见场景 |
|---:|---|---|
| `0` | 成功 | 正常接口调用 |
| `40000` | 请求参数错误 | 缺少字段、字段格式错误、非法筛选值 |
| `40001` | 库存不足 | 加购物车或创建订单时数量超过库存 |
| `40002` | 商品已下架 | 将下架商品加入购物车或下单 |
| `40003` | 购物车为空 | 没有选中购物车项时创建订单 |
| `40004` | 订单状态不允许操作 | 重复支付、取消已支付订单 |
| `40100` | 未认证 | 没有 Token、Token 无效、登录失败 |
| `40300` | 无权限 | 普通用户调用管理员接口 |
| `40400` | 资源不存在 | ID 不存在或普通用户访问他人资源 |
| `40900` | 重复提交 | 订单创建锁已被占用 |
| `40901` | 幂等键冲突 | 相同 `Idempotency-Key` 被用于不同订单请求内容 |
| `50000` | 未单独映射的服务端/HTTP 异常 | 当前异常处理器处理 HTTP `405` 时可能出现 |

## 2. 启动项目并确认服务可用

### 2.1 推荐方式：Docker Compose

在 PowerShell 中进入项目目录：

```powershell
Set-Location 'D:\AI-learning\E-commerce Backend Project'
```

如果没有 `.env`，从模板复制：

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
```

启动服务：

```powershell
docker compose up -d --build
```

查看状态：

```powershell
docker compose ps
```

正常情况下，`mysql`、`redis`、`web`、`nginx` 应处于运行状态，健康检查最终应变成 `healthy`。

如果服务没有正常启动：

```powershell
docker compose logs --tail 100 web
docker compose logs --tail 100 mysql
docker compose logs --tail 100 redis
docker compose logs --tail 100 nginx
```

PowerShell 健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/api/health/
```

预期结果：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "ok"
  }
}
```

### 2.2 备选方式：本地 runserver

本地运行需要你已经准备好 MySQL 和 Redis，并把 `.env` 中的服务地址设为本机：

```env
DB_HOST=127.0.0.1
REDIS_HOST=127.0.0.1
```

启动命令：

```powershell
python manage.py migrate
python manage.py runserver
```

健康检查地址：

```text
http://127.0.0.1:8000/api/health/
```

后续文档默认使用 Docker 的 `8080`，如果你使用本地 runserver，只需要将 Apifox 的 `base_url` 改成 `http://127.0.0.1:8000`。

### 2.3 在 Apifox 中创建健康检查请求

1. 打开 Apifox，新建一个项目，例如“Mini E-Commerce Backend”。
2. 新建目录“00-健康检查”。
3. 新建 HTTP 请求，名称填写“健康检查”。
4. 方法选择 `GET`。
5. URL 暂时填写 `http://127.0.0.1:8080/api/health/`。
6. 不设置 Auth，不填写请求体。
7. 点击“发送”。
8. 确认 HTTP 状态码为 `200`，响应 JSON 的 `code` 为 `0`，`data.status` 为 `ok`。

服务健康后再继续后面的测试，否则认证和业务请求都会失败。

## 3. 创建 Apifox 环境与公共变量

### 3.1 创建环境

1. 点击 Apifox 右上角的“环境管理”。
2. 新建环境，名称填写“本地-Docker”。
3. 添加下表中的变量。
4. 密码和 Token 建议只填写“本地值”，不要填写团队共享的远程值。
5. 保存并在右上角选择“本地-Docker”作为当前环境。

### 3.2 环境变量表

以下示例中的 `20260711a` 是本轮测试标识。重复执行测试时，请换成新的标识，例如 `20260711b`，以避免用户名、分类 slug、商品 slug 的唯一约束冲突。

| 变量名 | 示例本地值 | 用途 |
|---|---|---|
| `base_url` | `http://127.0.0.1:8080` | 所有接口的公共地址 |
| `run_id` | `20260711a` | 标记本轮测试数据 |
| `admin_username` | `apifox_admin_20260711a` | 管理员用户名 |
| `admin_password` | `Admin123456` | 管理员密码 |
| `admin_access` | 留空 | 管理员 access Token |
| `admin_refresh` | 留空 | 管理员 refresh Token |
| `user_username` | `apifox_user_20260711a` | 普通用户名 |
| `user_password` | `User123456` | 普通用户密码 |
| `user_access` | 留空 | 普通用户 access Token |
| `user_refresh` | 留空 | 普通用户 refresh Token |
| `category_name` | `Apifox 数码分类 20260711a` | 分类名称 |
| `category_slug` | `apifox-digital-20260711a` | 唯一分类 slug |
| `category_id` | 留空 | 创建分类后提取 |
| `product_name` | `Apifox 测试手机 20260711a` | 商品名称 |
| `product_slug` | `apifox-phone-20260711a` | 唯一商品 slug |
| `product_id` | 留空 | 创建商品后提取 |
| `cart_item_id` | 留空 | 添加购物车后提取 |
| `paid_order_id` | 留空 | 将要支付的订单 ID |
| `cancelled_order_id` | 留空 | 将要取消的订单 ID |
| `pending_order_id` | 留空 | 保持待支付的订单 ID |
| `admin_order_id` | 留空 | 管理员自己的订单，用于用户隔离测试 |

不要将 `admin_username` 的值设置成 `apifox_admin_{{run_id}}`。为了减少嵌套变量解析问题，直接填写完整用户名；更换 `run_id` 时手动同步修改用户名和 slug。

### 3.3 在请求中引用变量

URL 示例：

```text
{{base_url}}/api/products/{{product_id}}/
```

字符串字段必须带双引号：

```json
{
  "username": "{{user_username}}"
}
```

整数 ID 和数量不要带双引号：

```json
{
  "product_id": {{product_id}},
  "quantity": 2
}
```

### 3.4 配置 JWT Bearer Token

受保护请求按以下方式设置：

1. 打开请求的“Auth/认证”标签。
2. 认证类型选择 `Bearer Token`。
3. 管理员请求的 Token 填写 `{{admin_access}}`。
4. 普通用户请求的 Token 填写 `{{user_access}}`。

Apifox 会自动生成：

```http
Authorization: Bearer <实际 access token>
```

不要同时在 Headers 中再手动添加另一条 Authorization，否则可能出现重复请求头。

### 3.5 配置断言

发送请求前可以在“后置操作”中添加断言：

1. 点击“添加后置操作”。
2. 选择“断言”。
3. HTTP 状态码断言：断言对象选择“响应状态码”，条件选择“等于”，期望值填写 `200` 或该步骤指定的状态码。
4. 业务码断言：断言对象选择“响应 JSON”，JSONPath 填写 `$.code`，条件选择“等于”，期望值填写 `0`。
5. 业务字段可以继续使用 `$.data.id`、`$.data.role`、`$.data.status` 等 JSONPath。

### 3.6 提取响应变量

例如将登录响应中的 access Token 保存为环境变量：

1. 打开登录请求的“后置操作”。
2. 点击“添加后置操作” -> “提取变量”。
3. 变量名填写 `user_access`。
4. 变量类型选择“环境变量”。
5. 提取来源选择“响应 JSON”。
6. JSONPath 填写 `$.data.access`。
7. 再添加一条提取规则，将 `$.data.refresh` 保存为 `user_refresh`。

你也可以使用本手册给出的后置 JavaScript 脚本。两种方式选择一种即可，不需要重复配置。

## 4. 准备管理员和普通用户

建议在 Apifox 中建立以下目录：

```text
00-健康检查
01-认证
02-管理员分类
03-管理员商品
04-公开分类和商品
05-普通用户购物车
06-普通用户订单
07-管理员订单
08-权限和异常
09-清理与软删除
```

### 4.1 注册管理员候选账号

注册接口不能提交 `role`，所以第一次注册得到的仍是普通用户，稍后再通过 Django Shell 提升角色。

请求：

```http
POST {{base_url}}/api/auth/register/
Content-Type: application/json
```

Auth：`No Auth`。

Body 选择 `raw` -> `JSON`：

```json
{
  "username": "{{admin_username}}",
  "password": "{{admin_password}}",
  "password_confirm": "{{admin_password}}",
  "email": "apifox-admin@example.com",
  "phone": "13800000001"
}
```

预期：

- HTTP 状态码：`201 Created`
- 业务码：`0`
- 此时 `data.role`：`user`
- 响应不返回密码

响应示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "username": "apifox_admin_20260711a",
    "email": "apifox-admin@example.com",
    "phone": "13800000001",
    "role": "user",
    "date_joined": "2026-07-11T10:00:00+08:00"
  }
}
```

### 4.2 注册普通用户

请求：

```http
POST {{base_url}}/api/auth/register/
Content-Type: application/json
```

Auth：`No Auth`。

请求体：

```json
{
  "username": "{{user_username}}",
  "password": "{{user_password}}",
  "password_confirm": "{{user_password}}",
  "email": "apifox-user@example.com",
  "phone": "13800000002"
}
```

预期：HTTP `201`、`code=0`、`data.role=user`。

### 4.3 将管理员候选账号提升为 admin

先在 Apifox 环境中确认 `admin_username` 的实际值，例如：

```text
apifox_admin_20260711a
```

Docker 运行方式在 PowerShell 中执行：

```powershell
docker compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); updated=User.objects.filter(username='apifox_admin_20260711a').update(role='admin', is_staff=True); print(f'updated={updated}')"
```

本地 runserver 方式执行：

```powershell
python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); updated=User.objects.filter(username='apifox_admin_20260711a').update(role='admin', is_staff=True); print(f'updated={updated}')"
```

预期输出：

```text
updated=1
```

如果输出 `updated=0`，说明命令中的用户名和注册时的用户名不一致。不要继续管理员接口测试，先修正用户名并重新执行。

## 5. 认证接口测试

### 5.1 管理员登录并保存 Token

请求：

```http
POST {{base_url}}/api/auth/login/
Content-Type: application/json
```

Auth：`No Auth`。

请求体：

```json
{
  "username": "{{admin_username}}",
  "password": "{{admin_password}}"
}
```

预期：HTTP `200`、`code=0`，`data.access` 和 `data.refresh` 都是非空字符串。

后置脚本：

```javascript
const body = pm.response.json();

pm.test("管理员登录 HTTP 状态码为 200", function () {
  pm.response.to.have.status(200);
});

pm.test("管理员登录业务码为 0", function () {
  pm.expect(body.code).to.eql(0);
});

pm.environment.set("admin_access", body.data.access);
pm.environment.set("admin_refresh", body.data.refresh);
```

发送后打开环境管理，确认 `admin_access` 和 `admin_refresh` 的本地值已经出现。

### 5.2 普通用户登录并保存 Token

请求：

```http
POST {{base_url}}/api/auth/login/
Content-Type: application/json
```

请求体：

```json
{
  "username": "{{user_username}}",
  "password": "{{user_password}}"
}
```

后置脚本：

```javascript
const body = pm.response.json();

pm.test("普通用户登录 HTTP 状态码为 200", function () {
  pm.response.to.have.status(200);
});

pm.test("普通用户登录业务码为 0", function () {
  pm.expect(body.code).to.eql(0);
});

pm.environment.set("user_access", body.data.access);
pm.environment.set("user_refresh", body.data.refresh);
```

### 5.3 查询管理员当前信息

请求：

```http
GET {{base_url}}/api/auth/me/
Authorization: Bearer {{admin_access}}
```

预期：

- HTTP `200`
- `code=0`
- `data.username={{admin_username}}` 对应的实际用户名
- `data.role=admin`

如果这里仍然返回 `role=user`，说明管理员提升命令没有更新到正确用户，或者登录 Token 是提升前签发但用户查询本身仍应读取数据库最新角色；请重新核对用户名和数据库记录。

### 5.4 查询普通用户当前信息

请求：

```http
GET {{base_url}}/api/auth/me/
Authorization: Bearer {{user_access}}
```

预期：HTTP `200`、`code=0`、`data.role=user`。

### 5.5 刷新管理员 access Token

请求：

```http
POST {{base_url}}/api/auth/refresh/
Content-Type: application/json
```

Auth：`No Auth`。

请求体：

```json
{
  "refresh": "{{admin_refresh}}"
}
```

后置脚本：

```javascript
const body = pm.response.json();

pm.test("管理员刷新 Token 成功", function () {
  pm.response.to.have.status(200);
  pm.expect(body.code).to.eql(0);
  pm.expect(body.data.access).to.be.a("string").and.not.empty;
});

pm.environment.set("admin_access", body.data.access);
```

普通用户刷新方式相同，将 `admin_refresh/admin_access` 换成 `user_refresh/user_access`。

当前配置中 access Token 默认有效期为 60 分钟，refresh Token 默认有效期为 7 天。

### 5.6 认证负向测试

#### 错误密码

```http
POST {{base_url}}/api/auth/login/
```

```json
{
  "username": "{{user_username}}",
  "password": "WrongPassword123"
}
```

预期：HTTP `401`、业务码 `40100`、提示“用户名或密码错误”。

#### 重复用户名注册

再次发送 4.2 的普通用户注册请求。

预期：HTTP `400`、业务码 `40000`，响应数据中包含用户名已存在的校验错误。

#### 两次密码不一致

```json
{
  "username": "password_mismatch_{{run_id}}",
  "password": "User123456",
  "password_confirm": "User654321"
}
```

预期：HTTP `400`、业务码 `40000`，错误字段与 `password_confirm` 有关。

#### 不带 Token 查询当前用户

调用 `GET {{base_url}}/api/auth/me/`，Auth 选择 `No Auth`。

预期：HTTP `401`、业务码 `40100`。

#### 使用无效 Token

Bearer Token 临时填写：

```text
invalid-token
```

预期：HTTP `401`、业务码 `40100`。测试后恢复为正确变量。

## 6. 分类接口测试

分类管理接口都使用管理员 Token：

```text
Bearer {{admin_access}}
```

### 6.1 管理员查看分类列表

```http
GET {{base_url}}/api/admin/categories/?page=1&page_size=10
Authorization: Bearer {{admin_access}}
```

预期：HTTP `200`、`code=0`，列表位于 `data.results`。

### 6.2 管理员创建分类并保存 category_id

```http
POST {{base_url}}/api/admin/categories/
Authorization: Bearer {{admin_access}}
Content-Type: application/json
```

```json
{
  "name": "{{category_name}}",
  "slug": "{{category_slug}}",
  "is_active": true
}
```

预期：HTTP `201`、`code=0`、`data.id` 大于 `0`、`data.is_active=true`。

后置脚本：

```javascript
const body = pm.response.json();

pm.test("分类创建成功", function () {
  pm.response.to.have.status(201);
  pm.expect(body.code).to.eql(0);
  pm.expect(body.data.id).to.be.above(0);
});

pm.environment.set("category_id", String(body.data.id));
```

发送后确认环境变量 `category_id` 已保存。

### 6.3 管理员查看分类详情

```http
GET {{base_url}}/api/admin/categories/{{category_id}}/
Authorization: Bearer {{admin_access}}
```

预期：HTTP `200`、`code=0`、`data.id={{category_id}}`。

### 6.4 管理员完整更新分类（PUT）

PUT 必须提交所有可写字段：

```http
PUT {{base_url}}/api/admin/categories/{{category_id}}/
Authorization: Bearer {{admin_access}}
Content-Type: application/json
```

```json
{
  "name": "Apifox 数码与手机 {{run_id}}",
  "slug": "{{category_slug}}",
  "is_active": true
}
```

预期：HTTP `200`、`code=0`，名称变为本轮测试对应的“Apifox 数码与手机”。

### 6.5 管理员部分更新分类（PATCH）

```http
PATCH {{base_url}}/api/admin/categories/{{category_id}}/
Authorization: Bearer {{admin_access}}
Content-Type: application/json
```

```json
{
  "name": "Apifox 数码分类最终名称 {{run_id}}"
}
```

预期：HTTP `200`、`code=0`，没有提交的 `slug` 和 `is_active` 保持不变。

### 6.6 公开查看启用分类

```http
GET {{base_url}}/api/categories/?page=1&page_size=10
```

Auth：`No Auth`。

预期：HTTP `200`，新分类出现在 `data.results` 中。

公开分类详情：

```http
GET {{base_url}}/api/categories/{{category_id}}/
```

预期：HTTP `200`，前提是分类仍为启用状态。

### 6.7 普通用户创建分类应失败

复制“管理员创建分类”请求，改用：

```text
Bearer {{user_access}}
```

为避免唯一约束影响权限测试，请将请求体改成尚不存在的值：

```json
{
  "name": "普通用户无权创建的分类 {{run_id}}",
  "slug": "user-forbidden-category-{{run_id}}",
  "is_active": true
}
```

预期：HTTP `403`、业务码 `40300`。权限检查发生在创建之前，数据库中不会生成该分类。

### 6.8 暂时不要删除分类

分类 DELETE 会把分类设为停用。商品创建校验要求分类处于启用状态，因此分类删除必须放在商品、购物车和订单测试全部结束之后，见第 11 节。

## 7. 商品接口测试

### 7.1 管理员创建商品并保存 product_id

```http
POST {{base_url}}/api/admin/products/
Authorization: Bearer {{admin_access}}
Content-Type: application/json
```

```json
{
  "category": {{category_id}},
  "name": "{{product_name}}",
  "slug": "{{product_slug}}",
  "description": "用于管理员、普通用户、购物车和订单接口联调",
  "price": "1999.00",
  "stock": 30,
  "status": "active",
  "image_url": "https://example.com/apifox-phone.jpg"
}
```

预期：HTTP `201`、`code=0`、`data.stock=30`、`data.status=active`。

后置脚本：

```javascript
const body = pm.response.json();

pm.test("商品创建成功", function () {
  pm.response.to.have.status(201);
  pm.expect(body.code).to.eql(0);
  pm.expect(body.data.id).to.be.above(0);
});

pm.environment.set("product_id", String(body.data.id));
```

### 7.2 管理员查看商品列表

```http
GET {{base_url}}/api/admin/products/?page=1&page_size=10
Authorization: Bearer {{admin_access}}
```

预期：HTTP `200`，商品位于 `data.results`。

### 7.3 管理员查看商品详情

```http
GET {{base_url}}/api/admin/products/{{product_id}}/
Authorization: Bearer {{admin_access}}
```

预期：HTTP `200`，详情包含 `description`、`updated_at` 和嵌套的 `category`。

### 7.4 管理员完整更新商品（PUT）

PUT 必须提交所有可写字段：

```http
PUT {{base_url}}/api/admin/products/{{product_id}}/
Authorization: Bearer {{admin_access}}
Content-Type: application/json
```

```json
{
  "category": {{category_id}},
  "name": "Apifox 测试手机 Pro {{run_id}}",
  "slug": "{{product_slug}}",
  "description": "PUT 完整更新后的商品描述",
  "price": "2099.00",
  "stock": 30,
  "status": "active",
  "image_url": "https://example.com/apifox-phone-pro.jpg"
}
```

预期：HTTP `200`、`code=0`、`data.price="2099.00"`。

### 7.5 管理员部分更新商品（PATCH）

```http
PATCH {{base_url}}/api/admin/products/{{product_id}}/
Authorization: Bearer {{admin_access}}
Content-Type: application/json
```

```json
{
  "price": "1999.00",
  "stock": 30
}
```

预期：HTTP `200`，只修改价格和库存。

### 7.6 匿名查看商品列表

```http
GET {{base_url}}/api/products/?page=1&page_size=10
```

Auth：`No Auth`。

预期：HTTP `200`，刚创建的上架商品出现在 `data.results`。普通用户和匿名用户只能看到：

```text
商品 status=active
并且分类 is_active=true
```

### 7.7 匿名查看商品详情

```http
GET {{base_url}}/api/products/{{product_id}}/
```

预期：HTTP `200`，响应包含完整详情。该接口会使用 Redis 商品详情缓存，缓存 TTL 为 300 秒；管理员修改或下架商品时会删除对应缓存。

### 7.8 商品筛选、搜索、排序和分页

在 Apifox 的 Params 标签逐项添加：

| 参数 | 值 |
|---|---|
| `category` | `{{category_id}}` |
| `keyword` | `Apifox` |
| `min_price` | `1000` |
| `max_price` | `3000` |
| `ordering` | `-price` |
| `page` | `1` |
| `page_size` | `10` |

最终请求等价于：

```http
GET {{base_url}}/api/products/?category={{category_id}}&keyword=Apifox&min_price=1000&max_price=3000&ordering=-price&page=1&page_size=10
```

允许的 ordering：

```text
created_at
-created_at
price
-price
sales_count
-sales_count
```

预期：HTTP `200`，匹配商品位于 `data.results`。

### 7.9 普通用户创建商品应失败

复制管理员创建商品请求，改用 `Bearer {{user_access}}`，同时换一个未使用的 slug：

```json
{
  "category": {{category_id}},
  "name": "普通用户无权创建的商品 {{run_id}}",
  "slug": "user-forbidden-product-{{run_id}}",
  "description": "权限负向测试",
  "price": "100.00",
  "stock": 1,
  "status": "active",
  "image_url": ""
}
```

预期：HTTP `403`、业务码 `40300`。

### 7.10 商品参数负向测试

#### 价格为 0

管理员创建或修改商品时提交：

```json
{
  "price": "0.00"
}
```

使用 PATCH 测试即可。预期：HTTP `400`、业务码 `40000`，提示商品价格必须大于 `0`。

#### 分类 ID 不是整数

```http
GET {{base_url}}/api/products/?category=abc
```

预期：HTTP `400`、业务码 `40000`，提示分类 ID 必须是整数。

#### 最低价格不是数字

```http
GET {{base_url}}/api/products/?min_price=abc
```

预期：HTTP `400`、业务码 `40000`，提示价格必须是合法数字。

### 7.11 暂时不要删除商品

商品下架后不能加入购物车和创建订单，所以商品 DELETE 放在所有购物车和订单测试结束后，见第 11 节。

## 8. 购物车接口测试

购物车接口全部要求登录。本节默认使用普通用户：

```text
Bearer {{user_access}}
```

每个用户只能访问自己的购物车项。管理员虽然也可以使用购物车，但管理员和普通用户的购物车数据互相隔离。

### 8.1 测试前清空普通用户购物车

```http
DELETE {{base_url}}/api/cart/clear/
Authorization: Bearer {{user_access}}
```

预期：HTTP `200`、`code=0`、`data=null`。

该操作可以重复执行，即使购物车原本为空也返回成功。

### 8.2 查看空购物车

```http
GET {{base_url}}/api/cart/
Authorization: Bearer {{user_access}}
```

预期响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [],
    "total_amount": "0.00"
  }
}
```

### 8.3 首次添加商品并保存 cart_item_id

```http
POST {{base_url}}/api/cart/items/
Authorization: Bearer {{user_access}}
Content-Type: application/json
```

```json
{
  "product_id": {{product_id}},
  "quantity": 2
}
```

预期：

- HTTP `201 Created`
- `code=0`
- `data.quantity=2`
- `data.selected=true`
- `data.subtotal="3998.00"`，前提是商品单价为 `1999.00`

后置脚本：

```javascript
const body = pm.response.json();

pm.test("首次添加购物车返回 201", function () {
  pm.response.to.have.status(201);
  pm.expect(body.code).to.eql(0);
  pm.expect(body.data.quantity).to.eql(2);
});

pm.environment.set("cart_item_id", String(body.data.id));
```

### 8.4 再次添加同一商品，验证数量累加

再次发送：

```json
{
  "product_id": {{product_id}},
  "quantity": 1
}
```

预期：

- HTTP `200 OK`，不是 `201`
- 返回的购物车项 ID 与 `cart_item_id` 相同
- `data.quantity=3`
- 数据库中同一用户、同一商品仍然只有一条购物车项

这是因为当前项目使用 `(user, product)` 唯一约束，再次添加时会累加数量。

### 8.5 修改购物车数量和选中状态

```http
PATCH {{base_url}}/api/cart/items/{{cart_item_id}}/
Authorization: Bearer {{user_access}}
Content-Type: application/json
```

```json
{
  "quantity": 2,
  "selected": true
}
```

预期：HTTP `200`、`data.quantity=2`、`data.selected=true`。

只修改选中状态也可以：

```json
{
  "selected": false
}
```

再次 GET 购物车时，未选中商品仍在 `items` 中，但不会计入 `total_amount`。完成验证后再 PATCH 回：

```json
{
  "selected": true
}
```

### 8.6 查看购物车金额

```http
GET {{base_url}}/api/cart/
Authorization: Bearer {{user_access}}
```

当数量为 `2`、单价为 `1999.00`、`selected=true` 时，预期：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "product": {
          "id": 1,
          "name": "Apifox 测试手机 Pro 20260711a",
          "price": "1999.00",
          "stock": 30,
          "status": "active",
          "image_url": "https://example.com/apifox-phone-pro.jpg"
        },
        "quantity": 2,
        "selected": true,
        "subtotal": "3998.00",
        "created_at": "2026-07-11T10:10:00+08:00",
        "updated_at": "2026-07-11T10:11:00+08:00"
      }
    ],
    "total_amount": "3998.00"
  }
}
```

示例中的 ID 和时间以你的实际响应为准。

### 8.7 删除单个购物车项

```http
DELETE {{base_url}}/api/cart/items/{{cart_item_id}}/
Authorization: Bearer {{user_access}}
```

预期：HTTP `200`、`code=0`、`data=null`。

删除后再次 GET 购物车，预期 `items=[]`。

### 8.8 清空购物车

先重新添加商品，再调用：

```http
DELETE {{base_url}}/api/cart/clear/
Authorization: Bearer {{user_access}}
```

预期：HTTP `200`，之后购物车为空。

### 8.9 购物车负向测试

#### 不带 Token

调用 `GET /api/cart/` 或 `POST /api/cart/items/`，Auth 选择 `No Auth`。

预期：HTTP `401`、业务码 `40100`。

#### 数量为 0

```json
{
  "product_id": {{product_id}},
  "quantity": 0
}
```

预期：HTTP `400`、业务码 `40000`，数量最小值校验失败。

#### 数量超过库存

当前商品库存是 `30` 左右时提交：

```json
{
  "product_id": {{product_id}},
  "quantity": 999
}
```

预期：HTTP `400`、业务码 `40001`、提示“商品库存不足”。

#### PATCH 不提交可修改字段

```json
{}
```

预期：HTTP `400`、业务码 `40000`、提示至少提交一个可修改字段。

#### 访问不存在的购物车项

```http
PATCH {{base_url}}/api/cart/items/99999999/
Authorization: Bearer {{user_access}}
```

```json
{
  "quantity": 1
}
```

预期：HTTP `404`、业务码 `40400`。

下架商品加入购物车的测试放到第 11 节，避免提前破坏订单测试数据。

## 9. 订单与订单详情测试

订单创建只购买当前用户购物车中 `selected=true` 的商品。创建成功后会：

- 创建订单和订单明细；
- 按数据库当前价格计算订单金额；
- 扣减商品库存；
- 增加商品销量；
- 删除已下单的购物车项；
- 订单初始状态为 `pending`。

所有 `POST /api/orders/` 请求都必须携带 `Idempotency-Key`。每笔新订单使用不同 key；只有重试同一次请求时才复用原 key。

本节创建三笔普通用户订单：

1. 第一笔支付，保存为 `paid_order_id`。
2. 第二笔取消，保存为 `cancelled_order_id`。
3. 第三笔保持待支付，保存为 `pending_order_id`。

### 9.1 创建第一笔订单：用于支付

先清空购物车，再添加一个商品：

```http
DELETE {{base_url}}/api/cart/clear/
Authorization: Bearer {{user_access}}
```

```http
POST {{base_url}}/api/cart/items/
Authorization: Bearer {{user_access}}
Content-Type: application/json
```

```json
{
  "product_id": {{product_id}},
  "quantity": 1
}
```

创建订单：

```http
POST {{base_url}}/api/orders/
Authorization: Bearer {{user_access}}
Content-Type: application/json
Idempotency-Key: apifox-user-paid-order-001
```

```json
{
  "remark": "Apifox 第一笔订单：用于支付"
}
```

预期：

- HTTP `201 Created`
- `code=0`
- `data.status=pending`
- `data.total_amount="1999.00"`
- `data.items` 中有一个订单明细
- 明细保存了下单时的 `product_name` 和 `product_price`

后置脚本：

```javascript
const body = pm.response.json();

pm.test("第一笔订单创建成功", function () {
  pm.response.to.have.status(201);
  pm.expect(body.code).to.eql(0);
  pm.expect(body.data.status).to.eql("pending");
  pm.expect(body.data.items).to.have.length(1);
});

pm.environment.set("paid_order_id", String(body.data.id));
```

创建成功后立即 GET 购物车，预期购物车为空。

### 9.2 查看第一笔订单详情

```http
GET {{base_url}}/api/orders/{{paid_order_id}}/
Authorization: Bearer {{user_access}}
```

预期响应结构：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "order_no": "EC20260711101000123456ABCDEFGH",
    "user_id": 2,
    "total_amount": "1999.00",
    "status": "pending",
    "remark": "Apifox 第一笔订单：用于支付",
    "items": [
      {
        "id": 1,
        "product_id": 1,
        "product_name": "Apifox 测试手机 Pro 20260711a",
        "product_price": "1999.00",
        "quantity": 1,
        "subtotal": "1999.00",
        "created_at": "2026-07-11T10:10:00+08:00"
      }
    ],
    "created_at": "2026-07-11T10:10:00+08:00",
    "paid_at": null,
    "cancelled_at": null,
    "updated_at": "2026-07-11T10:10:00+08:00"
  }
}
```

订单号、ID 和时间以实际响应为准。

### 9.3 支付第一笔订单

```http
POST {{base_url}}/api/orders/{{paid_order_id}}/pay/
Authorization: Bearer {{user_access}}
```

不需要请求体。

预期：HTTP `200`、`code=0`、`data.status=paid`、`data.paid_at` 不为 `null`。

### 9.4 已支付订单不能再次支付或取消

再次调用支付接口：

```http
POST {{base_url}}/api/orders/{{paid_order_id}}/pay/
```

预期：HTTP `400`、业务码 `40004`。

尝试取消：

```http
POST {{base_url}}/api/orders/{{paid_order_id}}/cancel/
```

预期：HTTP `400`、业务码 `40004`、提示订单状态不允许取消。

### 9.5 创建第二笔订单：用于取消

重新添加商品，数量使用 `2`：

```http
POST {{base_url}}/api/cart/items/
Authorization: Bearer {{user_access}}
Content-Type: application/json
```

```json
{
  "product_id": {{product_id}},
  "quantity": 2
}
```

创建订单：

```http
POST {{base_url}}/api/orders/
Authorization: Bearer {{user_access}}
Content-Type: application/json
Idempotency-Key: apifox-user-cancelled-order-001
```

```json
{
  "remark": "Apifox 第二笔订单：用于取消和恢复库存"
}
```

后置脚本：

```javascript
const body = pm.response.json();

pm.test("第二笔订单创建成功", function () {
  pm.response.to.have.status(201);
  pm.expect(body.code).to.eql(0);
  pm.expect(body.data.status).to.eql("pending");
});

pm.environment.set("cancelled_order_id", String(body.data.id));
```

记录此时商品详情中的 `stock` 和 `sales_count`。

### 9.6 取消第二笔订单并验证库存恢复

```http
POST {{base_url}}/api/orders/{{cancelled_order_id}}/cancel/
Authorization: Bearer {{user_access}}
```

预期：HTTP `200`、`code=0`、`data.status=cancelled`、`data.cancelled_at` 不为 `null`。

然后查询商品详情：

```http
GET {{base_url}}/api/products/{{product_id}}/
Authorization: Bearer {{user_access}}
```

对比取消前后：

- 商品库存应增加 `2`。
- 商品销量应减少 `2`，但不会低于 `0`。
- 第一笔已支付订单扣减的库存不会恢复。

再次取消同一订单，预期 HTTP `400`、业务码 `40004`。

### 9.7 创建第三笔订单：保持待支付

重新添加商品：

```json
{
  "product_id": {{product_id}},
  "quantity": 1
}
```

创建订单：

```http
POST {{base_url}}/api/orders/
Authorization: Bearer {{user_access}}
Content-Type: application/json
Idempotency-Key: apifox-user-pending-order-001
```

请求体：

```json
{
  "remark": "Apifox 第三笔订单：保持待支付"
}
```

后置脚本：

```javascript
const body = pm.response.json();

pm.test("第三笔订单保持待支付", function () {
  pm.response.to.have.status(201);
  pm.expect(body.code).to.eql(0);
  pm.expect(body.data.status).to.eql("pending");
});

pm.environment.set("pending_order_id", String(body.data.id));
```

不要支付或取消这笔订单，后面用于状态筛选和 HTTP `405` 测试。

### 9.8 普通用户查看订单列表

```http
GET {{base_url}}/api/orders/?page=1&page_size=10
Authorization: Bearer {{user_access}}
```

预期：HTTP `200`，订单位于 `data.results`，只包含当前普通用户自己的订单。

订单列表项不包含 `items`；需要查看订单明细时调用订单详情接口。

### 9.9 按订单状态筛选

已支付订单：

```http
GET {{base_url}}/api/orders/?status=paid&page=1&page_size=10
Authorization: Bearer {{user_access}}
```

已取消订单：

```http
GET {{base_url}}/api/orders/?status=cancelled&page=1&page_size=10
Authorization: Bearer {{user_access}}
```

待支付订单：

```http
GET {{base_url}}/api/orders/?status=pending&page=1&page_size=10
Authorization: Bearer {{user_access}}
```

允许的状态只有：

```text
pending
paid
cancelled
```

非法状态：

```http
GET {{base_url}}/api/orders/?status=finished
```

预期：HTTP `400`、业务码 `40000`，提示订单状态不合法。

### 9.10 购物车为空时创建订单

由于上一笔订单创建成功后购物车已被清空，直接再次调用：

```http
POST {{base_url}}/api/orders/
Authorization: Bearer {{user_access}}
Content-Type: application/json
Idempotency-Key: apifox-empty-cart-001
```

```json
{}
```

预期：HTTP `400`、业务码 `40003`、提示“购物车为空”。

### 9.11 验证数据库幂等重放

购物车虽然已经为空，但使用第三笔订单完全相同的 key 和请求体再次提交：

```http
POST {{base_url}}/api/orders/
Authorization: Bearer {{user_access}}
Content-Type: application/json
Idempotency-Key: apifox-user-pending-order-001
```

```json
{
  "remark": "Apifox 第三笔订单：保持待支付"
}
```

预期：

- HTTP `201 Created`。
- 响应头 `Idempotency-Replayed=true`。
- 返回的订单 ID 与 `pending_order_id` 相同。
- 不再次扣减库存，不创建第二张订单。

把 `remark` 改成其他内容但继续使用这个 key，预期 HTTP `409`、业务码 `40901`。

### 9.12 可选：验证订单重复提交锁

手动连续点击两次“创建订单”不一定稳定复现锁冲突，因为第一次请求可能很快完成并释放锁。Docker 环境下可以临时预置 Redis 锁：

1. 调用 `GET /api/auth/me/`，记录普通用户响应中的 `data.id`，例如 `2`。
2. 先给普通用户购物车添加一个有效商品。
3. 在 PowerShell 执行，注意把最后的 `2` 换成真实用户 ID：

```powershell
docker compose exec redis redis-cli SET lock:order:create:user:2 manual-apifox-lock NX EX 30
```

预期 Redis 返回：

```text
OK
```

4. 在 30 秒内调用 `POST /api/orders/`。

请求需要携带一个尚未使用的幂等键，例如：

```http
Idempotency-Key: apifox-lock-check-001
```

预期：HTTP `409 Conflict`、业务码 `40900`、提示“订单正在处理中，请勿重复提交”，购物车项仍然存在。

等待 30 秒让测试锁自动过期，或者手动删除对应 key：

```powershell
docker compose exec redis redis-cli DEL lock:order:create:user:2
```

该步骤只用于本地开发环境，不要在生产 Redis 中手动写锁。

## 10. 管理员订单查询与用户隔离测试

### 10.1 管理员查看全部订单

```http
GET {{base_url}}/api/orders/?page=1&page_size=100
Authorization: Bearer {{admin_access}}
```

预期：HTTP `200`，管理员能够看到普通用户创建的三笔订单。

### 10.2 管理员查看普通用户订单详情

```http
GET {{base_url}}/api/orders/{{paid_order_id}}/
Authorization: Bearer {{admin_access}}
```

预期：HTTP `200`，即使订单不属于管理员也能查看。

### 10.3 创建一笔管理员自己的订单

管理员也是已认证用户，可以使用购物车和订单接口。先清空管理员购物车：

```http
DELETE {{base_url}}/api/cart/clear/
Authorization: Bearer {{admin_access}}
```

添加商品：

```http
POST {{base_url}}/api/cart/items/
Authorization: Bearer {{admin_access}}
Content-Type: application/json
```

```json
{
  "product_id": {{product_id}},
  "quantity": 1
}
```

创建管理员订单：

```http
POST {{base_url}}/api/orders/
Authorization: Bearer {{admin_access}}
Content-Type: application/json
Idempotency-Key: apifox-admin-order-001
```

```json
{
  "remark": "管理员订单：用于普通用户越权测试"
}
```

后置脚本：

```javascript
const body = pm.response.json();
pm.environment.set("admin_order_id", String(body.data.id));
```

### 10.4 普通用户访问管理员订单应失败

```http
GET {{base_url}}/api/orders/{{admin_order_id}}/
Authorization: Bearer {{user_access}}
```

预期：HTTP `404`、业务码 `40400`。

这里返回 `404` 而不是 `403`，因为普通用户的订单查询集已经限定为本人订单，系统不会向其暴露其他用户订单是否存在。

### 10.5 普通用户订单列表不应出现管理员订单

```http
GET {{base_url}}/api/orders/?page=1&page_size=100
Authorization: Bearer {{user_access}}
```

预期：`data.results` 中没有 `admin_order_id`。

## 11. 订单不支持方法与软删除测试

### 11.1 订单 PUT 返回 405

```http
PUT {{base_url}}/api/orders/{{pending_order_id}}/
Authorization: Bearer {{user_access}}
Content-Type: application/json
```

```json
{
  "remark": "尝试修改订单"
}
```

预期：HTTP `405 Method Not Allowed`。

### 11.2 订单 PATCH 返回 405

```http
PATCH {{base_url}}/api/orders/{{pending_order_id}}/
Authorization: Bearer {{user_access}}
Content-Type: application/json
```

```json
{
  "remark": "尝试部分修改订单"
}
```

预期：HTTP `405 Method Not Allowed`。

### 11.3 订单 DELETE 返回 405

```http
DELETE {{base_url}}/api/orders/{{pending_order_id}}/
Authorization: Bearer {{user_access}}
```

预期：HTTP `405 Method Not Allowed`。

当前自定义异常处理器没有为 HTTP `405` 单独配置业务码，因此响应体可能显示 `code=50000`；以 HTTP `405` 作为本组测试的主要断言，message 文本可能随 DRF 语言翻译略有变化。

### 11.4 管理员软删除商品

确认购物车和订单测试全部完成后执行：

```http
DELETE {{base_url}}/api/admin/products/{{product_id}}/
Authorization: Bearer {{admin_access}}
```

预期：HTTP `200`、`code=0`、`data=null`。

管理员再次访问管理商品详情：

```http
GET {{base_url}}/api/admin/products/{{product_id}}/
Authorization: Bearer {{admin_access}}
```

预期：HTTP `200`、`data.status=inactive`，证明记录没有被物理删除。

### 11.5 普通用户看不到下架商品

普通用户或匿名调用：

```http
GET {{base_url}}/api/products/{{product_id}}/
```

预期：HTTP `404`、业务码 `40400`。

商品列表中也不应再出现该商品。

### 11.6 下架商品不能加入购物车

```http
POST {{base_url}}/api/cart/items/
Authorization: Bearer {{user_access}}
Content-Type: application/json
```

```json
{
  "product_id": {{product_id}},
  "quantity": 1
}
```

预期：HTTP `400`、业务码 `40002`、提示“商品已下架”。

### 11.7 管理员软删除分类

商品测试完成后再执行：

```http
DELETE {{base_url}}/api/admin/categories/{{category_id}}/
Authorization: Bearer {{admin_access}}
```

预期：HTTP `200`、`code=0`、`data=null`。

管理员查看管理分类详情：

```http
GET {{base_url}}/api/admin/categories/{{category_id}}/
Authorization: Bearer {{admin_access}}
```

预期：HTTP `200`、`data.is_active=false`。

匿名访问公开分类详情：

```http
GET {{base_url}}/api/categories/{{category_id}}/
```

预期：HTTP `404`、业务码 `40400`。

## 12. 完整执行顺序

为了避免前一步破坏后一步所需数据，建议严格按以下顺序执行：

1. 启动 Docker 服务。
2. 调用健康检查。
3. 创建 Apifox 环境和全部变量。
4. 注册管理员候选账号。
5. 注册普通用户。
6. 使用 Django Shell 将管理员候选账号提升为 `admin`。
7. 管理员登录并提取 `admin_access/admin_refresh`。
8. 普通用户登录并提取 `user_access/user_refresh`。
9. 分别调用 `/api/auth/me/` 验证角色。
10. 测试刷新 Token。
11. 管理员创建分类并提取 `category_id`。
12. 管理员测试分类列表、详情、PUT、PATCH。
13. 普通用户测试无权创建分类。
14. 管理员创建商品并提取 `product_id`。
15. 管理员测试商品列表、详情、PUT、PATCH。
16. 匿名或普通用户测试商品列表、详情、筛选、排序和分页。
17. 普通用户测试无权创建商品。
18. 普通用户清空购物车。
19. 测试购物车首次添加、重复累加、PATCH、GET、单项删除、清空。
20. 测试购物车数量为 0、超过库存、空 PATCH、错误 ID。
21. 添加商品并创建第一笔订单，提取 `paid_order_id`。
22. 查询第一笔订单详情并支付。
23. 验证已支付订单不能重复支付或取消。
24. 添加两个商品数量并创建第二笔订单，提取 `cancelled_order_id`。
25. 取消第二笔订单并验证库存和销量恢复。
26. 添加商品并创建第三笔订单，提取 `pending_order_id`，保持待支付。
27. 测试订单列表、详情和三个状态筛选。
28. 测试购物车为空创建订单。
29. 复用第三笔订单 key，验证数据库幂等重放和内容冲突。
30. 可选测试 Redis 重复提交锁。
31. 管理员查看所有订单和普通用户订单详情。
32. 管理员创建自己的订单并提取 `admin_order_id`。
33. 普通用户验证无法查看管理员订单。
34. 对待支付订单发送 PUT、PATCH、DELETE，验证 HTTP `405`。
35. 管理员软删除商品。
36. 验证普通用户看不到下架商品且不能加入购物车。
37. 管理员软删除分类。
38. 验证公开分类接口看不到停用分类。

## 13. 角色权限矩阵

| 资源/操作 | 匿名用户 | 普通用户 | 管理员 |
|---|---:|---:|---:|
| 注册、登录、刷新 Token | 允许 | 允许 | 允许 |
| 获取当前用户 `/api/auth/me/` | `401` | 允许 | 允许 |
| 公开分类列表和详情 | 允许，仅启用分类 | 允许，仅启用分类 | 允许，但公开路由仍只返回启用分类 |
| 管理分类列表和详情 | `401` | `403` | 允许 |
| 创建、修改、软删除分类 | `401` | `403` | 允许 |
| 公开商品列表和详情 | 允许，仅上架商品 | 允许，仅上架商品 | 管理员携带 Token 时公开商品 ViewSet 可看到下架记录 |
| 管理商品列表和详情 | `401` | `403` | 允许 |
| 创建、修改、软删除商品 | `401` | `403` | 允许 |
| 查看和操作购物车 | `401` | 仅本人 | 仅本人 |
| 创建订单 | `401` | 从本人购物车创建 | 从本人购物车创建 |
| 查看订单列表 | `401` | 仅本人订单 | 全部订单 |
| 查看订单详情 | `401` | 仅本人订单 | 任意订单 |
| 支付或取消订单 | `401` | 仅本人订单且状态允许 | 任意订单且状态允许 |
| 通用修改/删除订单 | `405` 或先认证失败 | `405` | `405` |

说明：匿名调用管理员路由通常先在权限层失败，具体表现取决于 JWT 认证与权限处理；本项目在未提供有效凭证时通常返回 HTTP `401`。

## 14. 常见错误与排查

### 14.1 Apifox 提示连接失败

检查：

```powershell
docker compose ps
Invoke-RestMethod http://127.0.0.1:8080/api/health/
```

如果使用本地 runserver，`base_url` 必须改成 `http://127.0.0.1:8000`。

### 14.2 返回 401 未认证

依次检查：

1. 是否已经成功登录。
2. 环境中 `admin_access` 或 `user_access` 是否非空。
3. 当前请求是否选中了正确环境。
4. Auth 类型是否为 Bearer Token。
5. Token 输入框是否填写 `{{user_access}}` 或 `{{admin_access}}`。
6. 是否错误地把 refresh Token 当成 access Token。
7. access Token 是否超过默认 60 分钟有效期。

Token 过期时使用 refresh 接口获取新的 access Token。

### 14.3 普通用户调用管理员接口返回 403

这是正确结果。普通用户的 `role=user`，管理分类和商品要求 `role=admin` 或超级用户。

### 14.4 管理员接口仍返回 403

调用：

```http
GET {{base_url}}/api/auth/me/
Authorization: Bearer {{admin_access}}
```

如果 `data.role` 仍是 `user`：

- 检查 Shell 命令中的用户名是否与 `admin_username` 完全一致。
- 确认命令输出 `updated=1`。
- 重新登录管理员并覆盖 `admin_access`。

### 14.5 注册用户名已存在

更换本轮测试标识，并同步修改：

- `admin_username`
- `user_username`
- `category_name`
- `category_slug`
- `product_name`
- `product_slug`

### 14.6 分类或商品 slug 已存在

`slug` 设置了唯一约束。修改 Apifox 环境中的 `category_slug` 或 `product_slug` 后重新发送。

### 14.7 请求体提示 JSON 格式错误

检查：

- 字符串变量是否带双引号，例如 `"{{product_name}}"`。
- 数字变量是否不带双引号，例如 `{{product_id}}`。
- 环境变量是否已经提取成功。
- JSON 最后一项后面是否误加逗号。

### 14.8 创建订单提示购物车为空

创建订单只读取当前登录用户 `selected=true` 的购物车项。检查：

1. 添加购物车和创建订单是否使用了同一个用户 Token。
2. 购物车项是否被设置成 `selected=false`。
3. 前一次订单创建是否已经把购物车项删除。

### 14.9 商品已下架

如果已经执行第 11 节的商品 DELETE，商品状态会变成 `inactive`，无法继续购物车和订单测试。重新测试时应创建一个新的上架商品，或由管理员 PATCH 将状态改回 `active`，前提是分类仍启用。

### 14.10 分类已停用

分类停用后：

- 公开分类接口看不到该分类；
- 其商品对普通用户不可见；
- 商品创建/修改时选择该分类会校验失败。

因此分类软删除必须最后执行。

### 14.11 已支付订单不能取消

这是当前业务规则。需要验证取消和库存恢复时，必须新建一笔 `pending` 订单，不能复用已支付订单。

### 14.12 DELETE 返回 200 而不是 204

分类、商品和购物车 DELETE 使用项目统一的 `api_response()`，会返回 JSON 响应体：

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

因此当前项目返回 HTTP `200`，不是 DRF 默认的 `204 No Content`。

## 15. 测试结果记录表

你可以复制下表，在每次测试后填写：

| 序号 | 请求名称 | 角色 | 预期 HTTP | 实际 HTTP | 预期业务码 | 实际业务码 | 结论/备注 |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | 健康检查 | 匿名 | 200 |  | 0 |  |  |
| 2 | 注册管理员候选账号 | 匿名 | 201 |  | 0 |  |  |
| 3 | 注册普通用户 | 匿名 | 201 |  | 0 |  |  |
| 4 | 管理员登录 | 匿名 | 200 |  | 0 |  |  |
| 5 | 普通用户登录 | 匿名 | 200 |  | 0 |  |  |
| 6 | 管理员当前用户信息 | 管理员 | 200 |  | 0 |  | role=admin |
| 7 | 普通用户当前用户信息 | 普通用户 | 200 |  | 0 |  | role=user |
| 8 | 管理员创建分类 | 管理员 | 201 |  | 0 |  |  |
| 9 | 普通用户创建分类 | 普通用户 | 403 |  | 40300 |  |  |
| 10 | 管理员创建商品 | 管理员 | 201 |  | 0 |  |  |
| 11 | 普通用户创建商品 | 普通用户 | 403 |  | 40300 |  |  |
| 12 | 公开商品列表 | 匿名 | 200 |  | 0 |  |  |
| 13 | 首次添加购物车 | 普通用户 | 201 |  | 0 |  |  |
| 14 | 重复添加购物车 | 普通用户 | 200 |  | 0 |  | 数量累加 |
| 15 | 修改购物车 | 普通用户 | 200 |  | 0 |  |  |
| 16 | 超库存添加 | 普通用户 | 400 |  | 40001 |  |  |
| 17 | 创建支付订单 | 普通用户 | 201 |  | 0 |  |  |
| 18 | 支付订单 | 普通用户 | 200 |  | 0 |  | status=paid |
| 19 | 取消已支付订单 | 普通用户 | 400 |  | 40004 |  |  |
| 20 | 创建取消订单 | 普通用户 | 201 |  | 0 |  |  |
| 21 | 取消待支付订单 | 普通用户 | 200 |  | 0 |  | 库存恢复 |
| 22 | 创建待支付订单 | 普通用户 | 201 |  | 0 |  | status=pending |
| 23 | 管理员查看普通用户订单 | 管理员 | 200 |  | 0 |  |  |
| 24 | 普通用户查看管理员订单 | 普通用户 | 404 |  | 40400 |  |  |
| 25 | PUT 修改订单 | 普通用户 | 405 |  | 50000* |  | 以 HTTP 为准 |
| 26 | PATCH 修改订单 | 普通用户 | 405 |  | 50000* |  | 以 HTTP 为准 |
| 27 | DELETE 删除订单 | 普通用户 | 405 |  | 50000* |  | 以 HTTP 为准 |
| 28 | 管理员下架商品 | 管理员 | 200 |  | 0 |  | status=inactive |
| 29 | 下架商品加入购物车 | 普通用户 | 400 |  | 40002 |  |  |
| 30 | 管理员停用分类 | 管理员 | 200 |  | 0 |  | is_active=false |

`50000*` 表示当前异常处理器对 HTTP `405` 的可能业务码，实际测试以 HTTP 状态码和当前响应为准。

## 16. Apifox 官方参考

本手册中的环境变量、JSONPath 提取和后置脚本方式可参考：

- [Apifox：全局变量、环境变量、模块变量和临时变量](https://docs.apifox.com/global-environment-session-variables)
- [Apifox：提取变量](https://docs.apifox.com/extract-variables/)
- [Apifox：断言](https://docs.apifox.com/assertions)
- [Apifox：后置脚本](https://docs.apifox.com/5581000m0)
- [Apifox：接口之间如何传递数据](https://docs.apifox.com/doc-5793498)

完成整套测试后，至少应确认：管理员写权限、普通用户隔离、JWT 认证、商品上下架、购物车数量规则、订单库存扣减、支付状态、取消恢复库存和订单不支持方法都符合当前项目实现。
