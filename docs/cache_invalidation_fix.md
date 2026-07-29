# 商品缓存失效时序修复记录

## 1. 修改背景

商品公共缓存包含两类键：

- 列表缓存：`product:list:v{version}:{digest}`，通过递增 `product:list:version` 切换命名空间。
- 详情缓存：`product:detail:{product_id}`，通过 `delete()` 或 `delete_many()` 精确删除。

修改前存在两个一致性缺口：

1. 下单和取消订单在数据库事务提交前删除详情缓存。并发详情请求可能在事务提交前读到旧数据库值，并把旧库存、旧销量重新写入详情缓存；事务提交后只切换列表版本，重新写入的旧详情可继续存活到 TTL 到期。
2. Django Admin 商品保存、单个删除和批量删除只切换列表版本，没有删除对应详情键。

管理商品和管理分类 API 也存在统一性问题：部分缓存操作立即执行，外层事务回滚时可能产生无意义的详情删除或列表版本递增。

## 2. 修改目标

- 所有商品、分类和库存写入都在数据库事务成功提交后再失效缓存。
- 一个业务事务只注册一个缓存回调。
- 一次处理多个商品时批量删除明确的详情键，不扫描 Redis。
- 详情删除失败和列表版本递增失败继续采用 fail-open，不反向破坏已经提交的数据库业务。
- 支付订单不修改商品数据，继续不触发商品缓存失效。

## 3. 核心设计

在 `apps/products/services.py` 中增加：

```python
delete_product_detail_caches(product_ids)
invalidate_product_caches(product_ids)
```

`invalidate_product_caches()` 的执行顺序：

```text
删除 product:detail:{id}
        ↓
递增 product:list:version
```

调用方在事务中提前固化商品 ID：

```python
affected_product_ids = tuple(sorted(set(product_ids)))

transaction.on_commit(
    partial(invalidate_product_caches, affected_product_ids)
)
```

数据库回滚时，Django 会丢弃对应的 `on_commit()` 回调，因此缓存保持原状。

## 4. 修改文件

### `apps/products/services.py`

- 新增批量详情删除函数。
- 新增商品列表与详情组合失效函数。
- 分类组合失效调整为先删除详情，再切换列表版本。

### `apps/orders/services.py`

- 下单不再在商品循环内删除详情缓存。
- 取消订单不再在商品循环内删除详情缓存。
- 下单和取消分别收集受影响商品 ID。
- 每个订单事务提交后只执行一次组合失效回调。

### `apps/products/views.py`

- 管理商品创建、更新和软删除统一使用提交后组合失效。
- 管理分类创建在提交后切换列表版本。
- 管理分类更新和停用在提交后运行分类组合失效。
- 外层事务回滚时不再提前清缓存或递增列表版本。

### `apps/products/admin.py`

- `ProductAdmin` 单对象保存和删除绑定单个商品 ID。
- 批量删除在真正删除数据库记录前固化全部商品 ID。
- 提交后批量删除详情键，并只切换一次列表版本。
- 通用 mixin 增加 QuerySet 回调工厂，避免 ProductAdmin 批量删除重复注册回调。

### `apps/orders/tests.py`

- 验证下单、取消在提交前保留原详情缓存。
- 验证唯一提交回调执行后批量删除详情并只切换一次列表版本。

### `apps/products/tests.py`

- 验证 Django Admin 商品保存和批量删除同时处理列表、详情缓存。
- 验证管理商品 API 外层事务回滚时缓存保持不变。
- 验证管理分类 API 外层事务回滚时详情缓存和列表版本均保持不变。
- 调整旧测试，使提交回调在断言前显式执行。

## 5. 修改后的业务流程

### 下单或取消

```text
开启数据库事务
    ↓
锁定商品并修改库存、销量
    ↓
保存订单业务数据
    ↓
注册一个 on_commit 回调
    ↓
数据库提交成功
    ↓
批量删除受影响商品详情键
    ↓
递增一次列表缓存版本
```

### 商品或分类写入回滚

```text
开启外层事务
    ↓
保存商品或分类
    ↓
注册 on_commit 回调
    ↓
后续异常，数据库回滚
    ↓
回调不执行
    ↓
详情缓存和列表版本保持不变
```

## 6. 保留边界

- 缓存失效仍是最终一致性方案，不是数据库与 Redis 的强一致分布式事务。
- Redis 操作失败时，旧缓存最多可能保留到 300 秒 TTL 到期。
- 项目没有使用 Product/Category 模型 signals；脚本、Django shell、`QuerySet.update()` 和绕过标准 Admin 方法的自定义 action 必须显式注册缓存失效。
- 列表失效不会立即删除旧版本 Redis 键，旧键依靠 300 秒 TTL 自动过期。
- 自动化测试使用 SQLite 和 LocMemCache，验证的是业务调用链和提交时序，不等同于真实 Redis 并发压测。

## 7. 验证命令

```powershell
python manage.py test apps.products.tests apps.orders.tests -v 2
python manage.py test -v 2
python manage.py check
```

最终验证结果：

- 商品与订单针对性测试：52 项全部通过。
- 项目完整测试：58 项全部通过。
- Django system check：0 个问题。
- `git diff --check`：通过，仅出现 Windows 工作区的 LF/CRLF 转换提示。
