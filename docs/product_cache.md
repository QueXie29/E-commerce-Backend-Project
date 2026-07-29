# 商品列表缓存与商品详情缓存说明

本文档基于当前项目源码，集中说明 `apps/products` 中的两套 Redis 缓存：

- 商品列表缓存：缓存 `GET /api/products/` 的完整分页响应。
- 商品详情缓存：缓存 `GET /api/products/{id}/` 的序列化商品详情。

重点介绍缓存什么时候参与请求、缓存键如何生成、数据如何写入、哪些业务操作会让缓存失效，以及当前实现没有覆盖的边界。

相关源码：

- [`apps/products/services.py`](../apps/products/services.py)：缓存键、读写、删除和失效函数。
- [`apps/products/views.py`](../apps/products/views.py)：商品及分类 API 中的缓存触发逻辑。
- [`apps/products/admin.py`](../apps/products/admin.py)：Django Admin 中的缓存失效逻辑。
- [`apps/orders/services.py`](../apps/orders/services.py)：下单和取消订单造成的商品缓存失效。
- [`config/settings.py`](../config/settings.py)：Redis 和测试缓存后端配置。

---

## 1. 两套缓存总览

| 项目 | 商品列表缓存 | 商品详情缓存 |
| --- | --- | --- |
| 缓存键 | `product:list:v{version}:{digest}` | `product:detail:{product_id}` |
| 缓存内容 | 完整分页响应 `{code, message, data}` | `ProductDetailSerializer` 生成的详情数据 |
| TTL | 300 秒 | 300 秒 |
| 公共读取者 | 匿名用户、普通登录用户 | 匿名用户、普通登录用户 |
| 管理员请求 | 绕过公共列表缓存 | 绕过公共详情缓存的读取和写入 |
| 失效方式 | 递增版本号，旧键等待 TTL 自动过期 | `delete()` 删除单个键，或 `delete_many()` 批量删除 |
| Redis 故障策略 | fail-open，退回数据库查询 | fail-open，退回数据库查询 |

生产环境使用 Redis：

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    }
}
```

执行测试时，项目改用进程内的 `LocMemCache`，避免测试依赖真实 Redis：

```python
if "test" in sys.argv:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "mini-ecommerce-tests",
        }
    }
```

---

## 2. 为什么需要两套不同粒度的缓存

列表接口和详情接口面对的数据组合不同，因此采用了不同的缓存粒度。

商品列表接口受以下因素影响：

- 分类筛选；
- 关键词搜索；
- 最低价、最高价；
- 排序方式；
- 页码和每页数量；
- 请求来源的协议、主机和端口。

同一组参数对应一个列表缓存键。任何会改变公共商品列表内容的业务操作，都通过递增列表版本号使整组旧列表缓存失效。

商品详情接口只由商品 ID 定位，因此使用一个简单的 `product:detail:{product_id}` 键。商品自身或它所属分类发生变化时，可以精确删除一个或一批详情键。

需要特别注意：`ProductDetailSerializer` 会把分类信息嵌入商品详情：

```python
class ProductDetailSerializer(serializers.ModelSerializer):
    category = ProductCategorySerializer(read_only=True)
```

嵌套的分类数据包含：

```python
fields = ("id", "name", "slug")
```

所以分类名称或 `slug` 被修改后，即使商品表本身没有变化，已经缓存的商品详情也会过期，必须清理该分类下所有商品的详情缓存。

---

## 3. 商品列表缓存

### 3.1 核心常量

```python
PRODUCT_LIST_CACHE_KEY = "product:list:v{version}:{digest}"
PRODUCT_LIST_CACHE_TTL = 300
PRODUCT_LIST_CACHE_VERSION_KEY = "product:list:version"
PRODUCT_LIST_CACHE_ALLOWED_PARAMS = (
    "category",
    "keyword",
    "min_price",
    "max_price",
    "ordering",
    "page",
    "page_size",
)
```

含义如下：

- `product:list:version` 保存当前列表缓存版本号，不设置过期时间。
- `v{version}` 把版本号放进每一个列表数据键。
- `{digest}` 是请求来源和有效查询参数计算出的 MD5 摘要。
- 每个实际列表响应只保留 300 秒。

例如：

```text
product:list:version = 7
product:list:v7:9bd97d0c55f91b9c92e871fdb1651bba
```

MD5 在这里不是用来保存密码或提供安全性，只是把较长的规范化参数压缩成长度固定的 Redis 键后缀。

### 3.2 列表缓存什么时候触发

入口位于 `ProductViewSet.list()`：

```python
def list(self, request, *args, **kwargs):
    if is_admin_user(request.user):
        return super().list(request, *args, **kwargs)

    origin = f"{request.scheme}://{request.get_host()}"
    cache_key = make_product_list_cache_key(request.query_params, origin)
    cached_data = get_product_list_cache(cache_key)
    if cached_data is not None:
        canonicalize_product_list_pagination_links(cached_data)
        return Response(cached_data)

    response = super().list(request, *args, **kwargs)
    if response.status_code == status.HTTP_200_OK:
        canonicalize_product_list_pagination_links(response.data)
        set_product_list_cache(cache_key, response.data)
    return response
```

触发规则：

1. 请求必须进入公共商品列表接口 `GET /api/products/`。
2. 匿名用户和普通登录用户都会使用同一套公共缓存。
3. 管理员用户直接查询数据库，不读取也不写入公共列表缓存。
4. 只有数据库查询最终返回 HTTP 200 时才写入缓存。
5. 参数校验失败形成的 HTTP 400 响应不会被缓存。

管理员绕过公共缓存是因为管理员可以看到下架商品，而公共缓存只应保存“已上架商品 + 启用分类”的结果。若管理员复用或写入公共缓存，就可能把后台可见数据暴露给普通用户。

### 3.3 缓存键如何创建

#### 第一步：读取或初始化版本号

```python
def get_product_list_cache_version():
    try:
        version = cache.get(PRODUCT_LIST_CACHE_VERSION_KEY)
        if version is None:
            cache.add(PRODUCT_LIST_CACHE_VERSION_KEY, 1, timeout=None)
            version = cache.get(PRODUCT_LIST_CACHE_VERSION_KEY)
        return int(version if version is not None else 1)
    except Exception as exc:
        logger.warning("Failed to read product list cache version: %s", exc)
        return None
```

- 先从 Redis 读取 `product:list:version`。
- 不存在时使用 `cache.add()` 初始化为 1。
- `add()` 只会在键不存在时写入，多个并发请求同时初始化时不会互相覆盖。
- `timeout=None` 表示版本键长期保存，直到 Redis 数据被主动清理或 Redis 存储被重建。
- Redis 异常时返回 `None`，后续逻辑会放弃本次缓存，继续走数据库。

#### 第二步：规范化有效查询参数

```python
def normalize_product_list_query_params(query_params):
    normalized = []
    for name in PRODUCT_LIST_CACHE_ALLOWED_PARAMS:
        value = query_params.get(name)
        if value in (None, ""):
            continue
        normalized.append((name, str(value)))
    return normalized
```

只保留真正影响查询结果的参数：

| 参数 | 对列表结果的影响 |
| --- | --- |
| `category` | 按分类 ID 筛选 |
| `keyword` | 在名称和描述中搜索 |
| `min_price` | 最低价格 |
| `max_price` | 最高价格 |
| `ordering` | 按创建时间、价格或销量排序 |
| `page` | 页码 |
| `page_size` | 每页数量 |

以下内容不会制造新的缓存分片：

- 未知参数，例如 `foo=bar`；
- 空参数，例如 `keyword=`；
- 查询参数在 URL 中的排列顺序。

函数按 `PRODUCT_LIST_CACHE_ALLOWED_PARAMS` 的固定顺序组织参数，所以：

```text
?category=1&ordering=-price&page=2
?page=2&ordering=-price&category=1
```

会生成相同的缓存键。

#### 第三步：加入请求来源并计算摘要

```python
def make_product_list_cache_key(query_params, origin: str):
    version = get_product_list_cache_version()
    if version is None:
        return None

    normalized = json.dumps(
        {
            "origin": origin,
            "params": normalize_product_list_query_params(query_params),
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()
    return PRODUCT_LIST_CACHE_KEY.format(version=version, digest=digest)
```

`origin` 的格式为：

```python
origin = f"{request.scheme}://{request.get_host()}"
```

例如 `http://localhost:8080` 和 `https://shop.example.com` 会得到不同的缓存键。原因是分页响应中的 `next`、`previous` 是绝对 URL，不同域名或协议的响应不能错误地共用。

### 3.4 如何读取缓存

```python
def get_product_list_cache(cache_key):
    if cache_key is None:
        return None
    try:
        return cache.get(cache_key)
    except Exception as exc:
        logger.warning("Failed to read product list cache: %s", exc)
        return None
```

返回值有三种情况：

- 返回字典：缓存命中，接口直接返回该完整响应。
- 返回 `None`：缓存未命中，继续查询数据库。
- Redis 抛出异常：记录 warning 并返回 `None`，同样继续查询数据库。

缓存命中时不会再次执行 ORM 查询、分页和序列化。

### 3.5 如何创建并存入缓存

缓存未命中后，`super().list()` 完成下面的工作：

1. `get_queryset()` 取得商品 QuerySet。
2. 非管理员只保留 `status=active` 且 `category.is_active=True` 的商品。
3. `apply_product_filters()` 应用筛选和排序。
4. 分页器生成当前页数据。
5. `ProductListSerializer` 序列化商品。
6. 分页器形成完整的 `{code, message, data}` 响应。

随后只缓存成功响应：

```python
if response.status_code == status.HTTP_200_OK:
    canonicalize_product_list_pagination_links(response.data)
    set_product_list_cache(cache_key, response.data)
```

真正写入 Redis 的函数为：

```python
def set_product_list_cache(cache_key, data) -> None:
    if cache_key is None:
        return None
    try:
        cache.set(cache_key, data, timeout=PRODUCT_LIST_CACHE_TTL)
    except Exception as exc:
        logger.warning("Failed to write product list cache: %s", exc)
    return None
```

- `cache_key is None` 说明版本号读取失败，本次直接不缓存。
- `cache.set()` 会覆盖同名键并设置 300 秒 TTL。
- 写缓存失败不会改变已经生成的 HTTP 响应。

### 3.6 为什么要规范化分页链接

分页数据中包含：

```json
{
  "data": {
    "next": "http://localhost/api/products/?ordering=-price&page=2&page_size=10",
    "previous": null
  }
}
```

项目会在写入前和缓存命中后调用：

```python
canonicalize_product_list_pagination_links(payload)
```

它会清除分页链接里的未知参数、空参数和无效重复参数，只保留实际支持的筛选、排序、分页参数。写入前处理保证新缓存干净；命中后再次处理可以兼容以前已经保存的旧格式缓存。

### 3.7 列表缓存如何“删除”

列表缓存没有扫描和逐个删除 `product:list:*`，而是采用版本号递增：

```python
def invalidate_product_list_cache():
    try:
        cache.add(PRODUCT_LIST_CACHE_VERSION_KEY, 1, timeout=None)
        return cache.incr(PRODUCT_LIST_CACHE_VERSION_KEY)
    except Exception as exc:
        logger.warning("Failed to invalidate product list cache: %s", exc)
        return None
```

假设当前缓存为：

```text
product:list:version = 7
product:list:v7:aaa...
product:list:v7:bbb...
```

失效后：

```text
product:list:version = 8
```

后续请求只会生成或读取 `product:list:v8:*`。旧的 `v7` 键虽然仍在 Redis 中，但已经没有代码会访问它们，并会在各自的 300 秒 TTL 到期后自动删除。

这种方案的优点：

- 不使用 Redis `KEYS` 或通配符扫描；
- 一次 `INCR` 就能让所有筛选、排序、分页组合同时失效；
- 失效速度不受旧缓存数量影响；
- `cache.incr()` 是 Redis 原子递增操作，适合并发请求。

代价是旧键会在 Redis 中继续存在最多 300 秒，但它们已经是不可访问的逻辑失效数据。

### 3.8 哪些场景会让列表缓存失效

| 业务入口 | 操作 | 是否递增列表版本 | 代码位置 |
| --- | --- | --- | --- |
| 管理商品 API | 创建商品 | 是 | `AdminProductViewSet.perform_create()` |
| 管理商品 API | 修改商品 | 是 | `AdminProductViewSet.perform_update()` |
| 管理商品 API | 商品软删除/下架 | 是 | `AdminProductViewSet.perform_destroy()` |
| 管理分类 API | 创建分类 | 是 | `AdminCategoryViewSet.perform_create()` |
| 管理分类 API | 修改分类 | 是 | `AdminCategoryViewSet.perform_update()` |
| 管理分类 API | 分类软删除/停用 | 是 | `AdminCategoryViewSet.perform_destroy()` |
| 创建订单 | 扣减库存、增加销量 | 是，事务提交后 | `create_order_from_cart()` |
| 取消订单 | 恢复库存、减少销量 | 是，事务提交后 | `cancel_order()` |
| 支付订单 | 只修改订单状态 | 否 | `pay_order()` |
| Django Admin 商品 | 单个保存、单个删除、批量删除 | 是，事务提交后 | `ProductListCacheInvalidationAdminMixin` |
| Django Admin 分类 | 单个保存、单个删除 | 是，事务提交后 | `CategoryAdmin` 的组合回调 |
| Django Admin 分类 | 批量删除 | 是，事务提交后 | mixin 的默认列表回调 |

创建订单和取消订单会改变 `stock`、`sales_count`，而这两个字段都出现在列表序列化结果中，所以必须让列表缓存失效。支付订单不改变任何商品字段，因此不需要处理商品缓存。

---

## 4. 商品详情缓存

### 4.1 核心常量和缓存内容

```python
PRODUCT_DETAIL_CACHE_KEY = "product:detail:{product_id}"
PRODUCT_DETAIL_CACHE_TTL = 300
```

缓存键示例：

```text
product:detail:42
```

缓存值是 `ProductDetailSerializer` 的 `serializer.data`，主要包含：

- 商品 ID；
- 分类的 ID、名称和 slug；
- 商品名称、slug、描述；
- 价格、库存、销量；
- 上下架状态、图片 URL；
- 创建时间和更新时间。

### 4.2 商品详情缓存什么时候触发

入口位于 `ProductViewSet.retrieve()`：

```python
def retrieve(self, request, *args, **kwargs):
    product_id = kwargs.get(self.lookup_url_kwarg or self.lookup_field)
    if not is_admin_user(request.user):
        cached_data = get_product_detail_cache(product_id)
        if cached_data is not None:
            return api_response(data=cached_data)

    instance = self.get_object()
    serializer = self.get_serializer(instance)
    data = serializer.data

    if (
        not is_admin_user(request.user)
        and instance.status == Product.Status.ACTIVE
    ):
        set_product_detail_cache(instance.id, data)

    return api_response(data=data)
```

触发规则：

1. 请求进入 `GET /api/products/{id}/`。
2. 匿名用户和普通登录用户先读取公共详情缓存。
3. 管理员不读取公共详情缓存，直接查询数据库。
4. 公共请求缓存未命中时，`get_object()` 会基于公共 QuerySet 查询数据库。
5. 公共 QuerySet 只允许已上架商品且分类已启用。
6. 只有非管理员访问已上架商品时才写入公共详情缓存。
7. 管理员即使能看到下架商品或停用分类下的商品，也不会把这些后台数据写入公共缓存。

管理员同时绕过“读”和“写”非常重要。如果管理员读取了停用分类下的商品并把结果放进公共缓存，匿名用户就可能绕过数据库可见性过滤，从缓存中拿到本应返回 404 的商品。

### 4.3 如何读取详情缓存

```python
def get_product_detail_cache(product_id: int):
    try:
        return cache.get(make_product_detail_cache_key(product_id))
    except Exception as exc:
        logger.warning("Failed to read product detail cache: %s", exc)
        return None
```

缓存键由以下函数统一生成：

```python
def make_product_detail_cache_key(product_id: int) -> str:
    return PRODUCT_DETAIL_CACHE_KEY.format(product_id=product_id)
```

缓存命中时直接包装成项目统一响应，不再查询商品表和分类表。

### 4.4 如何创建并存入详情缓存

缓存未命中后：

```python
instance = self.get_object()
serializer = self.get_serializer(instance)
data = serializer.data
```

`get_object()` 负责可见性校验，`ProductDetailSerializer` 负责生成最终缓存数据。然后写入：

```python
def set_product_detail_cache(product_id: int, data) -> None:
    try:
        cache.set(
            make_product_detail_cache_key(product_id),
            data,
            timeout=PRODUCT_DETAIL_CACHE_TTL,
        )
    except Exception as exc:
        logger.warning("Failed to write product detail cache: %s", exc)
```

写入失败只记录 warning，用户仍能收到刚从数据库序列化出的正确响应。

### 4.5 如何删除单个或一批商品详情缓存

```python
def delete_product_detail_cache(product_id: int) -> None:
    try:
        cache.delete(make_product_detail_cache_key(product_id))
    except Exception as exc:
        logger.warning("Failed to delete product detail cache: %s", exc)
```

它会真正删除：

```text
product:detail:{product_id}
```

删除后，该商品下一次公共详情请求会重新查询数据库、重新序列化并写入一个新的 300 秒缓存。

下单、取消订单和 Django Admin 批量删除需要一次清理多个明确的商品 ID，因此使用批量函数：

```python
def delete_product_detail_caches(product_ids) -> None:
    try:
        cache_keys = [
            make_product_detail_cache_key(product_id)
            for product_id in dict.fromkeys(product_ids)
        ]
        if cache_keys:
            cache.delete_many(cache_keys)
    except Exception as exc:
        logger.warning("Failed to delete product detail caches: %s", exc)
```

`dict.fromkeys(product_ids)` 用于按输入顺序去重。函数只构造传入商品 ID 对应的详情键，不扫描 Redis，也不会删除无关商品。

商品列表和一批详情的组合失效函数为：

```python
def invalidate_product_caches(product_ids) -> None:
    delete_product_detail_caches(product_ids)
    invalidate_product_list_cache()
```

组合函数先删除详情键，再切换列表版本。两个底层操作都采用 fail-open，Redis 删除失败时仍会继续尝试切换列表版本，数据库事务不会因此回滚。

### 4.6 如何按分类批量删除详情缓存

分类信息被嵌入商品详情，所以分类更新或停用后需要清理该分类下全部商品：

```python
def delete_category_product_detail_caches(category_id: int) -> None:
    try:
        product_ids = Product.objects.filter(category_id=category_id).values_list(
            "id",
            flat=True,
        )
        cache_keys = [
            make_product_detail_cache_key(product_id) for product_id in product_ids
        ]
        if cache_keys:
            cache.delete_many(cache_keys)
    except Exception as exc:
        logger.warning("Failed to delete category product detail caches: %s", exc)
```

执行过程：

1. 根据 `category_id` 查询该分类下的所有商品 ID。
2. 把每个 ID 转成 `product:detail:{id}`。
3. 使用一次 `cache.delete_many(cache_keys)` 批量删除。
4. 不扫描 Redis，也不会误删其他分类的详情缓存。
5. 分类下没有商品时，不调用 `delete_many()`。

列表和详情的组合失效函数为：

```python
def invalidate_category_caches(category_id: int) -> None:
    delete_category_product_detail_caches(category_id)
    invalidate_product_list_cache()
```

它同时解决两个问题：

- 商品列表中也嵌套了分类名称和 slug，需要让全部列表组合失效。
- 商品详情中嵌套了分类信息，需要精确删除该分类下的详情键。

### 4.7 哪些场景会删除详情缓存

| 业务入口 | 操作 | 删除范围 | 触发时机 |
| --- | --- | --- | --- |
| 管理商品 API | 创建商品 | 新商品的单个详情键 | 事务提交后的组合回调 |
| 管理商品 API | 修改商品 | 该商品的单个详情键 | 事务提交后的组合回调 |
| 管理商品 API | 商品软删除/下架 | 该商品的单个详情键 | 事务提交后的组合回调 |
| 创建订单 | 库存减少、销量增加 | 订单中全部商品的详情键 | 事务提交后一次批量删除 |
| 取消订单 | 库存恢复、销量减少 | 订单中全部商品的详情键 | 事务提交后一次批量删除 |
| 管理分类 API | 创建分类 | 不删除详情 | 新分类还没有依赖它的旧详情数据 |
| 管理分类 API | 修改分类 | 该分类下全部商品详情键 | 事务提交后的组合回调 |
| 管理分类 API | 分类软删除/停用 | 该分类下全部商品详情键 | 事务提交后的组合回调 |
| Django Admin 分类 | 单个保存、单个删除 | 该分类下全部商品详情键 | 事务提交后的组合回调 |
| Django Admin 分类 | 批量删除 | 不批量删详情，只失效列表 | 默认 mixin 回调 |
| Django Admin 商品 | 保存、单个删除 | 该商品的单个详情键 | 事务提交后的组合回调 |
| Django Admin 商品 | 批量删除 | 删除商品对应的全部详情键 | 提交后一次批量删除 |
| 支付订单 | 修改支付状态 | 不删除详情 | 商品数据没有变化 |

### 4.8 为什么写操作统一使用 `transaction.on_commit()`

分类更新代码：

```python
def perform_update(self, serializer):
    category = serializer.save()
    transaction.on_commit(
        partial(invalidate_category_caches, category.id)
    )
```

分类停用代码：

```python
def perform_destroy(self, instance):
    category_id = instance.id
    instance.is_active = False
    instance.save(update_fields=["is_active", "updated_at"])
    transaction.on_commit(
        partial(invalidate_category_caches, category_id)
    )
```

`partial()` 先保存将来调用函数所需的 ID，但不会立即执行缓存失效。`transaction.on_commit()` 只在数据库事务成功提交后运行回调。

这样可以避免以下情况：

1. 商品、分类或库存变化暂时写入数据库。
2. 缓存提前删除或列表提前切换到新版本。
3. 后续异常导致数据库事务回滚。
4. 数据库没有变化，但缓存已经被无意义清理。

更重要的是，详情键在数据库提交后才删除，关闭了“事务提交前删除详情键，并发请求读取旧数据库值并重新写入旧详情”的时间窗。即使缓存操作失败，底层函数也只记录 warning，已经成功提交的数据库业务不会因为 Redis 故障变成接口失败。

---

## 5. 各业务模块中的失效调用链

### 5.1 管理商品 API

```python
def perform_update(self, serializer):
    product = serializer.save()
    transaction.on_commit(
        partial(invalidate_product_caches, (product.id,))
    )
```

商品修改后：

1. 数据库更新先成功提交。
2. 提交回调删除该商品的详情键。
3. 回调递增列表版本，使所有列表参数组合同时失效。
4. 下一次列表和详情请求都从数据库重建缓存。

创建和软删除使用相同思路。软删除会提前保存商品 ID，把状态设置为 `inactive`，提交成功后再删除详情缓存，因此普通用户下一次访问会经过数据库可见性过滤并得到 404。外层事务如果回滚，列表版本和详情缓存都保持不变。

### 5.2 管理分类 API

分类创建在提交后递增列表版本。分类更新和停用在提交后运行一次 `invalidate_category_caches()`，先批量删除该分类下的详情键，再递增列表版本。

分类停用后，如果不删除详情缓存，匿名用户可能继续命中旧的 `product:detail:{id}`，绕过 `category__is_active=True` 的数据库过滤。批量删除正是为了关闭这条旧数据路径。

### 5.3 创建订单

创建订单时，事务内部只修改数据库并收集受影响的商品 ID：

```python
product.stock -= cart_item.quantity
product.sales_count += cart_item.quantity
product.save(update_fields=["stock", "sales_count", "updated_at"])
```

事务末尾只注册一个组合失效回调：

```python
transaction.on_commit(
    partial(invalidate_product_caches, affected_product_ids)
)
```

所以：

- 事务提交前不提前删除详情缓存；
- 订单事务成功提交后，一次批量删除所有受影响商品的详情缓存；
- 商品列表版本只递增一次；
- 即使订单包含多个商品，也不会为每个商品重复递增列表版本。

如果订单事务回滚，提交回调不会执行，详情缓存和列表版本都保持不变。如果事务提交前有并发请求把旧数据库值重新写入详情缓存，提交后的组合回调仍会将旧详情删除。

### 5.4 取消订单

取消订单会恢复库存并减少销量：

```python
product.stock += item.quantity
product.sales_count = max(product.sales_count - item.quantity, 0)
product.save(update_fields=["stock", "sales_count", "updated_at"])
```

取消过程同样收集商品 ID，并在事务提交后调用一次 `invalidate_product_caches()`，批量删除详情并递增一次列表版本。支付订单只修改订单状态，没有修改商品，所以不会触发商品缓存失效。

### 5.5 Django Admin

通用 mixin 提供一个可替换的回调工厂：

```python
class ProductListCacheInvalidationAdminMixin:
    def get_cache_invalidation_callback(self, obj=None):
        return invalidate_product_list_cache

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        transaction.on_commit(self.get_cache_invalidation_callback(obj))
```

默认情况下，mixin 使用列表失效回调；具体 Admin 可以为单对象和批量 QuerySet 提供组合失效回调。

`CategoryAdmin` 对单对象操作覆盖回调：

```python
def get_cache_invalidation_callback(self, obj=None):
    if obj is None:
        return super().get_cache_invalidation_callback(obj)
    return partial(invalidate_category_caches, obj.id)
```

因此分类单个保存或删除只注册一个回调，但这个回调会同时：

1. 批量删除该分类下的商品详情缓存；
2. 递增商品列表缓存版本。

`delete_model()` 会在真正删除对象前创建回调，因为 Django 删除成功后可能清空对象的主键；提前用 `partial()` 捕获 ID，可以保留正确的分类 ID。

分类批量删除时传入的是整个 QuerySet，没有单个 `obj`，所以使用默认的列表失效回调。`Product.category` 使用 `PROTECT`，仍有商品关联的分类不能成功删除；成功硬删除的分类通常没有需要清理的商品详情键。

`ProductAdmin` 对单对象回调绑定一个商品 ID，对批量删除则在执行数据库删除前固化 QuerySet 中的全部商品 ID：

```python
def get_cache_invalidation_callback(self, obj=None):
    if obj is None:
        return super().get_cache_invalidation_callback(obj)
    return partial(invalidate_product_caches, (obj.id,))

def get_queryset_cache_invalidation_callback(self, queryset):
    product_ids = tuple(queryset.values_list("id", flat=True))
    return partial(invalidate_product_caches, product_ids)
```

因此 Django Admin 商品保存、单个删除和批量删除都会在提交后删除对应详情键，并只递增一次列表版本。

---

## 6. 完整请求流程

### 6.1 第一次请求商品列表

```text
GET /api/products/?category=1&ordering=-price&page=2
        ↓
非管理员，启用公共缓存
        ↓
读取 product:list:version
        ↓
规范化 origin 和查询参数，生成 digest
        ↓
读取 product:list:v{version}:{digest}
        ↓ 未命中
查询数据库 → 过滤 → 排序 → 分页 → 序列化
        ↓
规范化 next/previous
        ↓
cache.set(..., timeout=300)
        ↓
返回 HTTP 200
```

### 6.2 相同条件再次请求商品列表

```text
生成同一个缓存键
        ↓
cache.get() 命中
        ↓
直接返回完整分页响应
```

### 6.3 管理员修改商品

```text
PATCH /api/admin/products/{id}/
        ↓
保存商品
        ↓
delete product:detail:{id}
        ↓
INCR product:list:version
        ↓
下一次公共列表、详情请求重新构建缓存
```

### 6.4 管理员修改分类

```text
PATCH /api/admin/categories/{id}/
        ↓
保存分类
        ↓
INCR product:list:version
        ↓
事务成功提交
        ↓
查询该分类下的商品 ID
        ↓
delete_many(product:detail:{product_id}, ...)
        ↓
下一次详情请求得到新的分类名称和 slug
```

### 6.5 分类停用后访问商品详情

```text
停用分类
        ↓
提交后删除该分类下全部详情键
        ↓
匿名用户再次 GET /api/products/{id}/
        ↓
缓存 miss
        ↓
公共 QuerySet 要求 category__is_active=True
        ↓
商品不可见，返回 404
```

---

## 7. Redis 异常时的 fail-open 策略

商品缓存是性能优化，不是业务数据的唯一来源。所有核心读写、版本递增和删除函数都使用 `try/except`：

```python
except Exception as exc:
    logger.warning("...: %s", exc)
```

异常后的行为：

| Redis 操作失败 | 系统行为 |
| --- | --- |
| 读取列表版本失败 | 返回 `None`，本次不生成缓存键 |
| 读取列表缓存失败 | 当作 miss，查询数据库 |
| 写列表缓存失败 | 正常返回数据库响应 |
| 列表版本递增失败 | 数据库写操作仍成功；旧缓存最多保留到 TTL 到期 |
| 读取详情缓存失败 | 当作 miss，查询数据库 |
| 写详情缓存失败 | 正常返回数据库响应 |
| 删除详情缓存失败 | 数据库写操作仍成功；旧详情最多保留到 TTL 到期 |

这叫 fail-open：缓存服务不可用时，接口性能可能下降或在 TTL 内短暂读到旧缓存，但核心数据库业务不会因为缓存故障直接失败。

---

## 8. 当前实现的覆盖边界

以下边界必须明确，避免误以为任何模型变化都会自动清缓存。

### 8.1 没有使用 Django signals

项目没有通过 `post_save`、`post_delete` 全局监听 `Product` 或 `Category`。缓存失效由明确的 API、订单服务和 Django Admin 调用触发。

因此下面的直接 ORM 操作不会自动清缓存：

```python
Product.objects.filter(id=1).update(price=100)
Category.objects.filter(id=1).update(name="New Name")
product.save()
category.save()
```

如果脚本、Django shell、数据修复任务或其他新服务直接修改模型，调用方需要主动调用对应函数：

```python
transaction.on_commit(
    partial(invalidate_product_caches, (product.id,))
)
```

分类发生变化时使用：

```python
invalidate_category_caches(category.id)
```

事务中的商品和分类缓存失效都应注册到 `transaction.on_commit()`。

### 8.2 自定义 Django Admin 动作仍需显式接入

当前 `ProductAdmin` 已覆盖单对象和批量 QuerySet 回调，因此标准保存、单个删除和批量删除都会处理列表与详情缓存。

如果未来增加自定义 Admin action，并且该 action 使用 `QuerySet.update()` 或绕过 `save_model()`、`delete_model()`、`delete_queryset()`，仍需在 action 成功后显式注册 `invalidate_product_caches()` 或 `invalidate_category_caches()`。

### 8.3 分类批量硬删除只处理列表缓存

`CategoryAdmin.delete_queryset()` 使用默认列表回调，不会为每个分类批量构造详情键。由于商品外键采用 `on_delete=models.PROTECT`，有关联商品的分类不能成功硬删除；但如果未来改变外键策略或自定义批量删除逻辑，需要重新评估详情缓存失效。

### 8.4 TTL 是最终兜底，不等于实时一致

缓存删除或版本递增失败后，旧缓存可能继续被读取，最长约为 300 秒。当前系统选择“数据库业务优先、缓存 fail-open”，并没有实现强一致的 Redis 与数据库分布式事务。

---

## 9. 测试覆盖

缓存相关测试主要位于：

- [`apps/products/tests.py`](../apps/products/tests.py)
- [`apps/orders/tests.py`](../apps/orders/tests.py)

主要覆盖内容：

- 查询参数顺序不影响列表缓存键；
- 每个有效筛选、排序、分页参数都会隔离缓存；
- 未知参数和空参数不会制造缓存碎片；
- 版本号和请求来源会改变列表缓存键；
- 列表缓存固定使用 300 秒 TTL；
- 列表缓存命中会复用完整分页响应；
- 管理员绕过公共列表和详情缓存；
- 非法筛选的 400 响应不会写缓存；
- Redis 读写或递增失败时退回数据库；
- 商品管理 API 增、改、软删除会递增列表版本；
- 商品管理 API 外层事务回滚时保留原详情缓存和列表版本；
- 分类管理 API 增、改、停用会递增列表版本；
- 分类更新后，已缓存详情会显示新的分类名称和 slug；
- 分类停用后，旧详情键被删除，匿名请求返回 404；
- 分类详情批量删除只影响目标分类；
- 缓存删除失败不会让分类更新 API 失败；
- 分类事务回滚时不删除详情缓存，也不递增列表版本；
- Django Admin 商品单个保存和批量删除会同时处理列表与详情缓存；
- Django Admin 每次操作只注册一个提交回调；
- 下单和取消订单在提交后批量删除详情，并只递增一次列表版本；
- 订单事务回滚时不递增列表版本；
- 支付订单不会无意义地失效商品列表缓存。

---

## 10. 最终记忆要点

1. 列表缓存键必须包含版本号、请求来源、筛选、排序和分页参数。
2. 列表缓存的“删除”是版本号递增，不是真正删除旧 Redis 键。
3. 旧版本列表键依靠 300 秒 TTL 自动过期。
4. 详情缓存按商品 ID 建键，删除时可以精确到单个商品。
5. 分类信息嵌入商品详情，所以分类修改或停用必须批量删除关联详情键。
6. 管理员不能读取或写入公共商品缓存，否则可能污染公共数据可见性。
7. 修改库存或销量的下单、取消订单也必须处理两套商品缓存。
8. `transaction.on_commit()` 用来避免数据库回滚后提前删除详情或切换列表版本，并关闭提交前旧详情重新写入的时间窗。
9. Redis 异常采用 fail-open，数据库业务优先正常完成。
10. 当前没有 signals，直接 ORM 修改不会自动触发缓存失效。
