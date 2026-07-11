# Apifox 双角色接口测试手册 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一份基于当前仓库真实实现的中文 Apifox 操作手册，使读者能够用管理员和普通用户完成认证、分类、商品、购物车、订单与订单详情测试。

**Architecture:** 只新增 `docs/apifox_api_testing_guide.md`，不修改后端代码。文档采用端到端场景顺序，使用 Apifox 环境变量串联 Token 和业务 ID，并用接口速查表、权限矩阵和错误场景补全覆盖。

**Tech Stack:** Markdown、Apifox、Django 5.2、Django REST Framework、SimpleJWT、Docker Compose、PowerShell

## Global Constraints

- 最终交付文件固定为 `docs/apifox_api_testing_guide.md`，编码为 UTF-8。
- 不修改 `apps/`、`config/`、数据库迁移或运行配置。
- Docker 推荐地址固定为 `http://127.0.0.1:8080`，本地 `runserver` 备选地址为 `http://127.0.0.1:8000`。
- 管理员与普通用户都先调用注册接口；管理员候选账号注册后通过 Django Shell 更新为 `role=admin`。
- 商品与分类管理接口仅管理员可写；购物车和订单接口必须认证。
- 订单只覆盖当前实现的创建、列表、详情、支付、取消；`PUT/PATCH/DELETE` 作为 HTTP `405` 负向测试。
- Apifox 请求中使用 `{{变量名}}`，脚本中使用 `pm.environment.get/set`，Token 和密码写入本地值而非团队共享远程值。
- 所有接口说明都同时标明 HTTP 状态码、业务 `code`、关键响应字段和所用角色。

---

## File Structure

- Create: `docs/apifox_api_testing_guide.md` — 最终可执行测试手册。
- Reference: `docs/superpowers/specs/2026-07-11-apifox-api-testing-guide-design.md` — 已批准设计与完成标准。
- Reference: `config/urls.py`、`apps/*/urls.py` — URL 真值来源。
- Reference: `apps/*/serializers.py` — 请求字段与校验真值来源。
- Reference: `apps/*/views.py`、`apps/orders/services.py` — 权限、状态码和业务状态变化真值来源。
- Reference: `apps/*/tests.py` — 预期响应与错误码真值来源。

### Task 1: 创建运行准备、Apifox 环境和双角色认证章节

**Files:**
- Create: `docs/apifox_api_testing_guide.md`
- Reference: `README.md`
- Reference: `docker-compose.yml`
- Reference: `apps/accounts/serializers.py`
- Reference: `apps/accounts/views.py`

**Interfaces:**
- Consumes: `/api/health/`、`/api/auth/register/`、`/api/auth/login/`、`/api/auth/refresh/`、`/api/auth/me/`。
- Produces: `admin_access`、`admin_refresh`、`user_access`、`user_refresh` 环境变量，以及后续业务请求统一使用的认证规则。

- [ ] **Step 1: 创建文档骨架和执行目录**

创建文件并按以下固定顺序写入一级、二级标题：

```markdown
# Mini E-Commerce Backend：Apifox 双角色接口测试完整手册

## 1. 测试目标与当前 API 边界
## 2. 启动项目并确认服务可用
## 3. 创建 Apifox 项目与测试环境
## 4. 准备管理员和普通用户
## 5. 认证接口测试
## 6. 分类接口测试
## 7. 商品接口测试
## 8. 购物车接口测试
## 9. 订单与订单详情测试
## 10. 管理员订单查询与用户隔离测试
## 11. 订单不支持方法测试
## 12. 完整执行顺序
## 13. 角色权限矩阵
## 14. 常见错误与排查
## 15. 测试结果记录表
## 16. Apifox 官方参考
```

在第 1 节明确说明分类和商品管理支持标准 ModelViewSet 方法，购物车支持业务所需的查询、添加、部分更新、删除和清空，订单不提供通用更新与删除。

- [ ] **Step 2: 写入 Docker、本地启动和健康检查步骤**

写入以下 PowerShell 命令及期望结果：

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://127.0.0.1:8080/api/health/
```

期望健康检查响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "ok"
  }
}
```

同时写入本地备选启动命令：

```powershell
python manage.py migrate
python manage.py runserver
Invoke-RestMethod http://127.0.0.1:8000/api/health/
```

- [ ] **Step 3: 写入 Apifox 环境变量表**

使用以下变量名和示例本地值，明确 Token 与密码只填写本地值：

```text
base_url=http://127.0.0.1:8080
run_id=20260711a
admin_username=apifox_admin_20260711a
admin_password=Admin123456
admin_access=
admin_refresh=
user_username=apifox_user_20260711a
user_password=User123456
user_access=
user_refresh=
category_id=
product_id=
cart_item_id=
paid_order_id=
cancelled_order_id=
pending_order_id=
```

解释每轮重新测试需要更换 `run_id`，并同步修改两个完整用户名；不要把一个变量值设置成另一个变量表达式。

- [ ] **Step 4: 写入两次注册请求和管理员提升命令**

管理员候选账号注册：

```http
POST {{base_url}}/api/auth/register/
Content-Type: application/json
```

```json
{
  "username": "{{admin_username}}",
  "password": "{{admin_password}}",
  "password_confirm": "{{admin_password}}",
  "email": "apifox-admin@example.com",
  "phone": "13800000001"
}
```

普通用户注册请求体只将用户名、密码、邮箱、手机号替换为普通用户变量和 `13800000002`。两个请求都断言 HTTP `201`、`$.code` 等于 `0`、`$.data.role` 等于 `user`。

Docker 管理员提升命令：

```powershell
docker compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); updated=User.objects.filter(username='apifox_admin_20260711a').update(role='admin', is_staff=True); print(f'updated={updated}')"
```

本地运行备选命令：

```powershell
python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); updated=User.objects.filter(username='apifox_admin_20260711a').update(role='admin', is_staff=True); print(f'updated={updated}')"
```

期望输出为 `updated=1`。说明更换 `run_id` 后必须同步替换命令中的实际管理员用户名。

- [ ] **Step 5: 写入登录、提取 Token、当前用户和刷新 Token 操作**

分别创建管理员和普通用户登录请求：

```http
POST {{base_url}}/api/auth/login/
Content-Type: application/json
```

```json
{
  "username": "{{admin_username}}",
  "password": "{{admin_password}}"
}
```

管理员登录后置脚本固定为：

```javascript
const body = pm.response.json();
pm.test("HTTP 状态码为 200", function () {
  pm.response.to.have.status(200);
});
pm.test("业务码为 0", function () {
  pm.expect(body.code).to.eql(0);
});
pm.environment.set("admin_access", body.data.access);
pm.environment.set("admin_refresh", body.data.refresh);
```

普通用户脚本将变量名替换为 `user_access`、`user_refresh`。`/api/auth/me/` 请求分别使用 Bearer `{{admin_access}}` 与 `{{user_access}}`，断言管理员 `$.data.role=admin`、普通用户 `$.data.role=user`。刷新请求使用对应 refresh Token，并把返回的 `$.data.access` 覆盖保存到对应 access 环境变量。

- [ ] **Step 6: 验证认证章节并提交**

运行：

```powershell
Select-String -LiteralPath docs\apifox_api_testing_guide.md -Pattern '/api/auth/register/','/api/auth/login/','/api/auth/refresh/','/api/auth/me/','admin_access','user_access'
```

期望：六组模式全部至少匹配一次。

提交：

```powershell
git add docs/apifox_api_testing_guide.md
git commit -m "docs: add Apifox setup and authentication workflow"
```

### Task 2: 补全分类、商品、购物车和订单端到端测试

**Files:**
- Modify: `docs/apifox_api_testing_guide.md`
- Reference: `apps/products/urls.py`
- Reference: `apps/products/serializers.py`
- Reference: `apps/products/views.py`
- Reference: `apps/carts/urls.py`
- Reference: `apps/carts/serializers.py`
- Reference: `apps/carts/views.py`
- Reference: `apps/orders/urls.py`
- Reference: `apps/orders/views.py`
- Reference: `apps/orders/services.py`

**Interfaces:**
- Consumes: Task 1 产出的 access Token 环境变量。
- Produces: `category_id`、`product_id`、`cart_item_id`、`paid_order_id`、`cancelled_order_id`、`pending_order_id`，以及完整业务验证链路。

- [ ] **Step 1: 写入分类管理 CRUD 与权限测试**

覆盖并说明以下请求：

```text
GET    /api/admin/categories/
POST   /api/admin/categories/
GET    /api/admin/categories/{{category_id}}/
PUT    /api/admin/categories/{{category_id}}/
PATCH  /api/admin/categories/{{category_id}}/
DELETE /api/admin/categories/{{category_id}}/
GET    /api/categories/
GET    /api/categories/{{category_id}}/
```

创建请求体：

```json
{
  "name": "Apifox 数码分类 20260711a",
  "slug": "apifox-digital-20260711a",
  "is_active": true
}
```

创建成功后用 JSONPath `$.data.id` 提取 `category_id`。POST 断言 HTTP `201`，其他成功请求断言 HTTP `200`。普通用户携带 `{{user_access}}` 调用管理创建接口，断言 HTTP `403` 和业务码 `40300`。分类 DELETE 放到整条业务链最后执行，因为它会把 `is_active` 改为 `false`。

- [ ] **Step 2: 写入商品管理 CRUD、公开查询、筛选和权限测试**

覆盖以下管理请求：

```text
GET    /api/admin/products/
POST   /api/admin/products/
GET    /api/admin/products/{{product_id}}/
PUT    /api/admin/products/{{product_id}}/
PATCH  /api/admin/products/{{product_id}}/
DELETE /api/admin/products/{{product_id}}/
```

创建请求体：

```json
{
  "category": {{category_id}},
  "name": "Apifox 测试手机 20260711a",
  "slug": "apifox-phone-20260711a",
  "description": "用于管理员、购物车和订单接口联调",
  "price": "1999.00",
  "stock": 30,
  "status": "active",
  "image_url": "https://example.com/apifox-phone.jpg"
}
```

用 `$.data.id` 提取 `product_id`。公开接口覆盖：

```text
GET /api/products/
GET /api/products/{{product_id}}/
GET /api/products/?category={{category_id}}&keyword=Apifox&min_price=1000&max_price=3000&ordering=-price&page=1&page_size=10
```

说明分页结果位于 `$.data.results`。普通用户调用管理创建接口断言 `403/40300`。商品 DELETE 放到订单测试结束后，因为它会把商品状态改为 `inactive`。

- [ ] **Step 3: 写入购物车增删改查和业务校验**

按顺序覆盖：

```text
GET    /api/cart/
POST   /api/cart/items/
POST   /api/cart/items/              再次添加，验证数量累加
PATCH  /api/cart/items/{{cart_item_id}}/
DELETE /api/cart/items/{{cart_item_id}}/
DELETE /api/cart/clear/
```

首次添加请求体：

```json
{
  "product_id": {{product_id}},
  "quantity": 2
}
```

首次添加断言 HTTP `201` 并用 `$.data.id` 提取 `cart_item_id`；再次添加数量 `1`，断言 HTTP `200` 且 `$.data.quantity=3`。PATCH 请求体为：

```json
{
  "quantity": 2,
  "selected": true
}
```

补充无 Token 返回 `401/40100`、数量 `0` 返回 HTTP `400`、数量超过库存返回 `400/40001`。说明购物车项 ID 属于用户，其他用户访问时表现为 `404/40400`。

- [ ] **Step 4: 写入三笔订单的创建、详情、支付、取消和待支付测试**

每次创建订单前调用 `POST /api/cart/items/` 添加数量 `1` 且保持 `selected=true`，然后调用：

```http
POST {{base_url}}/api/orders/
Authorization: Bearer {{user_access}}
Content-Type: application/json
```

```json
{
  "remark": "Apifox 接口测试订单"
}
```

第一笔订单用 `$.data.id` 提取 `paid_order_id`，随后调用 `POST /api/orders/{{paid_order_id}}/pay/`，断言状态为 `paid`。第二笔提取 `cancelled_order_id`，调用 `POST /api/orders/{{cancelled_order_id}}/cancel/`，断言状态为 `cancelled`，并重新查询商品确认库存恢复。第三笔提取 `pending_order_id`，保持状态为 `pending`。

覆盖列表、筛选和详情：

```text
GET /api/orders/
GET /api/orders/?status=paid&page=1&page_size=10
GET /api/orders/{{paid_order_id}}/
GET /api/orders/{{cancelled_order_id}}/
GET /api/orders/{{pending_order_id}}/
```

补充购物车为空创建订单返回 `400/40003`，已支付订单再次支付或取消返回 `400/40004`，非法状态筛选返回 HTTP `400`。

- [ ] **Step 5: 写入管理员订单查询、用户隔离和 405 测试**

管理员使用 `{{admin_access}}` 调用 `/api/orders/` 和 `/api/orders/{{paid_order_id}}/`，断言能够看到普通用户订单。普通用户访问一个管理员或其他用户创建的订单 ID 时，断言 `404/40400`。

对 `/api/orders/{{pending_order_id}}/` 分别发送：

```text
PUT
PATCH
DELETE
```

三次都以 HTTP `405 Method Not Allowed` 为主要断言。响应体业务码按当前异常处理器的实际结果记录，不能描述成订单状态错误。

- [ ] **Step 6: 写入末尾软删除验证、权限矩阵、执行顺序和排查表**

先以管理员 DELETE 商品，再验证普通用户商品列表不再出现该商品、添加购物车返回 `400/40002`；最后 DELETE 分类，并验证公开分类列表不再出现它。

权限矩阵至少包含匿名、普通用户、管理员三列以及认证、公开商品、管理商品、购物车、本人订单、他人订单六类资源。测试结果记录表至少包含序号、请求名称、角色、预期 HTTP、实际 HTTP、预期业务码、实际业务码、结论八列。

常见排查必须覆盖：Docker 未启动、`base_url` 端口错误、Token 未保存或过期、Bearer 前缀缺失、用户名或 slug 重复、Shell 提升用户名未同步、购物车为空、商品已下架、库存不足、已支付订单不能取消。

- [ ] **Step 7: 提交业务测试章节**

运行结构检查：

```powershell
$patterns = @('/api/admin/categories/','/api/admin/products/','/api/cart/items/','/api/orders/','/pay/','/cancel/','405 Method Not Allowed','角色权限矩阵','测试结果记录表')
$text = Get-Content -LiteralPath docs\apifox_api_testing_guide.md -Raw -Encoding UTF8
$missing = $patterns | Where-Object { $text -notmatch [regex]::Escape($_) }
if ($missing) { $missing; exit 1 }
```

期望：退出码 `0`，没有缺失模式输出。

提交：

```powershell
git add docs/apifox_api_testing_guide.md
git commit -m "docs: complete Apifox e-commerce API test workflow"
```

### Task 3: 对照代码和测试验证最终手册

**Files:**
- Verify: `docs/apifox_api_testing_guide.md`
- Verify: `config/urls.py`
- Verify: `apps/accounts/serializers.py`
- Verify: `apps/products/serializers.py`
- Verify: `apps/carts/serializers.py`
- Verify: `apps/orders/serializers.py`
- Test: `apps/accounts/tests.py`
- Test: `apps/products/tests.py`
- Test: `apps/carts/tests.py`
- Test: `apps/orders/tests.py`

**Interfaces:**
- Consumes: Task 2 完整手册。
- Produces: 路由、字段、Markdown 结构和 Django 测试均通过的验证证据。

- [ ] **Step 1: 用 Django resolver 检查所有路径模板**

运行：

```powershell
python manage.py shell -c "from django.urls import resolve; paths=['/api/health/','/api/auth/register/','/api/auth/login/','/api/auth/refresh/','/api/auth/me/','/api/categories/','/api/categories/1/','/api/products/','/api/products/1/','/api/admin/categories/','/api/admin/categories/1/','/api/admin/products/','/api/admin/products/1/','/api/cart/','/api/cart/items/','/api/cart/items/1/','/api/cart/clear/','/api/orders/','/api/orders/1/','/api/orders/1/pay/','/api/orders/1/cancel/']; [print(p, resolve(p).view_name) for p in paths]"
```

期望：所有路径都输出非空 `view_name`，没有 `Resolver404`。

- [ ] **Step 2: 检查关键序列化器字段**

运行：

```powershell
python manage.py shell -c "from apps.accounts.serializers import RegisterSerializer, LoginSerializer; from apps.products.serializers import CategorySerializer, ProductCreateUpdateSerializer; from apps.carts.serializers import AddCartItemSerializer, UpdateCartItemSerializer; from apps.orders.serializers import OrderCreateSerializer; classes=[RegisterSerializer,LoginSerializer,CategorySerializer,ProductCreateUpdateSerializer,AddCartItemSerializer,UpdateCartItemSerializer,OrderCreateSerializer]; [print(c.__name__, list(c().fields)) for c in classes]"
```

期望字段分别与手册请求体一致，尤其确认注册接口没有 `role`、购物车添加使用 `product_id`、订单创建只接收可选 `remark`。

- [ ] **Step 3: 运行 Django 系统检查和完整测试**

运行：

```powershell
python manage.py check
python manage.py test
```

期望：`System check identified no issues`，测试退出码 `0` 且无失败或错误。

- [ ] **Step 4: 运行 Markdown 完整性检查**

运行：

```powershell
$path = 'docs\apifox_api_testing_guide.md'
$text = Get-Content -LiteralPath $path -Raw -Encoding UTF8
$required = @('## 1.','## 2.','## 3.','## 4.','## 5.','## 6.','## 7.','## 8.','## 9.','## 10.','## 11.','## 12.','## 13.','## 14.','## 15.','## 16.','{{base_url}}','{{admin_access}}','{{user_access}}','category_id','product_id','cart_item_id','paid_order_id','cancelled_order_id','pending_order_id')
$missing = $required | Where-Object { $text -notmatch [regex]::Escape($_) }
$markers = @('TO' + 'DO', 'TB' + 'D')
$unfinished = ($markers | Where-Object { $text -match [regex]::Escape($_) }).Count
"missing=$($missing.Count) unfinished=$unfinished lines=$((Get-Content -LiteralPath $path -Encoding UTF8).Count)"
if ($missing.Count -ne 0 -or $unfinished -ne 0) { $missing; exit 1 }
```

期望输出包含 `missing=0 unfinished=0`，退出码 `0`。

- [ ] **Step 5: 对照设计完成标准并提交必要修订**

逐项检查设计文件中的“完成标准”，只修改 `docs/apifox_api_testing_guide.md` 中与源码不一致或操作不完整的内容。若有修订，执行：

```powershell
git add docs/apifox_api_testing_guide.md
git commit -m "docs: verify Apifox guide against implemented APIs"
```

若没有修订，不创建空提交；记录 `git status --short` 和最后两条提交作为交付证据。
