# Docker 使用完整流程

本文档说明如何使用 Docker Compose 启动本项目，并解释 `Dockerfile`、`docker-compose.yml`、`nginx/default.conf`、`scripts/entrypoint.sh` 中每段配置的作用。

适用环境：

- Windows + PowerShell
- 已安装 Docker Desktop
- 项目路径：`D:\AI-learning\E-commerce Backend Project`

## 1. Docker 部署会启动什么

本项目的 `docker-compose.yml` 会启动 6 个服务：

| 服务名 | 容器名 | 作用 | 容器内端口 | 默认映射到本机 |
|---|---|---|---|---|
| `mysql` | `mini_ecommerce_mysql` | MySQL 8.0 数据库 | `3306` | `127.0.0.1:3307` |
| `redis` | `mini_ecommerce_redis` | Redis 缓存、订单锁和 Celery Broker | `6379` | `127.0.0.1:6379` |
| `web` | `mini_ecommerce_web` | Django + Gunicorn | `8000` | 不直接暴露 |
| `celery_worker` | `mini_ecommerce_celery_worker` | 消费订单超时任务 | 无 | 不暴露 |
| `celery_beat` | `mini_ecommerce_celery_beat` | 周期扫描到期订单并补偿入队 | 无 | 不暴露 |
| `nginx` | `mini_ecommerce_nginx` | 反向代理到 Django | `80` | `127.0.0.1:8080` |

访问 API 时建议走 Nginx：

```text
http://127.0.0.1:8080/api/health/
http://127.0.0.1:8080/api/products/
```

## 2. 第一次启动完整流程

### 2.1 进入项目目录

```powershell
cd "D:\AI-learning\E-commerce Backend Project"
```

### 2.2 确认 Docker Desktop 已启动

```powershell
docker version
docker compose version
```

如果 `docker version` 报类似错误：

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

说明 Docker Desktop 没有启动，先手动打开 Docker Desktop，等左下角显示 Docker Engine running 后再执行命令。

### 2.3 创建 `.env`

```powershell
Copy-Item .env.example .env
```

`.env` 用来给 `docker-compose.yml` 注入数据库名、用户、密码、JWT 时间等配置。

推荐把 `.env` 中的 `SECRET_KEY` 改成长一点，例如：

```env
SECRET_KEY=mini-ecommerce-dev-secret-key-change-me-please-2026
```

### 2.4 检查 Compose 配置是否能解析

```powershell
docker compose config
```

如果只想确认有没有语法错误：

```powershell
docker compose config --quiet
```

没有输出表示配置文件语法正常。

### 2.5 构建并启动

前台启动，可以直接看日志：

```powershell
docker compose up --build
```

后台启动：

```powershell
docker compose up --build -d
```

第一次启动时会发生这些事情：

1. 拉取 `mysql:8.0`、`redis:7-alpine`、`nginx:1.27-alpine` 镜像；
2. 根据 `Dockerfile` 构建 Django 镜像；
3. 启动 MySQL 和 Redis；
4. 等 MySQL 和 Redis 健康检查通过；
5. 启动 Django 容器；
6. `entrypoint.sh` 等待 MySQL/Redis 可连接；
7. 自动执行 `python manage.py migrate`；
8. 自动执行 `python manage.py collectstatic --noinput`；
9. Gunicorn 启动 Django；
10. 启动 Celery Worker 和 Celery Beat；
11. Nginx 反向代理到 Django。

### 2.6 查看服务状态

```powershell
docker compose ps
```

正常情况下应该看到：

```text
mini_ecommerce_mysql    healthy
mini_ecommerce_redis    healthy
mini_ecommerce_web      healthy
mini_ecommerce_celery_worker    running
mini_ecommerce_celery_beat      running
mini_ecommerce_nginx    running
```

### 2.7 查看日志

查看全部日志：

```powershell
docker compose logs -f
```

只看 Django：

```powershell
docker compose logs -f web
```

只看订单异步任务：

```powershell
docker compose logs -f celery_worker celery_beat
```

只看 MySQL：

```powershell
docker compose logs -f mysql
```

只看 Nginx：

```powershell
docker compose logs -f nginx
```

### 2.8 验证接口

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/api/health/
```

商品列表：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/api/products/
```

当前 Nginx 本机端口默认是 `8080`，访问地址是：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/api/health/
Invoke-RestMethod http://127.0.0.1:8080/api/products/
```

## 3. `.env` 需要怎么改

当前 `.env.example`：

```env
DEBUG=True
SECRET_KEY=replace-me
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=mini_ecommerce
DB_USER=mini_ecommerce_user
DB_PASSWORD=mini_ecommerce_password
MYSQL_ROOT_PASSWORD=mini_ecommerce_root_password
DB_HOST=mysql
DB_PORT=3306

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
CELERY_BROKER_DB=1

ORDER_PAYMENT_TIMEOUT_SECONDS=1800
ORDER_TIMEOUT_SWEEP_INTERVAL_SECONDS=60
ORDER_TIMEOUT_SWEEP_BATCH_SIZE=200

JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

### 3.1 Docker 运行时，DB_HOST 和 REDIS_HOST 不要改成本机地址

Docker Compose 中，`web` 容器连接数据库时走 Compose 内部网络：

```env
DB_HOST=mysql
REDIS_HOST=redis
```

这里的 `mysql` 和 `redis` 是 `docker-compose.yml` 里的服务名，不是本机域名。

不要在 Docker 场景中改成：

```env
DB_HOST=127.0.0.1
REDIS_HOST=127.0.0.1
```

否则 Django 容器会尝试连接自己容器内部的 `127.0.0.1`，而不是 MySQL/Redis 容器。

### 3.2 修改数据库名、用户、密码

只改 `.env` 即可：

```env
DB_NAME=ecommerce_dev
DB_USER=ecommerce_user
DB_PASSWORD=ecommerce_password_123
MYSQL_ROOT_PASSWORD=root_password_123
```

然后重建：

```powershell
docker compose down
docker compose up --build -d
```

注意：如果之前已经创建过 MySQL volume，改 `.env` 不一定会重新初始化数据库用户和数据库名，因为 MySQL 初始化脚本只在空数据目录第一次启动时执行。

如果你要彻底按新数据库配置重建数据卷：

```powershell
docker compose down -v
docker compose up --build -d
```

`-v` 会删除数据库数据卷，已有数据会丢失。

### 3.3 修改 ALLOWED_HOSTS

默认 Docker Compose 中 `web` 服务会给 Django 注入：

```yaml
ALLOWED_HOSTS: ${ALLOWED_HOSTS:-127.0.0.1,localhost,web,nginx}
```

如果你要用局域网 IP 或域名访问，例如：

```text
http://192.168.1.100/
http://api.example.com/
```

则 `.env` 应写：

```env
ALLOWED_HOSTS=127.0.0.1,localhost,web,nginx,192.168.1.100,api.example.com
```

修改后重启 web 和 nginx：

```powershell
docker compose up -d --force-recreate web nginx
```

### 3.4 修改 CSRF_TRUSTED_ORIGINS

Django Admin 使用浏览器表单登录时会校验请求 Origin。当前 Nginx 暴露在本机 `8080`，因此 `.env` 需要包含：

```env
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8080,http://localhost:8080
```

如果你把 Nginx 端口改成 `8008`，这里也要同步改：

```env
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8008,http://localhost:8008
```

修改后重建 `web` 容器环境：

```powershell
docker compose up -d --force-recreate web nginx
```

## 4. 本机端口已经被占用怎么办

`docker-compose.yml` 中的端口映射格式是：

```yaml
ports:
  - "宿主机端口:容器内端口"
```

例如：

```yaml
ports:
  - "80:80"
```

含义是：把本机 `80` 端口转发到 Nginx 容器的 `80` 端口。

### 4.1 查看本机端口占用

查看 80、8080、3306、3307、6379：

```powershell
netstat -ano | findstr ":80"
netstat -ano | findstr ":8080"
netstat -ano | findstr ":3306"
netstat -ano | findstr ":3307"
netstat -ano | findstr ":6379"
```

查看占用进程：

```powershell
tasklist /FI "PID eq <PID>"
```

示例：

```powershell
tasklist /FI "PID eq 12345"
```

### 4.2 80 端口被占用

本项目已经默认避开 80 端口：

```yaml
nginx:
  ports:
    - "8080:80"
```

如果 `8080` 也被占用，可以继续改成本机其他端口，例如：

```yaml
nginx:
  ports:
    - "8008:80"
```

然后访问：

```text
http://127.0.0.1:8008/api/health/
http://127.0.0.1:8008/api/products/
```

注意：只改左边的本机端口，右边容器内端口仍然保持 `80`。

### 4.3 3306 端口被占用

当前项目已经把 MySQL 映射到本机 `3307`，用于避开本机已有 MySQL 的 `3306`：

```yaml
mysql:
  ports:
    - "3307:3306"
```

如果 `3307` 也被占用，可以继续改成本机其他端口，例如：

```yaml
mysql:
  ports:
    - "3308:3306"
```

这表示：

- 本机用 `127.0.0.1:3308` 访问容器 MySQL；
- 容器内部 MySQL 仍然是 `mysql:3306`；
- `web` 服务中的 `DB_PORT` 不要改，仍然是 `3306`。

也就是说，Docker 内部服务互相访问时不看左边的本机端口。

### 4.4 6379 端口被占用

如果本机 Redis 占用了 6379，把：

```yaml
redis:
  ports:
    - "6379:6379"
```

改成：

```yaml
redis:
  ports:
    - "6380:6379"
```

这表示：

- 本机用 `127.0.0.1:6380` 访问容器 Redis；
- 容器内部 Redis 仍然是 `redis:6379`；
- `web` 服务中的 `REDIS_PORT` 不要改，仍然是 `6379`。

### 4.5 不想从本机直连 MySQL/Redis

如果你只通过 Django API 访问系统，不需要本机工具连接 MySQL/Redis，可以删除 MySQL 和 Redis 的 `ports`：

```yaml
mysql:
  # ports:
  #   - "3307:3306"

redis:
  # ports:
  #   - "6379:6379"
```

这样 MySQL 和 Redis 只在 Docker 内部网络可见，更接近生产部署。

## 5. 常用操作命令

### 启动

```powershell
docker compose up --build
```

后台启动：

```powershell
docker compose up --build -d
```

### 停止但保留数据

```powershell
docker compose down
```

这会删除容器和网络，但保留 MySQL、Redis、静态文件 volume。

### 停止并删除数据

```powershell
docker compose down -v
```

这会删除 volume，MySQL 数据会丢失。只有在你要重置数据库时使用。

### 重新构建应用镜像

修改 Python 依赖、Dockerfile 或项目代码后：

```powershell
docker compose build web celery_worker celery_beat
docker compose up -d web celery_worker celery_beat
```

或者：

```powershell
docker compose up --build -d
```

### 进入 Django 容器

```powershell
docker compose exec web sh
```

### 执行 Django 命令

```powershell
docker compose exec web python manage.py check
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py test
```

### 查看数据库

进入 MySQL：

```powershell
docker compose exec mysql mysql -uroot -p
```

输入 `.env` 中的：

```env
MYSQL_ROOT_PASSWORD=mini_ecommerce_root_password
```

查看数据库：

```sql
SHOW DATABASES;
USE mini_ecommerce;
SHOW TABLES;
```

使用业务用户登录：

```powershell
docker compose exec mysql mysql -umini_ecommerce_user -p mini_ecommerce
```

### 查看 Redis

```powershell
docker compose exec redis redis-cli
```

测试：

```redis
PING
KEYS *
```

查看商品详情缓存示例：

```redis
GET product:detail:1
```

查看订单锁示例：

```redis
GET lock:order:create:user:1:idempotency:create-order-001
```

## 6. API 操作流程示例

以下命令假设 Nginx 端口是默认 `80`。

### 6.1 注册普通用户

```powershell
$body = @{
  username = "testuser"
  password = "Test123456"
  password_confirm = "Test123456"
  email = "test@example.com"
  phone = "13800000000"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8080/api/auth/register/" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

### 6.2 登录并保存 Token

```powershell
$loginBody = @{
  username = "testuser"
  password = "Test123456"
} | ConvertTo-Json

$login = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8080/api/auth/login/" `
  -Method Post `
  -ContentType "application/json" `
  -Body $loginBody

$access = $login.data.access
$headers = @{ Authorization = "Bearer $access" }
```

### 6.3 创建管理员

```powershell
docker compose exec web python manage.py shell
```

在 shell 中执行：

```python
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.create_user(
    username="admin",
    password="Admin123456",
    role="admin",
    is_staff=True,
)
```

### 6.4 管理员登录

```powershell
$adminBody = @{
  username = "admin"
  password = "Admin123456"
} | ConvertTo-Json

$adminLogin = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8080/api/auth/login/" `
  -Method Post `
  -ContentType "application/json" `
  -Body $adminBody

$adminHeaders = @{ Authorization = "Bearer $($adminLogin.data.access)" }
```

### 6.5 创建分类

```powershell
$categoryBody = @{
  name = "Laptop"
  slug = "laptop"
  is_active = $true
} | ConvertTo-Json

$category = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8080/api/admin/categories/" `
  -Method Post `
  -Headers $adminHeaders `
  -ContentType "application/json" `
  -Body $categoryBody
```

### 6.6 创建商品

```powershell
$productBody = @{
  category = $category.data.id
  name = "MacBook Pro 14"
  slug = "macbook-pro-14"
  description = "Apple laptop"
  price = "12999.00"
  stock = 50
  status = "active"
  image_url = "https://example.com/macbook.jpg"
} | ConvertTo-Json

$product = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8080/api/admin/products/" `
  -Method Post `
  -Headers $adminHeaders `
  -ContentType "application/json" `
  -Body $productBody
```

### 6.7 普通用户加入购物车

```powershell
$cartBody = @{
  product_id = $product.data.id
  quantity = 2
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8080/api/cart/items/" `
  -Method Post `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $cartBody
```

### 6.8 创建订单

```powershell
$orderBody = @{
  remark = "请尽快发货"
} | ConvertTo-Json

$order = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8080/api/orders/" `
  -Method Post `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $orderBody
```

### 6.9 支付订单

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8080/api/orders/$($order.data.id)/pay/" `
  -Method Post `
  -Headers $headers
```

如果要测试取消订单，应创建一个新订单并在支付前取消：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8080/api/orders/$($order.data.id)/cancel/" `
  -Method Post `
  -Headers $headers
```

## 7. `docker-compose.yml` 代码解释

### 7.1 services

```yaml
services:
```

`services` 是 Compose 的核心节点。下面每一个子节点都是一个容器服务，例如 `mysql`、`redis`、`web`、`nginx`。

### 7.2 mysql 服务

```yaml
mysql:
  image: mysql:8.0
  container_name: mini_ecommerce_mysql
  restart: unless-stopped
```

- `image: mysql:8.0`：使用官方 MySQL 8.0 镜像。
- `container_name`：固定容器名，方便 `docker logs` 或 Docker Desktop 中识别。
- `restart: unless-stopped`：容器异常退出时自动重启，除非你手动停止。

```yaml
environment:
  MYSQL_DATABASE: ${DB_NAME:-mini_ecommerce}
  MYSQL_USER: ${DB_USER:-mini_ecommerce_user}
  MYSQL_PASSWORD: ${DB_PASSWORD:-mini_ecommerce_password}
  MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-mini_ecommerce_root_password}
```

这些是 MySQL 官方镜像支持的初始化变量：

- `MYSQL_DATABASE`：第一次启动时自动创建的数据库。
- `MYSQL_USER`：第一次启动时自动创建的普通用户。
- `MYSQL_PASSWORD`：普通用户密码。
- `MYSQL_ROOT_PASSWORD`：root 用户密码。

`${DB_NAME:-mini_ecommerce}` 的意思是：如果 `.env` 中配置了 `DB_NAME`，就用 `.env` 的值；否则使用默认值 `mini_ecommerce`。

```yaml
command:
  - --character-set-server=utf8mb4
  - --collation-server=utf8mb4_unicode_ci
```

指定 MySQL 默认字符集为 `utf8mb4`，支持中文和 emoji。

```yaml
ports:
  - "3307:3306"
```

把本机 3307 映射到容器 3306。只影响你从宿主机直连 MySQL，不影响 Docker 内部服务访问。

```yaml
volumes:
  - mysql_data:/var/lib/mysql
```

使用 Docker volume 持久化 MySQL 数据。删除容器不会丢数据库，只有执行 `docker compose down -v` 才会删 volume。

```yaml
healthcheck:
  test: ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 -uroot -p$${MYSQL_ROOT_PASSWORD} --silent"]
```

健康检查会周期性执行 `mysqladmin ping`。只有 MySQL healthy 后，`web` 才会启动。

### 7.3 redis 服务

```yaml
redis:
  image: redis:7-alpine
  container_name: mini_ecommerce_redis
  restart: unless-stopped
  command: ["redis-server", "--appendonly", "yes"]
```

- 使用轻量的 Redis Alpine 镜像。
- `--appendonly yes` 开启 AOF 持久化，比纯内存更稳。

```yaml
ports:
  - "6379:6379"
volumes:
  - redis_data:/data
```

- `ports` 允许宿主机通过 `127.0.0.1:6379` 访问 Redis。
- `redis_data` 保存 Redis 持久化数据。

```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
```

执行 `redis-cli ping`，返回 `PONG` 表示 Redis 可用。

### 7.4 web 服务

```yaml
web:
  build: .
  container_name: mini_ecommerce_web
  restart: unless-stopped
```

- `build: .` 表示用当前目录的 `Dockerfile` 构建 Django 镜像。
- 容器名固定为 `mini_ecommerce_web`。

```yaml
environment:
  DEBUG: ${DEBUG:-True}
  SECRET_KEY: ${SECRET_KEY:-dev-secret-key-change-me-32-characters-minimum}
  ALLOWED_HOSTS: ${ALLOWED_HOSTS:-127.0.0.1,localhost,web,nginx}
  DB_NAME: ${DB_NAME:-mini_ecommerce}
  DB_USER: ${DB_USER:-mini_ecommerce_user}
  DB_PASSWORD: ${DB_PASSWORD:-mini_ecommerce_password}
  DB_HOST: mysql
  DB_PORT: 3306
  REDIS_HOST: redis
  REDIS_PORT: 6379
```

这些环境变量会被 `config/settings.py` 读取。

重点：

- `DB_HOST: mysql` 是 Compose 服务名，不是本机地址。
- `REDIS_HOST: redis` 是 Compose 服务名。
- `DB_PORT` 和 `REDIS_PORT` 是容器内部端口，一般不随宿主机端口映射变化。

```yaml
depends_on:
  mysql:
    condition: service_healthy
  redis:
    condition: service_healthy
```

表示 `web` 等 MySQL 和 Redis 通过健康检查后再启动。

```yaml
expose:
  - "8000"
```

`expose` 只暴露给 Docker 内部网络，不映射到宿主机。外部用户不直接访问 `web:8000`，而是访问 Nginx。

```yaml
volumes:
  - .:/app
  - static_volume:/app/staticfiles
```

- `.:/app` 表示把当前本地项目目录挂载到容器 `/app`。本地修改 Python 代码后，容器内能直接看到最新代码。
- `static_volume:/app/staticfiles` 保存 Django 收集出来的静态文件，Nginx 通过同一个 volume 读取静态文件。

注意：当前 `web` 仍然使用 Gunicorn，不会像 Django `runserver` 那样自动重载 Python 进程。修改 Python 代码后建议重启 `web`：

```powershell
docker compose restart web
```

如果修改了 `requirements.txt`、`Dockerfile` 或系统依赖，仍然需要重新构建镜像：

```powershell
docker compose up --build -d web
```

```yaml
healthcheck:
  test:
    [
      "CMD-SHELL",
      "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/', timeout=5).read()\"",
    ]
```

健康检查访问 Django 容器内部的 `/api/health/`，确认 Gunicorn 和 Django 已经可用。

### 7.5 nginx 服务

```yaml
nginx:
  image: nginx:1.27-alpine
  container_name: mini_ecommerce_nginx
  restart: unless-stopped
```

使用 Nginx 作为入口，所有外部 API 请求先到 Nginx，再转发到 Django。

```yaml
depends_on:
  web:
    condition: service_healthy
```

Nginx 等 Django healthy 后启动。

```yaml
ports:
  - "8080:80"
```

把本机 8080 映射到 Nginx 容器 80。这样可以避开 Windows 上常见的 80 端口占用或系统保留问题。

```yaml
volumes:
  - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
  - static_volume:/app/staticfiles:ro
```

- 第一行把项目里的 Nginx 配置挂载到容器中。
- `:ro` 表示只读挂载。
- 第二行让 Nginx 读取 Django 收集出来的静态文件。

### 7.6 volumes

```yaml
volumes:
  mysql_data:
  redis_data:
  static_volume:
```

声明 Docker volume：

- `mysql_data`：保存 MySQL 数据。
- `redis_data`：保存 Redis AOF 数据。
- `static_volume`：保存 Django 静态文件。

## 8. `Dockerfile` 代码解释

```dockerfile
FROM python:3.12-slim
```

使用官方 Python 3.12 slim 镜像，体积比完整镜像小。

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
```

- 不生成 `.pyc` 文件。
- Python 日志直接输出，方便 `docker compose logs` 查看。

```dockerfile
WORKDIR /app
```

设置容器工作目录。

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*
```

安装编译 `mysqlclient` 所需的系统依赖。

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
```

先复制依赖文件并安装依赖，利用 Docker 构建缓存。只改业务代码时，不需要重新安装依赖。

```dockerfile
COPY . .
RUN sed -i 's/\r$//' /app/scripts/entrypoint.sh \
    && chmod +x /app/scripts/entrypoint.sh
```

复制项目代码，并处理 Windows CRLF 换行，避免 Linux 容器中脚本报错。

```dockerfile
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
```

容器启动时先执行 `entrypoint.sh`，脚本结束后再执行 Gunicorn 命令。

## 9. `entrypoint.sh` 代码解释

脚本做三件事：

1. 等待 MySQL 和 Redis 端口可连接；
2. 执行数据库迁移；
3. 收集静态文件并启动 Gunicorn。

关键命令：

```sh
python manage.py migrate
python manage.py collectstatic --noinput
exec "$@"
```

`exec "$@"` 会执行 Dockerfile 中的 `CMD`，也就是：

```sh
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

## 10. Nginx 配置解释

```nginx
upstream django_app {
    server web:8000;
}
```

定义后端 Django 服务地址。`web` 是 Compose 服务名，`8000` 是 Gunicorn 监听端口。

```nginx
location /static/ {
    alias /app/staticfiles/;
    expires 7d;
    access_log off;
}
```

静态文件直接由 Nginx 返回，不经过 Django。

```nginx
location / {
    proxy_pass http://django_app;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

其他请求全部反向代理到 Django，并把真实 Host、IP、协议传给 Django。

## 11. 常见问题排查

### Docker Engine 没启动

错误：

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

处理：

1. 打开 Docker Desktop；
2. 等待 Docker Engine running；
3. 重新执行 `docker compose up --build`。

### Nginx 启动失败，提示端口占用

如果错误里是 `0.0.0.0:80`，说明 Compose 仍在使用 80，建议改成：

```yaml
ports:
  - "8080:80"
```

如果错误里是 `0.0.0.0:8080`，说明 8080 也被占用，继续改成：

```yaml
ports:
  - "8008:80"
```

然后访问 `http://127.0.0.1:8008/`。

### MySQL 初始化后修改密码不生效

原因：`mysql_data` volume 已经存在，MySQL 不会重新执行初始化。

处理：

```powershell
docker compose down -v
docker compose up --build -d
```

注意：这会删除数据库数据。

### web 容器一直重启

查看日志：

```powershell
docker compose logs -f web
```

常见原因：

- MySQL 没有 healthy；
- `.env` 中数据库密码和已存在 volume 中的不一致；
- Python 依赖安装失败；
- migration 报错；
- `ALLOWED_HOSTS` 未包含当前访问域名。

### 商品详情缓存没看到

商品详情缓存只有访问商品详情后才会写入：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/api/products/1/
```

然后进入 Redis：

```powershell
docker compose exec redis redis-cli
KEYS product:detail:*
```

### 创建订单重复提交锁怎么观察

订单锁 key 格式：

```text
lock:order:create:user:{user_id}:idempotency:{idempotency_key}
```

由于锁 TTL 只有 10 秒，正常情况下很快消失。可以在接口请求期间或通过测试方式观察。

## 12. 推荐开发流程

日常开发建议：

```powershell
docker compose up -d mysql redis
python manage.py runserver
```

这样本机 Django 连接容器里的 MySQL 和 Redis。此时 `.env` 应改为：

```env
DB_HOST=127.0.0.1
DB_PORT=3307
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

如果 MySQL/Redis 本机映射端口改成了 `3308`、`6380`：

```env
DB_HOST=127.0.0.1
DB_PORT=3308
REDIS_HOST=127.0.0.1
REDIS_PORT=6380
```

完整容器化验证建议：

```powershell
docker compose down
docker compose up --build -d
docker compose logs -f web
```

测试建议：

```powershell
python manage.py test
docker compose exec web python manage.py check
```
