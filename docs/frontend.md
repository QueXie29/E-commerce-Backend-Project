# Vue 前端设计与开发说明

## 1. 定位与技术选型

`frontend/` 是与 Django REST API 配套的 Vue 3 单页应用，覆盖普通用户商城和业务管理界面。前端不直接访问数据库，也不复制后端业务规则；库存、权限、订单状态和金额均以后端响应为准。

主要依赖：

- Vue 3 + TypeScript + Vite
- Vue Router：页面路由和访问守卫
- Pinia：认证用户等少量全局客户端状态
- TanStack Vue Query：服务端数据、缓存和请求状态
- Element Plus：表单、弹窗、分页等交互组件
- Vitest + Vue Testing Library：单元和组件测试

## 2. 目录结构

```text
frontend/
├─ src/
│  ├─ app/
│  │  ├─ layouts/          # 商城公共布局
│  │  ├─ instances.ts      # Pinia 和 QueryClient 实例
│  │  └─ router.ts         # 路由表与认证/管理员守卫
│  ├─ components/
│  │  └─ storefront/       # 商品卡片、图片、订单状态等复用组件
│  ├─ shared/
│  │  └─ api/              # HTTP 客户端、领域请求、契约和错误类型
│  ├─ stores/
│  │  └─ auth.ts           # 当前用户与认证初始化状态
│  ├─ styles/              # 全局设计变量和基础样式
│  ├─ test/                # Vitest 公共初始化
│  ├─ views/
│  │  ├─ account/          # 个人中心
│  │  ├─ auth/             # 登录与注册
│  │  ├─ management/       # 管理端页面
│  │  └─ storefront/       # 商品、购物车、结算和订单页面
│  ├─ App.vue
│  └─ main.ts
├─ index.html
├─ package.json
├─ tsconfig*.json
└─ vite.config.ts
```

`shared/api/client.ts` 是前后端 HTTP 边界；页面只调用 `auth.ts`、`products.ts`、`cart.ts`、`orders.ts` 和 `management.ts` 暴露的领域函数，不自行拼接鉴权和响应解包逻辑。

## 3. 页面与路由

普通用户路由使用商城公共布局：

| 路由 | 页面 | 访问要求 |
|---|---|---|
| `/` | 商品列表、关键词/分类/价格/排序筛选 | 公开 |
| `/products/:id` | 商品详情、加入购物车 | 公开；加入购物车需登录 |
| `/login` | 登录 | 仅未登录用户 |
| `/register` | 注册 | 仅未登录用户 |
| `/account` | 当前账号信息 | 登录 |
| `/cart` | 购物车 | 登录 |
| `/checkout` | 确认订单和备注 | 登录 |
| `/orders` | 当前用户订单列表 | 登录 |
| `/orders/:id` | 订单详情、支付和取消 | 登录 |

业务管理员路由：

| 路由 | 页面 |
|---|---|
| `/manage` | 管理概览 |
| `/manage/categories` | 分类管理 |
| `/manage/products` | 商品管理 |
| `/manage/orders` | 所有订单查看 |

路由守卫在首次导航前恢复浏览器会话。需要登录的页面会跳转到 `/login?redirect=原地址`；已登录用户不能再次进入登录或注册页；非 `admin` 角色不能进入 `/manage/*`。

路由守卫仅改善用户体验，不能替代服务器鉴权。管理 API 仍由 Django 的管理员权限类校验。`/manage/*` 是 Vue 业务管理界面，`/admin/` 是 Django Admin。

## 4. 状态边界

前端按状态来源划分管理方式：

| 状态 | 管理方式 | 示例 |
|---|---|---|
| 服务端状态 | TanStack Vue Query | 商品、分类、购物车、订单 |
| 认证客户端状态 | Pinia | 当前用户、是否已初始化、登录忙碌状态 |
| 可分享的列表条件 | Vue Router query | 关键词、分类、价格、排序、页码 |
| 页面临时状态 | `ref` / `reactive` | 表单输入、弹窗开关、提交中状态 |
| 下单重试意图 | `sessionStorage` | 幂等键及对应的订单备注、购物车签名 |

不把商品、购物车和订单复制进 Pinia，可避免客户端副本与服务端缓存不一致。业务写操作成功后，由页面刷新或失效对应的 Vue Query 查询。

全局 `QueryClient` 默认配置：

- 查询数据 30 秒内视为新鲜
- 窗口重新获得焦点时不自动请求
- HTTP 4xx 和业务错误不重试
- 可恢复的服务端/网络查询最多重试 2 次
- mutation 默认不自动重试

## 5. 统一请求层

所有 API 请求使用相对路径 `/api/...`。`createApiClient` 统一处理：

1. 补齐 `/api` 前缀和查询参数。
2. 设置 `Accept: application/json`，并在需要时序列化 JSON 请求体。
3. 从内存读取 access token，写入 `Authorization: Bearer ...`。
4. 使用 `credentials: same-origin` 携带同源 Cookie。
5. 解析后端统一的 `{code, message, data}` 响应并直接返回 `data`。
6. 将 HTTP 错误和业务错误转换为带 `status`、`code`、`data` 的 `ApiError`。
7. 认证请求收到 `401` 后刷新一次 access token，再重放原请求一次。

同时到达的多个 `401` 会共享同一个 `refreshPromise`，CSRF 初始化也会共享同一个 `csrfPromise`。这可以避免并发请求重复刷新令牌或产生刷新轮换竞争。

## 6. 浏览器认证

浏览器前端不使用会在 JSON 中返回 refresh token 的通用登录接口，而使用 `/api/auth/browser/*`：

1. `GET /api/auth/browser/csrf/` 初始化可读的 `csrftoken` Cookie。
2. `POST /api/auth/browser/login/` 携带 `X-CSRFToken`，响应返回 access token 并设置 HttpOnly refresh Cookie。
3. access token 只保存在 `session.ts` 的模块内存中，不写入 `localStorage` 或 `sessionStorage`。
4. 页面刷新后，Pinia auth store 调用浏览器刷新接口，再调用 `/api/auth/me/` 恢复用户。
5. 退出时调用浏览器 logout，服务端注销并删除 refresh Cookie，前端清空内存 token 和用户状态。

这样可以降低长期令牌被页面脚本直接读取的风险。CSRF Cookie、请求头、Cookie 路径和相关环境变量详见 [API 文档](api.md)。

## 7. 下单幂等

每个新的下单意图都需要一个新的 `Idempotency-Key`。前端的 `orders.ts` 将当前意图保存在当前标签页的 `sessionStorage`：

```text
key: mini-mall:checkout-intent
value: { key: crypto.randomUUID(), remark: 当前备注, cartSignature: 当前勾选项签名 }
```

处理规则：

- 第一次提交当前备注与购物车组合时生成 UUID
- 网络超时或响应丢失后，备注和购物车均未变化的重试会复用原 UUID
- 备注或购物车内容发生变化时视为新的下单意图并生成新 UUID
- 订单成功创建后删除该意图
- 用户明确放弃当前结算时可以删除该意图

服务端还会组合 Redis 用户级锁、订单请求摘要和数据库唯一约束。前端按钮防重复点击只改善交互，不是幂等保证。

金额字段使用后端返回的十进制字符串展示，不使用 JavaScript 浮点数重新计算订单权威金额；订单倒计时也只用于展示，能否支付最终由服务端校验决定。

## 8. 本地开发

先在项目根目录启动 Django，使其监听 `http://127.0.0.1:8000`。再开一个 PowerShell 终端：

```powershell
Set-Location frontend
$env:VITE_DEV_PROXY_TARGET = "http://127.0.0.1:8000"
npm.cmd install
npm.cmd run dev
```

浏览器访问：

```text
http://127.0.0.1:5173
```

`vite.config.ts` 将 `/api` 代理到 `VITE_DEV_PROXY_TARGET`。变量未设置时默认使用 `http://127.0.0.1:8000`。也可以创建不提交到版本库的 `frontend/.env.local`：

```env
VITE_DEV_PROXY_TARGET=http://127.0.0.1:8000
```

访问前端时应始终使用同一种主机名，例如始终使用 `127.0.0.1`，不要在 `localhost` 和 `127.0.0.1` 之间混用，以免 Cookie 主机不一致。

## 9. 测试与生产构建

在 `frontend/` 下执行：

```powershell
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
```

各命令含义：

- `npm.cmd run typecheck`：执行 Vue/TypeScript 类型检查
- `npm.cmd test`：以单次运行模式执行 Vitest 测试
- `npm.cmd run test:watch`：开发期间监听并重复执行 Vitest
- `npm.cmd run build`：先做类型检查，再生成 `dist/`
- `npm.cmd run preview`：本地预览已构建的静态文件

后端测试仍在项目根目录执行：

```powershell
python manage.py test
```

## 10. Docker 与 Nginx 部署

`nginx/Dockerfile` 使用多阶段构建：

1. Node 阶段根据 `package-lock.json` 执行 `npm ci`。
2. 执行 `npm run build` 生成 Vue `dist/`。
3. 将构建产物复制进 Nginx 镜像的 `/usr/share/nginx/html/`。

Nginx 路由职责：

| 路径 | 处理方式 |
|---|---|
| `/assets/` | 直接返回带长期 immutable 缓存的前端静态资源 |
| `/index.html` | 直接返回且禁止缓存，方便发布新版本 |
| `/api/` | 反向代理到 Django `web:8000` |
| `/admin/` | 反向代理到 Django Admin |
| 其他路径 | 优先读取静态文件，否则回退到 `index.html` 交给 Vue Router |

因此生产环境中的页面、API、CSRF Cookie 和 refresh Cookie 位于同一个站点。完整启动方式：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

访问 `http://127.0.0.1:8080`。正式使用 HTTPS 时，应将 `JWT_REFRESH_COOKIE_SECURE=True`，并把实际 HTTPS 来源加入 `CSRF_TRUSTED_ORIGINS`。
