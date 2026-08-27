# Mini E-Commerce

## 项目简介

Mini E-Commerce 是一个前后端完整的轻量级电商项目。后端基于 Django REST Framework，负责认证授权、商品、购物车、订单、库存一致性、缓存和异步任务；前端基于 Vue 3，为普通用户和业务管理员提供可直接在浏览器中使用的界面。

核心业务链路包括：注册和登录、筛选及浏览商品、加入购物车、提交订单、模拟支付、取消待支付订单并恢复库存。管理员可以在独立的管理界面维护分类、商品并查看订单。

## 技术栈

后端与基础设施：

- Python 3.12、Django 5.2、Django REST Framework
- djangorestframework-simplejwt
- MySQL 8.0、Redis 7
- Celery 5.6、Gunicorn
- Nginx、Docker Compose
- Django APITestCase

前端：

- Vue 3、TypeScript、Vite
- Vue Router、Pinia
- TanStack Vue Query
- Element Plus
- Vitest、Vue Testing Library

## 核心功能

- Vue 单页商城和响应式浏览器界面
- 用户注册、登录、退出、会话恢复和个人中心
- 浏览器安全认证：access token 仅保存在内存，refresh token 使用 HttpOnly Cookie，并为认证写操作校验 CSRF
- 商品分类、关键词、价格、排序和分页筛选
- 商品详情和商品详情 Redis 缓存
- 购物车添加、勾选、修改数量、删除和清空
- 从已勾选购物车项创建订单
- 使用幂等键、Redis 短锁和数据库唯一约束防止重复下单
- 使用数据库事务和行锁保证库存扣减一致性
- 订单列表、订单详情、模拟支付和取消
- Celery 自动取消超时未支付订单，并通过定时扫描补偿丢失消息
- 管理员分类和商品管理、订单查看
- Docker Compose 一键启动 Vue、Django、MySQL、Redis、Celery 和 Nginx

## 项目结构

```text
.
├─ apps/                 # Django 业务应用
├─ config/               # Django、JWT、Celery 配置
├─ frontend/             # Vue 3 前端
├─ nginx/                # SPA 托管和 Django 反向代理
├─ docs/                 # API、前端、Docker、数据库等文档
├─ docker-compose.yml
└─ Dockerfile
```

前端目录、状态边界、请求层和部署细节见 [docs/frontend.md](docs/frontend.md)。

## 界面入口

普通用户界面：

| 地址 | 功能 |
|---|---|
| `/` | 商品列表、搜索与筛选 |
| `/products/{id}` | 商品详情 |
| `/login`、`/register` | 登录、注册 |
| `/account` | 当前用户信息 |
| `/cart` | 购物车 |
| `/checkout` | 确认并提交订单 |
| `/orders`、`/orders/{id}` | 订单列表与订单详情 |

业务管理员界面：

| 地址 | 功能 |
|---|---|
| `/manage` | 管理概览 |
| `/manage/categories` | 分类管理 |
| `/manage/products` | 商品管理 |
| `/manage/orders` | 订单查看 |

`/manage/*` 是 Vue 管理界面；`/admin/` 仍是 Django Admin，两者不要混淆。前端路由守卫只负责界面跳转，真正的权限校验始终由后端完成。

## Docker 一键启动

这是最简单的完整运行方式。首次启动执行：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

构建完成且所有服务健康后，在浏览器访问：

```text
http://127.0.0.1:8080
```

同一地址下还可以访问：

```text
http://127.0.0.1:8080/api/health/
http://127.0.0.1:8080/admin/
```

Nginx 在构建镜像时生成前端 `dist`，将 `/` 作为 Vue 单页应用入口，把 `/api/` 和 `/admin/` 转发给 Django。默认映射到本机 `8080`，避免 Windows 上常见的 80 端口占用问题。

常用命令：

```powershell
docker compose ps
docker compose logs -f web nginx
docker compose down
```

完整 Docker 操作流程和故障排查见 [docs/docker.md](docs/docker.md)。

## 前后端本地开发

### 1. 准备后端依赖

复制环境变量：

```powershell
Copy-Item .env.example .env
```

确保本机可以访问 MySQL 和 Redis，并将 `.env` 中的连接地址改为实际地址。例如服务均运行在本机时：

```env
DB_HOST=127.0.0.1
DB_PORT=3306
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

如果使用 Compose 中映射到宿主机的 MySQL，端口应为 `3307`。

### 2. 启动 Django

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Django 默认运行在 `http://127.0.0.1:8000`。健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/
```

如需测试订单自动超时取消，再分别启动 Celery Worker 和 Beat：

```powershell
celery -A config worker --loglevel=info --pool=solo
celery -A config beat --loglevel=info
```

### 3. 启动 Vue

另开一个 PowerShell 终端：

```powershell
Set-Location frontend
$env:VITE_DEV_PROXY_TARGET = "http://127.0.0.1:8000"
npm.cmd install
npm.cmd run dev
```

然后访问 `http://127.0.0.1:5173`。Vite 会把浏览器发往 `/api` 的请求代理到 `VITE_DEV_PROXY_TARGET`，因此 Cookie 和 CSRF 流程仍按同源请求工作。若后端就在默认的 `127.0.0.1:8000`，可以不设置该变量。

也可以在 `frontend/.env.local` 中持久化开发代理地址：

```env
VITE_DEV_PROXY_TARGET=http://127.0.0.1:8000
```

## 创建账号

普通用户可以在 `/register` 页面注册，也可以调用 `POST /api/auth/register/`。

业务管理员需要在 Django shell 中创建。Docker 运行时执行：

```powershell
docker compose exec web python manage.py shell
```

本地开发时执行：

```powershell
python manage.py shell
```

然后输入：

```python
from django.contrib.auth import get_user_model

User = get_user_model()
User.objects.create_user(
    username="admin",
    password="Admin123456",
    role=User.Role.ADMIN,
    is_staff=True,
)
```

登录后访问 `/manage`。`role=admin` 用于业务管理界面和管理 API；`is_staff=True` 还允许该账号进入 Django Admin。

## API 概览

认证：

- 通用 JWT 客户端：`POST /api/auth/login/`、`POST /api/auth/refresh/`
- 浏览器客户端：`GET /api/auth/browser/csrf/`、`POST /api/auth/browser/login/`、`POST /api/auth/browser/refresh/`、`POST /api/auth/browser/logout/`
- 注册和当前用户：`POST /api/auth/register/`、`GET /api/auth/me/`

业务资源：

- 商品与分类：`/api/products/`、`/api/categories/`
- 购物车：`/api/cart/`
- 订单：`/api/orders/`
- 管理接口：`/api/admin/categories/`、`/api/admin/products/`

创建订单必须携带 `Idempotency-Key` 请求头。同一用户使用相同 key 和相同请求内容重试时，会返回原订单而不会再次扣减库存。

完整请求、响应及浏览器 Cookie/CSRF 契约见 [docs/api.md](docs/api.md)。

## 测试与构建

后端测试：

```powershell
python manage.py test
```

前端类型检查、单元测试和生产构建：

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
```

前端生产构建输出到 `frontend/dist/`。Docker 构建会自动执行相同的前端安装与构建流程。

测试环境中的 Django 会自动使用 SQLite 和本地内存缓存，避免本机没有 MySQL 或 Redis 时无法执行后端测试；Docker 和正式运行仍使用 MySQL 与 Redis。

## 项目亮点

1. 前后端通过统一的 `{code, message, data}` 契约通信，请求层集中处理分页、业务错误、401 刷新和并发刷新合并。
2. 浏览器只在内存中保存短期 access token，长期 refresh token 放在限定路径的 HttpOnly Cookie 中，登录、刷新和退出均执行 CSRF 校验。
3. 订单创建使用 `transaction.atomic` 与 `select_for_update` 保证库存一致性，避免并发下单导致超卖。
4. Redis 用户级短锁拦截短时间重复提交，数据库幂等记录保证重试返回同一订单。
5. Celery ETA 消息负责到期取消订单，Celery Beat 定时补偿消息队列故障期间的漏投任务。
6. Nginx 同时托管 Vue 构建产物并反向代理 Django，浏览器、API 和后台管理保持同域部署。

## 数据库模型说明

主要表：

- `accounts_user`：自定义用户表，扩展 `phone` 和 `role`
- `products_category`：商品分类
- `products_product`：商品、价格、库存、销量、上下架状态
- `carts_cartitem`：购物车项，约束同一用户同一商品唯一
- `orders_order`：订单主表，记录订单号、用户、金额、状态和幂等信息
- `orders_orderitem`：订单明细，保存商品名称和价格快照

详细说明见 [docs/database.md](docs/database.md)。订单超时取消资料见 [消息队列设计文档](docs/order_timeout_mq_design.md)和[运行文档](docs/order_timeout.md)。

## 面试讲解

这个项目重点展示浏览器认证安全、库存一致性、接口防重复提交和订单超时释放库存。完整讲解稿和常见问题见 [docs/interview.md](docs/interview.md)。

## 可扩展方向

- 收货地址、真实支付和退款流程
- 商品图片上传和对象存储
- 优惠券和订单金额计算
- 秒杀接口和并发压测
- Swagger / OpenAPI 文档及 TypeScript 类型生成
- 操作日志、监控和 CI 测试流水线
