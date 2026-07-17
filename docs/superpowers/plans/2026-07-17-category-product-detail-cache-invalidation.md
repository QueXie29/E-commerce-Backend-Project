# Category Product Detail Cache Invalidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 分类通过现有管理 API 或 Django Admin 修改、停用后，精确删除该分类下商品的详情缓存，并阻止管理员请求污染公共详情缓存。

**Architecture:** `apps/products/services.py` 提供按 `category_id` 查询商品并批量删除 `product:detail:<id>` 的 fail-open 服务；DRF 分类更新与软删除通过 `transaction.on_commit()` 调用它。Django Admin 通过可覆盖的单回调工厂把列表版本递增和分类详情缓存删除组合成一个提交回调，保持现有 exactly-once 约束。

**Tech Stack:** Python 3.11、Django 5.2.15、Django REST Framework 3.17.1、Django Cache API、RedisCache、LocMemCache、MySQL 8.0、SQLite 测试数据库、`TestCase`、`APITestCase`。

## Global Constraints

- 只覆盖 `AdminCategoryViewSet` 和已注册的 Django `CategoryAdmin`；不引入模型信号。
- 使用 `cache.delete_many()`，只删除目标分类下的 `product:detail:<product_id>`。
- 分类创建不需要专门删除详情缓存；分类更新和软删除必须删除。
- 分类详情缓存删除必须通过 `transaction.on_commit()` 在成功提交后发生；回滚时不删除。
- 缓存查询或删除异常只记录 warning，不得破坏分类数据库操作。
- 管理员访问公开详情接口时不得写入公共详情缓存。
- 保持商品列表缓存、商品自身失效、订单库存与销量、统一响应结构和路由不变。
- 不增加依赖，不创建数据库迁移，不使用 Redis 通配符扫描。

## File Map

- Modify: `apps/products/services.py` — 分类关联商品详情键的批量删除，以及列表+详情组合失效函数。
- Modify: `apps/products/views.py` — 分类 API 更新/停用后的提交回调，以及管理员详情请求的缓存写保护。
- Modify: `apps/products/admin.py` — 可覆盖的单回调工厂和 CategoryAdmin 组合失效。
- Modify: `apps/products/tests.py` — 服务、DRF、事务、管理员缓存写入和 Django Admin 回归测试。
- Reference: `docs/superpowers/specs/2026-07-16-category-product-detail-cache-invalidation-design.md`。

---

### Task 1: Add category-scoped detail cache services

**Files:**
- Modify: `apps/products/services.py`
- Modify: `apps/products/tests.py`

**Interfaces:**
- Consumes: `make_product_detail_cache_key(product_id: int) -> str`、`invalidate_product_list_cache()`、Django `Product` ORM 和 `cache.delete_many()`。
- Produces: `delete_category_product_detail_caches(category_id: int) -> None` 和 `invalidate_category_caches(category_id: int) -> None`。

- [ ] **Step 1: Add failing service imports and tests**

In `apps/products/tests.py`, extend the service imports to include:

```python
from apps.products.services import (
    delete_category_product_detail_caches,
    get_product_list_cache,
    get_product_list_cache_version,
    invalidate_category_caches,
    invalidate_product_list_cache,
    make_product_detail_cache_key,
    make_product_list_cache_key,
    set_product_list_cache,
)
```

Insert this database-backed test class before `ProductAdminInvalidationTests`:

```python
class ProductDetailCacheInvalidationServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.target_category = Category.objects.create(
            name="Target Category",
            slug="target-category",
        )
        self.other_category = Category.objects.create(
            name="Other Category",
            slug="other-category",
        )
        self.target_products = [
            Product.objects.create(
                category=self.target_category,
                name="Target Product One",
                slug="target-product-one",
                description="Target one",
                price=Decimal("10.00"),
                stock=1,
            ),
            Product.objects.create(
                category=self.target_category,
                name="Target Product Two",
                slug="target-product-two",
                description="Target two",
                price=Decimal("20.00"),
                stock=2,
            ),
        ]
        self.other_product = Product.objects.create(
            category=self.other_category,
            name="Other Product",
            slug="other-product",
            description="Other",
            price=Decimal("30.00"),
            stock=3,
        )

    def cache_product_detail(self, product):
        cache.set(
            make_product_detail_cache_key(product.id),
            {"id": product.id, "name": product.name},
            timeout=300,
        )

    def test_delete_category_product_detail_caches_only_deletes_target_category(self):
        for product in [*self.target_products, self.other_product]:
            self.cache_product_detail(product)

        delete_category_product_detail_caches(self.target_category.id)

        for product in self.target_products:
            self.assertIsNone(
                cache.get(make_product_detail_cache_key(product.id))
            )
        self.assertIsNotNone(
            cache.get(make_product_detail_cache_key(self.other_product.id))
        )

    def test_delete_category_product_detail_caches_fails_open(self):
        self.cache_product_detail(self.target_products[0])

        with patch(
            "apps.products.services.cache.delete_many",
            side_effect=RuntimeError("cache delete failed"),
        ):
            result = delete_category_product_detail_caches(
                self.target_category.id
            )

        self.assertIsNone(result)

    def test_invalidate_category_caches_combines_list_and_detail_invalidation(self):
        with patch(
            "apps.products.services.invalidate_product_list_cache"
        ) as list_invalidation, patch(
            "apps.products.services.delete_category_product_detail_caches"
        ) as detail_invalidation:
            result = invalidate_category_caches(self.target_category.id)

        self.assertIsNone(result)
        list_invalidation.assert_called_once_with()
        detail_invalidation.assert_called_once_with(self.target_category.id)
```

- [ ] **Step 2: Run the new service tests and confirm RED**

Run:

```powershell
python manage.py test apps.products.tests.ProductDetailCacheInvalidationServiceTests -v 2
```

Expected: exit code non-zero during test import because `delete_category_product_detail_caches` and `invalidate_category_caches` do not exist yet. This proves the tests precede production code.

- [ ] **Step 3: Implement the category-scoped services**

In `apps/products/services.py`, add the model import:

```python
from apps.products.models import Product
```

Append these functions after `delete_product_detail_cache()`:

```python
def delete_category_product_detail_caches(category_id: int) -> None:
    try:
        product_ids = Product.objects.filter(
            category_id=category_id
        ).values_list("id", flat=True)
        cache_keys = [
            make_product_detail_cache_key(product_id)
            for product_id in product_ids
        ]
        if cache_keys:
            cache.delete_many(cache_keys)
    except Exception as exc:
        logger.warning(
            "Failed to delete category product detail caches: %s",
            exc,
        )


def invalidate_category_caches(category_id: int) -> None:
    invalidate_product_list_cache()
    delete_category_product_detail_caches(category_id)
```

- [ ] **Step 4: Run focused and product tests and confirm GREEN**

Run:

```powershell
python manage.py test apps.products.tests.ProductDetailCacheInvalidationServiceTests -v 2
python manage.py test apps.products -v 2
```

Expected: the 3 new service tests pass; the existing product suite also passes. The fail-open test intentionally emits one warning containing `cache delete failed`.

- [ ] **Step 5: Commit Task 1**

```powershell
git add apps/products/services.py apps/products/tests.py
git commit -m "fix: add category detail cache invalidation service"
```

Expected: one commit containing only the new service functions and their tests.

---

### Task 2: Invalidate detail caches from category API writes

**Files:**
- Modify: `apps/products/views.py`
- Modify: `apps/products/tests.py`

**Interfaces:**
- Consumes: Task 1 `delete_category_product_detail_caches(category_id: int) -> None` and Django `transaction.on_commit()`.
- Produces: category API update/soft-delete invalidation after commit, rollback safety, fail-open behavior, and public-only detail cache writes.

- [ ] **Step 1: Add failing DRF regression tests**

In `apps/products/tests.py`, add:

```python
from django.db import transaction
```

Append these methods to `ProductApiTests`:

```python
    def test_category_update_refreshes_cached_product_detail(self):
        detail_url = reverse(
            "product-detail",
            args=[self.active_product.id],
        )
        first_response = self.client.get(detail_url)
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(
            first_response.data["data"]["category"]["name"],
            "Laptop",
        )

        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            update_response = self.client.patch(
                reverse("admin-category-detail", args=[self.category.id]),
                {"name": "Notebook", "slug": "notebook"},
                format="json",
            )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(len(callbacks), 1)

        self.client.force_authenticate(user=None)
        second_response = self.client.get(detail_url)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(
            second_response.data["data"]["category"]["name"],
            "Notebook",
        )
        self.assertEqual(
            second_response.data["data"]["category"]["slug"],
            "notebook",
        )

    def test_category_deactivation_removes_cached_product_detail(self):
        detail_url = reverse(
            "product-detail",
            args=[self.active_product.id],
        )
        first_response = self.client.get(detail_url)
        self.assertEqual(first_response.status_code, 200)
        self.assertIsNotNone(
            cache.get(make_product_detail_cache_key(self.active_product.id))
        )

        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            destroy_response = self.client.delete(
                reverse("admin-category-detail", args=[self.category.id])
            )

        self.assertEqual(destroy_response.status_code, 200)
        self.assertEqual(len(callbacks), 1)

        self.client.force_authenticate(user=None)
        second_response = self.client.get(detail_url)
        self.assertEqual(second_response.status_code, 404)

    def test_category_update_cache_delete_failure_does_not_fail_request(self):
        self.client.get(
            reverse("product-detail", args=[self.active_product.id])
        )
        self.client.force_authenticate(self.admin)

        with patch(
            "apps.products.services.cache.delete_many",
            side_effect=RuntimeError("cache delete failed"),
        ) as cache_delete_many, self.captureOnCommitCallbacks(
            execute=True
        ) as callbacks:
            response = self.client.patch(
                reverse("admin-category-detail", args=[self.category.id]),
                {"name": "Updated Despite Cache Failure"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(callbacks), 1)
        cache_delete_many.assert_called_once()
        self.category.refresh_from_db()
        self.assertEqual(
            self.category.name,
            "Updated Despite Cache Failure",
        )

    def test_category_update_rollback_does_not_delete_detail_cache(self):
        original_name = self.category.name
        self.client.force_authenticate(self.admin)

        with patch(
            "apps.products.views.delete_category_product_detail_caches"
        ) as detail_invalidation:
            try:
                with transaction.atomic():
                    response = self.client.patch(
                        reverse(
                            "admin-category-detail",
                            args=[self.category.id],
                        ),
                        {"name": "Rolled Back Category"},
                        format="json",
                    )
                    self.assertEqual(response.status_code, 200)
                    raise RuntimeError("force rollback")
            except RuntimeError as exc:
                self.assertEqual(str(exc), "force rollback")

        detail_invalidation.assert_not_called()
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, original_name)

    def test_admin_public_detail_does_not_populate_public_cache(self):
        self.category.is_active = False
        self.category.save(update_fields=["is_active", "updated_at"])
        detail_url = reverse(
            "product-detail",
            args=[self.active_product.id],
        )
        detail_cache_key = make_product_detail_cache_key(
            self.active_product.id
        )
        cache.delete(detail_cache_key)

        self.client.force_authenticate(self.admin)
        admin_response = self.client.get(detail_url)

        self.assertEqual(admin_response.status_code, 200)
        self.assertIsNone(cache.get(detail_cache_key))

        self.client.force_authenticate(user=None)
        anonymous_response = self.client.get(detail_url)
        self.assertEqual(anonymous_response.status_code, 404)
```

- [ ] **Step 2: Run the DRF tests and confirm RED**

Run:

```powershell
python manage.py test `
  apps.products.tests.ProductApiTests.test_category_update_refreshes_cached_product_detail `
  apps.products.tests.ProductApiTests.test_category_deactivation_removes_cached_product_detail `
  apps.products.tests.ProductApiTests.test_category_update_cache_delete_failure_does_not_fail_request `
  apps.products.tests.ProductApiTests.test_category_update_rollback_does_not_delete_detail_cache `
  apps.products.tests.ProductApiTests.test_admin_public_detail_does_not_populate_public_cache `
  -v 2
```

Expected: exit code non-zero. Update/deactivation tests capture zero callbacks and retain stale data; the cache-failure test observes no `delete_many()` call; the administrator detail test finds a populated public cache. The rollback test may already pass because it establishes the intended `on_commit()` baseline.

- [ ] **Step 3: Add category commit hooks and public-cache write protection**

In `apps/products/views.py`, add imports:

```python
from functools import partial

from django.db import transaction
```

Extend the service imports:

```python
from apps.products.services import (
    canonicalize_product_list_pagination_links,
    delete_category_product_detail_caches,
    delete_product_detail_cache,
    get_product_detail_cache,
    get_product_list_cache,
    invalidate_product_list_cache,
    make_product_list_cache_key,
    set_product_detail_cache,
    set_product_list_cache,
)
```

Replace the category update and destroy hooks with:

```python
    def perform_update(self, serializer):
        category = serializer.save()
        invalidate_product_list_cache()
        transaction.on_commit(
            partial(
                delete_category_product_detail_caches,
                category.id,
            )
        )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        invalidate_product_list_cache()
        transaction.on_commit(
            partial(
                delete_category_product_detail_caches,
                instance.id,
            )
        )
```

In `ProductViewSet.retrieve()`, replace the cache-write condition with:

```python
        if (
            not is_admin_user(request.user)
            and instance.status == Product.Status.ACTIVE
        ):
            set_product_detail_cache(instance.id, data)
```

Do not change cache reads: administrators continue to bypass public detail cache reads, while anonymous and normal users continue to share public detail cache entries.

- [ ] **Step 4: Run focused, product, and order tests and confirm GREEN**

Run:

```powershell
python manage.py test `
  apps.products.tests.ProductApiTests.test_category_update_refreshes_cached_product_detail `
  apps.products.tests.ProductApiTests.test_category_deactivation_removes_cached_product_detail `
  apps.products.tests.ProductApiTests.test_category_update_cache_delete_failure_does_not_fail_request `
  apps.products.tests.ProductApiTests.test_category_update_rollback_does_not_delete_detail_cache `
  apps.products.tests.ProductApiTests.test_admin_public_detail_does_not_populate_public_cache `
  -v 2
python manage.py test apps.products -v 2
python manage.py test apps.orders -v 2
```

Expected: the 5 focused tests pass, all product tests pass, and all 9 order tests remain green. The cache-failure test intentionally emits one warning.

- [ ] **Step 5: Commit Task 2**

```powershell
git add apps/products/views.py apps/products/tests.py
git commit -m "fix: invalidate details after category api writes"
```

Expected: one commit containing only DRF integration, administrator cache-write protection, and their tests.

---

### Task 3: Preserve one-callback Django Admin invalidation

**Files:**
- Modify: `apps/products/admin.py`
- Modify: `apps/products/tests.py`

**Interfaces:**
- Consumes: Task 1 `invalidate_category_caches(category_id: int) -> None` and existing `invalidate_product_list_cache()`.
- Produces: a customizable `get_cache_invalidation_callback(obj=None)` admin interface; CategoryAdmin returns one combined callback while ProductAdmin retains list-only invalidation.

- [ ] **Step 1: Add the failing CategoryAdmin combination test**

Append this method to `ProductAdminInvalidationTests`:

```python
    def test_category_admin_change_combines_list_and_detail_invalidation(self):
        product = Product.objects.create(
            category=self.base_category,
            name="Cached Admin Product",
            slug="cached-admin-product",
            description="Cached before category admin update",
            price=Decimal("100.00"),
            stock=1,
            status=Product.Status.ACTIVE,
        )
        detail_cache_key = make_product_detail_cache_key(product.id)
        cache.set(
            detail_cache_key,
            {"id": product.id, "name": product.name},
            timeout=300,
        )
        version_before = get_product_list_cache_version()
        model_admin = admin.site._registry[Category]
        self.base_category.name = "Renamed Through Django Admin"

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            model_admin.save_model(
                self.request,
                self.base_category,
                form=None,
                change=True,
            )

        self.assertEqual(len(callbacks), 1)
        self.assertEqual(get_product_list_cache_version(), version_before)
        self.assertIsNotNone(cache.get(detail_cache_key))

        callbacks[0]()

        self.assertEqual(
            get_product_list_cache_version(),
            version_before + 1,
        )
        self.assertIsNone(cache.get(detail_cache_key))
```

- [ ] **Step 2: Run the Django Admin tests and confirm RED**

Run:

```powershell
python manage.py test apps.products.tests.ProductAdminInvalidationTests -v 2
```

Expected: the new test fails because the existing CategoryAdmin callback only increments the list version and leaves `product:detail:<id>` present. The existing save, single-delete and bulk-delete tests remain green.

- [ ] **Step 3: Add a customizable single-callback admin hook**

In `apps/products/admin.py`, add:

```python
from functools import partial
```

Replace the service import with:

```python
from apps.products.services import (
    invalidate_category_caches,
    invalidate_product_list_cache,
)
```

Replace `ProductListCacheInvalidationAdminMixin` with:

```python
class ProductListCacheInvalidationAdminMixin:
    def get_cache_invalidation_callback(self, obj=None):
        return invalidate_product_list_cache

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        transaction.on_commit(
            self.get_cache_invalidation_callback(obj)
        )

    def delete_model(self, request, obj):
        callback = self.get_cache_invalidation_callback(obj)
        super().delete_model(request, obj)
        transaction.on_commit(callback)

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        transaction.on_commit(
            self.get_cache_invalidation_callback()
        )
```

Add this method inside `CategoryAdmin`:

```python
    def get_cache_invalidation_callback(self, obj=None):
        if obj is None:
            return super().get_cache_invalidation_callback(obj)
        return partial(invalidate_category_caches, obj.id)
```

Why `delete_model()` creates the callback before `super().delete_model()`: Django clears the object's primary key after successful hard delete. Capturing the callback first preserves the original category ID, while registration still occurs only after a successful delete.

Why bulk Category deletion uses the default list callback: a category with related products is protected by `on_delete=models.PROTECT`; successfully bulk-deleted categories therefore have no product detail keys to remove.

- [ ] **Step 4: Run Django Admin and product tests and confirm GREEN**

Run:

```powershell
python manage.py test apps.products.tests.ProductAdminInvalidationTests -v 2
python manage.py test apps.products -v 2
```

Expected: all 4 Django Admin tests pass, including exactly one callback per operation; the complete product suite also passes.

- [ ] **Step 5: Commit Task 3**

```powershell
git add apps/products/admin.py apps/products/tests.py
git commit -m "fix: invalidate details after category admin writes"
```

Expected: one commit containing the admin callback extension and its focused regression test.

---

### Task 4: Complete regression verification

**Files:**
- Verify: `apps/products/services.py`
- Verify: `apps/products/views.py`
- Verify: `apps/products/admin.py`
- Verify: `apps/products/tests.py`

**Interfaces:**
- Consumes: all functions and hooks implemented in Tasks 1-3.
- Produces: a clean, fully verified bug fix with no unrelated changes.

- [ ] **Step 1: Run the product suite**

```powershell
python manage.py test apps.products -v 2
```

Expected: exit code 0 and `OK`; service, DRF, transaction, fail-open, public visibility, Django Admin and existing product tests all pass.

- [ ] **Step 2: Run the order suite**

```powershell
python manage.py test apps.orders -v 2
```

Expected: exit code 0 and all 9 order tests pass; inventory and existing product detail invalidation behavior remain unchanged.

- [ ] **Step 3: Run Django system checks**

```powershell
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Run the complete suite**

```powershell
python manage.py test -v 2
```

Expected: exit code 0 and `OK` with no failures or errors. Warning logs are acceptable only from tests that deliberately inject cache backend failures and must be reported.

- [ ] **Step 5: Inspect the final repository state**

```powershell
git diff --check
git status --short
git log -6 --oneline
```

Expected: no whitespace errors, no uncommitted implementation files, and recent history contains the three focused implementation commits after the design and plan commits.
