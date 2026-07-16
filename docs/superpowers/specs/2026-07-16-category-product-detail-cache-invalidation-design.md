# 分类变更后的商品详情缓存失效设计

## 背景

商品详情接口使用 `product:detail:{product_id}` 缓存最终序列化结果，TTL 为 300 秒。详情结果通过 `ProductDetailSerializer` 嵌入分类的 `id`、`name` 和 `slug`。

当前商品新增、修改、停用以及订单库存变化会删除对应商品的详情缓存，但分类修改和停用只会让商品列表缓存失效。结果是：

- 分类名称或 `slug` 修改后，商品详情最长 300 秒仍可能返回旧分类信息。
- 分类停用后，公开商品查询本应被 `category__is_active=True` 排除，但详情接口在调用 `get_object()` 前直接返回缓存，最长 300 秒仍可能返回 HTTP 200。
- 管理员访问公开商品详情时绕过公开可见性过滤；当前代码仍可能把管理员看到的“启用商品 + 停用分类”详情写入公共缓存，随后被匿名用户读取。

运行态回滚复现已经确认：分类数据库名称更新后详情仍返回旧名称，分类停用后缓存详情仍返回 HTTP 200。

## 目标

1. 分类名称、`slug` 或启用状态通过现有分类管理 API 修改后，删除该分类下所有商品的详情缓存。
2. Django Admin 修改分类时执行相同的详情缓存失效。
3. 分类停用后，匿名用户和普通用户不能通过旧缓存继续访问商品详情。
4. 管理员访问公开商品详情时不得写入公共详情缓存。
5. 缓存删除失败只记录 warning，不得回滚或破坏已经成功的分类数据库操作。
6. 保持现有商品列表缓存、商品自身详情缓存失效、订单库存逻辑和响应结构不变。

## 范围

本次只覆盖项目现有的两类分类管理入口：

- DRF `AdminCategoryViewSet`。
- Django `CategoryAdmin`。

直接在脚本、Django shell 或未接入服务函数的后台任务中调用 `Category.save()` 不在本次保证范围内。本次不引入模型信号。

## 方案选择

采用“按分类批量删除相关商品详情键”的方案：

1. 根据 `category_id` 查询该分类下的商品 ID。
2. 生成 `product:detail:{product_id}` 键列表。
3. 使用 `cache.delete_many()` 一次删除。

未采用以下方案：

- 全局详情缓存版本号：分类修改会让所有分类的商品详情失效，影响范围过大。
- 缓存命中后查询数据库验证分类状态：每次详情命中仍产生数据库查询，削弱缓存价值。
- Category 模型信号：超出已批准的两个管理入口范围，并增加隐藏副作用。

## 代码设计

### `apps/products/services.py`

新增：

```python
def delete_category_product_detail_caches(category_id: int) -> None:
    ...
```

职责：

- 查询 `Product.objects.filter(category_id=category_id)` 的商品 ID。
- 复用 `make_product_detail_cache_key()` 生成缓存键。
- 缓存键非空时调用 `cache.delete_many(cache_keys)`。
- 数据查询或缓存删除出现异常时记录 warning 并返回 `None`，不向调用方抛出。

同时提供一个供 Django Admin 使用的组合失效函数：

```python
def invalidate_category_caches(category_id: int) -> None:
    invalidate_product_list_cache()
    delete_category_product_detail_caches(category_id)
```

组合函数保证 CategoryAdmin 仍只注册一个 `on_commit()` 回调，同时完成列表版本递增和详情缓存删除。

### `apps/products/views.py`

`AdminCategoryViewSet.perform_create()`：

- 保持现有列表缓存失效。
- 不删除详情缓存，因为新分类尚无关联商品。

`AdminCategoryViewSet.perform_update()`：

- 保存分类并保留现有列表缓存失效。
- 使用 `transaction.on_commit()` 注册 `delete_category_product_detail_caches(category.id)`。

`AdminCategoryViewSet.perform_destroy()`：

- 保持当前软删除：将 `is_active` 设为 `False`。
- 保留现有列表缓存失效。
- 使用 `transaction.on_commit()` 注册该分类下商品详情缓存删除。

在项目当前未启用 `ATOMIC_REQUESTS` 的配置下，`on_commit()` 会在保存成功后立即执行；如果调用方处于事务中，则等待事务真正提交。事务回滚时不删除缓存。

`ProductViewSet.retrieve()`：

- 普通用户和匿名用户仍可读取、写入公共详情缓存。
- 管理员继续绕过公共缓存读取。
- 只有非管理员请求能够写入公共详情缓存，避免管理员把停用分类下的商品写入公共缓存。

### `apps/products/admin.py`

现有 `ProductListCacheInvalidationAdminMixin` 增加一个可覆盖的回调工厂方法，默认仍返回 `invalidate_product_list_cache`。

保存和单条删除完成后，Mixin 将对象传给该方法并注册返回的一个回调；批量删除继续注册一个列表缓存失效回调。

`CategoryAdmin` 覆盖回调工厂：当存在分类对象时，返回绑定 `category_id` 的 `invalidate_category_caches()` 回调。这样：

- 每次 CategoryAdmin 操作仍只有一个 `on_commit()` 回调。
- 分类保存成功后同时失效列表和相关详情缓存。
- 分类创建时详情删除查询为空，不影响正确性。
- 有关联商品的分类受 `on_delete=models.PROTECT` 保护，不能在 Django Admin 中硬删除；空分类删除没有详情键需要删除。

`ProductAdmin` 保持现有行为不变。

## 数据流

### 分类修改

```text
管理员修改分类
  -> 分类保存成功
  -> 列表缓存版本递增
  -> 事务提交后查询该分类的商品 ID
  -> delete_many(product:detail:<id> ...)
  -> 下一次详情请求重新查询数据库并写入新缓存
```

### 分类停用

```text
公开详情已有缓存
  -> 管理员停用分类
  -> 事务提交后删除该分类下的详情缓存
  -> 匿名用户再次请求详情
  -> 缓存未命中
  -> get_object() 应用 category__is_active=True
  -> 返回 404
```

## 错误处理

- `cache.delete_many()` 异常：记录 warning，分类数据库修改保持成功。
- 查询关联商品 ID 异常：记录 warning，不让已提交的分类操作失败。
- 没有关联商品：不调用 `delete_many()`，正常返回。
- 列表缓存失效继续使用现有 fail-open 行为。
- 不删除其他分类下商品的详情缓存。

## 测试设计

严格按 TDD 执行，先增加测试并确认当前代码失败，再实现生产代码。

### 服务层测试

1. 给同一分类创建多个商品并预置详情缓存，调用分类详情失效函数后，这些键全部删除。
2. 另一个分类的商品详情缓存保持存在。
3. `cache.delete_many()` 抛出异常时函数返回 `None`，不向外抛出。

### DRF API 测试

1. 先请求商品详情建立缓存，再通过管理 API 修改分类名称和 `slug`；下一次详情返回新分类信息。
2. 先请求商品详情建立缓存，再通过管理 API停用分类；下一次匿名请求返回 404。
3. 修改一个分类时，另一个分类下商品的详情缓存不受影响。
4. 在分类更新事务回滚场景中，`on_commit()` 回调不执行，避免无意义失效。
5. 模拟缓存批量删除失败，分类更新请求仍然成功。
6. 管理员通过公开详情接口查看停用分类下的启用商品后，不产生公共详情缓存；匿名请求仍返回 404。

### Django Admin 测试

1. 修改已有分类时仍只注册一个 `on_commit()` 回调。
2. 执行该回调后，商品列表版本只递增一次，并删除该分类下商品的详情缓存。
3. `ProductAdmin` 现有保存、单删、批删 exactly-once 测试继续通过。

### 回归验证

```powershell
python manage.py test apps.products -v 2
python manage.py test apps.orders -v 2
python manage.py check
python manage.py test -v 2
git diff --check
```

## 文件范围

计划修改：

- `apps/products/services.py`
- `apps/products/views.py`
- `apps/products/admin.py`
- `apps/products/tests.py`

新增设计和实施计划文档不计入生产代码范围。

不修改：

- 数据库模型和迁移。
- 第三方依赖。
- 商品列表缓存键和版本策略。
- 订单服务、购物车、认证和路由。

## 验收标准

- 分类改名后详情立即返回新分类信息。
- 分类停用后已缓存的公开详情返回 404，而不是旧的 200。
- 管理员不会向公共详情缓存写入停用分类下的商品。
- 只删除受影响分类下的商品详情缓存。
- 分类 API 和 Django Admin 都被覆盖。
- 缓存删除失败不破坏分类数据库操作。
- 新测试先红后绿，商品、订单和完整测试套件全部通过。
