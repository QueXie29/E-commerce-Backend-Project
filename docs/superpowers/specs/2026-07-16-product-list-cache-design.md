# 商品列表缓存设计

## 背景

当前商品模块已经实现商品详情缓存：公开商品详情优先读取缓存，管理员修改商品以及订单改变库存、销量后会清理对应详情缓存。

`apps/products/services.py` 还包含 `make_product_list_cache_key()` 和 `PRODUCT_LIST_KEYS_CACHE_KEY`，但商品列表 View 尚未接入缓存，也没有可靠的批量失效机制。本设计补全公开商品列表缓存，同时保持管理员查询和核心业务不依赖缓存可用性。

## 目标

- 缓存公开 `/api/products/` 的最终分页响应。
- 匿名用户和普通用户共享公开商品列表缓存。
- 管理员访问公开商品接口时绕过缓存。
- `/api/admin/products/` 不使用公开列表缓存。
- 缓存键区分有效筛选、排序、分页参数和请求来源。
- 商品、分类、库存或销量变化后立即切换到新的缓存版本。
- Redis 故障时降级到数据库查询，不让缓存异常中断商品或订单业务。
- 使用项目现有 SQLite 和 `LocMemCache` 测试配置覆盖读写、隔离、失效和降级行为。

## 非目标

- 不缓存管理员商品列表。
- 不使用 Redis 专属的通配符扫描或批量模式删除。
- 不重构现有商品详情缓存。
- 不缓存分类列表。
- 不改变商品筛选、排序、分页或响应格式。
- 不在本次实现中处理分类修改后的商品详情缓存失效问题。

## 方案选择

采用“版本号递增 + 旧缓存等待 TTL 自动过期”。

每个商品列表缓存键带当前全局版本号：

```text
product:list:v{version}:{digest}
```

商品、分类或订单变化时只递增全局版本号。新请求使用新版本缓存键，旧版本缓存立即变为不可达，并在 300 秒 TTL 到期后由缓存后端自动清理。

该方案不需要登记和遍历所有列表缓存键，避免 Django 通用缓存接口下“读取键列表、修改、重新保存”产生的并发覆盖问题；同时兼容生产环境 RedisCache 和测试环境 LocMemCache。

## 缓存服务设计

### 常量

在 `apps/products/services.py` 中定义：

- `PRODUCT_LIST_CACHE_KEY`：`product:list:v{version}:{digest}`。
- `PRODUCT_LIST_CACHE_VERSION_KEY`：`product:list:version`。
- `PRODUCT_LIST_CACHE_TTL`：300 秒。
- `PRODUCT_LIST_CACHE_ALLOWED_PARAMS`：`category`、`keyword`、`min_price`、`max_price`、`ordering`、`page`、`page_size`。

现有未使用的 `PRODUCT_LIST_KEYS_CACHE_KEY` 由版本键替代。

### 参数规范化

缓存键只读取允许的查询参数，忽略 `foo` 等不参与商品查询的参数。参数按照固定名称顺序或排序后的键值对序列化，保证参数顺序不影响缓存键。

空值不写入规范化结果。重复查询参数采用 `QueryDict.get()` 的最终值，与当前 View 读取参数的方式保持一致。

缓存键还包含请求的 scheme 和 host。原因是当前分页响应中的 `next`、`previous` 是绝对 URL；不同请求来源不能复用带有其他域名的分页链接。

规范化数据经过紧凑 JSON 序列化和 MD5 摘要后进入缓存键。MD5 只用于生成短缓存键，不承担安全用途。

### 版本读取

版本键默认值为 `1`，并设置为不过期。读取时：

1. 获取 `product:list:version`。
2. 若不存在，使用原子 `cache.add()` 初始化为 `1`。
3. 再次读取并转换为整数。
4. 任一步骤出现缓存异常时记录 warning，并让本次请求绕过列表缓存。

### 版本递增

`invalidate_product_list_cache()` 执行：

1. 使用 `cache.add()` 保证版本键至少存在且初始为 `1`。
2. 使用 `cache.incr()` 原子递增版本。
3. 缓存异常只记录 warning，不抛给调用方。

多个并发失效操作可能让版本连续递增多次，但不会让旧数据重新可达，正确性优先于版本号连续性。

### 列表缓存读写

服务层增加：

- `make_product_list_cache_key(query_params, origin)`：读取一次当前版本并生成列表缓存键；版本读取失败时返回 `None`。
- `get_product_list_cache(cache_key)`：读取指定缓存键的列表响应；缓存异常返回 `None`。
- `set_product_list_cache(cache_key, data)`：写入指定缓存键的最终响应数据，TTL 为 300 秒；缓存异常只记录日志。
- `invalidate_product_list_cache()`：递增列表缓存版本。

一次列表请求只生成一次缓存键，并复用于缓存读取和数据库查询后的缓存写入。如果查询数据库期间版本被其他写操作递增，该请求仍然只会把结果写回旧版本键，不会把失效前开始查询的结果污染到新版本。

缓存值保存 `Response.data`，而不是 QuerySet、模型对象或 DRF Response 对象。

## 公开商品列表读取流程

只在 `ProductViewSet` 中重写 `list()`，不修改通用的 `ApiReadOnlyViewSetResponseMixin.list()`，避免分类列表和管理员列表被意外缓存。

处理流程：

1. 如果 `is_admin_user(request.user)` 为真，直接调用 `super().list()`，不读取或写入公开列表缓存。
2. 根据当前版本、有效查询参数和请求来源生成缓存键。
3. 缓存命中时使用 DRF `Response` 直接返回缓存的完整响应数据。
4. 缓存未命中或缓存不可用时调用 `super().list()`，保留现有查询、筛选、排序、分页和序列化流程。
5. 仅当响应 HTTP 状态为 `200` 时写入缓存。
6. `ValidationError`、分页错误和其他非 `200` 响应不缓存。

匿名用户和普通用户经过相同的公开可见性过滤，可以共享缓存。管理员看到的数据范围不同，因此必须绕过公开缓存。

## 缓存失效调用点

### 商品管理

`AdminProductViewSet` 在以下数据库操作成功后调用 `invalidate_product_list_cache()`：

- `perform_create()`：保存商品并清理详情缓存之后。
- `perform_update()`：保存商品并清理详情缓存之后。
- `perform_destroy()`：将状态改为 `inactive` 并清理详情缓存之后。

无论变更字段是否影响当前查询，统一失效全部公开列表缓存，以保持规则简单和可靠。

### 分类管理

`AdminCategoryViewSet` 增加或扩展以下钩子：

- `perform_create()`：保存分类后失效列表缓存。
- `perform_update()`：保存分类后失效列表缓存。
- `perform_destroy()`：将 `is_active` 改为 `False` 后失效列表缓存。

分类名称、slug 会出现在商品列表的嵌套分类数据中，分类启用状态还决定普通用户能否看到商品，因此三类操作都要失效列表缓存。

### 订单创建与取消

创建订单会减少库存并增加销量，取消订单会恢复库存并减少销量。这些字段出现在商品列表中，销量还支持排序。

订单服务位于 `transaction.atomic()` 中。每次成功的订单创建或取消只注册一次：

```python
transaction.on_commit(invalidate_product_list_cache)
```

回调放在所有商品与订单写入完成之后、事务退出之前。这样可以保证：

- 事务提交后才切换缓存版本。
- 事务回滚时不切换版本。
- 一张包含多个商品的订单只递增一次版本。
- 不会在事务尚未提交时让其他请求用新版本缓存旧数据库数据。

支付订单不改变商品库存或销量，不失效商品列表缓存。

## 异常与一致性策略

- 缓存读取失败：记录 warning，查询数据库并正常返回。
- 缓存写入失败：记录 warning，本次数据库结果仍正常返回。
- 版本递增失败：记录 warning，商品、分类或订单写入不回滚；旧列表缓存最多继续存在 300 秒。
- 旧版本缓存不会立即释放 Redis 空间，但 TTL 将其生命周期限制在 300 秒内。
- 只有数据库是事实来源，缓存是可降级的性能优化。

## 测试设计

### 缓存键单元测试

- 参数顺序不同但含义相同，缓存键相同。
- `category`、`keyword`、`min_price`、`max_price`、`ordering`、`page`、`page_size` 任一有效值不同，缓存键不同。
- 无效参数不影响缓存键。
- 空参数不制造无意义的独立缓存键。
- 版本号变化后，相同请求得到不同缓存键。
- scheme 或 host 不同时缓存键不同。

### 公开列表缓存测试

- 首次请求将完整分页响应写入缓存。
- 第二次相同请求命中缓存；直接绕过业务失效钩子修改数据库后，仍返回第一次缓存数据，以证明命中。
- 不同筛选、排序和分页参数不交叉污染。
- 缓存命中和未命中的响应结构一致。
- 匿名用户与普通用户共享公开缓存。
- 管理员访问公开商品接口时绕过缓存并能看到其完整数据范围。
- 管理员商品列表不使用公开缓存。
- 非 `200` 响应不写入缓存。
- 模拟缓存 get/set 异常后，接口仍从数据库返回 HTTP 200。

### 商品与分类失效测试

- 管理员新增、修改、下架商品后版本变化，并且后续公开列表返回新数据。
- 管理员新增、修改、停用分类后版本变化；停用分类后，其商品不再出现在公开列表。

### 订单失效测试

- 创建订单提交后版本只递增一次。
- 取消订单提交后版本只递增一次。
- 事务失败或回滚时版本不变。
- 支付订单不改变版本。

Django `TestCase` 外层事务会推迟 `on_commit()` 回调，测试使用 `captureOnCommitCallbacks(execute=True)` 执行并断言回调；如现有测试结构不适合，则对相关用例使用 `TransactionTestCase`。

### 验证命令

实现后依次运行：

```text
python manage.py test apps.products
python manage.py test apps.orders
python manage.py check
python manage.py test
```

## 完成标准

- 公开商品列表相同请求可以命中缓存。
- 有效筛选、排序、分页和请求来源之间缓存隔离正确。
- 管理员公开查询和管理员管理列表不使用公开缓存。
- 商品、分类、订单变化后，新请求不会读取旧版本列表缓存。
- 订单事务回滚不切换版本，事务成功只切换一次。
- 缓存不可用时商品和订单业务继续工作。
- 新增测试通过，完整测试套件通过。
