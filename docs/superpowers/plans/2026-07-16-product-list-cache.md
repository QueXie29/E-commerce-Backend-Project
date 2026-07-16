# Product List Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为公开商品列表增加按有效筛选、排序和分页参数隔离的版本化缓存，并在商品、分类、订单数据变化后安全失效，同时补齐回归测试。

**Architecture:** `apps/products/services.py` 提供后端无关的版本号、缓存键和列表缓存读写函数；`ProductViewSet.list()` 只为匿名用户和普通用户缓存最终分页响应，管理员始终绕过公开缓存。商品和分类管理操作直接递增版本，订单创建和取消通过 `transaction.on_commit()` 在事务成功后递增一次版本。

**Tech Stack:** Python 3.11、Django 5.2.15、Django REST Framework 3.17.1、RedisCache、LocMemCache、SQLite 测试数据库、`APITestCase`、PowerShell。

## Global Constraints

- 只缓存公开 `/api/products/` 中匿名用户和普通用户看到的列表。
- 管理员访问公开商品接口时绕过缓存，`/api/admin/products/` 永不使用公开列表缓存。
- 缓存 TTL 固定为 300 秒。
- 缓存键只包含 `category`、`keyword`、`min_price`、`max_price`、`ordering`、`page`、`page_size`、scheme 和 host。
- 使用 `product:list:version` 全局版本键；失效时原子递增版本，旧缓存等待 TTL 到期。
- 同一个列表请求只生成一次版本化缓存键，并用该键完成读取和写入，防止并发失效期间把旧结果写入新版本。
- 商品、分类、订单写入不能依赖缓存成功；缓存异常只记录 warning。
- 订单创建和取消只在事务成功提交后递增一次列表版本，回滚不递增。
- 保持现有商品筛选、排序、分页、统一响应结构和详情缓存行为不变。
- 不增加第三方依赖，不创建数据库迁移，不使用 Redis 通配符扫描。

## File Map

- Modify: `apps/products/services.py` — 版本号、有效参数规范化、列表缓存键和缓存读写。
- Modify: `apps/products/views.py` — 公开商品列表读取缓存，以及商品、分类管理操作的缓存失效。
- Modify: `apps/products/tests.py` — 缓存服务、公开列表缓存、管理员绕过和商品/分类失效测试。
- Modify: `apps/orders/services.py` — 订单创建、取消事务提交后的列表缓存失效。
- Modify: `apps/orders/tests.py` — 订单提交、取消、支付、回滚的版本变化测试。

---

### Task 1: Add versioned product-list cache primitives

**Files:**
- Modify: `apps/products/services.py:1-52`
- Modify: `apps/products/tests.py:1-15`

**Interfaces:**
- Consumes: Django `cache.get()`、`cache.add()`、`cache.incr()`、`cache.set()` 和 `QueryDict.get()`。
- Produces: `get_product_list_cache_version()`、`make_product_list_cache_key(query_params, origin)`、`get_product_list_cache(cache_key)`、`set_product_list_cache(cache_key, data)`、`invalidate_product_list_cache()`。

- [ ] **Step 1: Write failing cache-service tests**

Replace the import section at the top of `apps/products/tests.py` with:

```python
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import QueryDict
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.products.models import Category, Product
from apps.products.services import (
    get_product_list_cache,
    get_product_list_cache_version,
    invalidate_product_list_cache,
    make_product_detail_cache_key,
    make_product_list_cache_key,
    set_product_list_cache,
)
```

Insert this test class before `ProductApiTests`:

```python
class ProductListCacheServiceTests(SimpleTestCase):
    origin = "http://testserver"

    def setUp(self):
        cache.clear()

    def test_list_cache_key_is_independent_of_query_parameter_order(self):
        first = QueryDict("category=1&ordering=-price&page=2")
        second = QueryDict("page=2&ordering=-price&category=1")

        self.assertEqual(
            make_product_list_cache_key(first, self.origin),
            make_product_list_cache_key(second, self.origin),
        )

    def test_list_cache_key_changes_for_each_effective_parameter(self):
        base = QueryDict(
            "category=1&keyword=phone&min_price=10&max_price=20"
            "&ordering=price&page=1&page_size=10"
        )
        base_key = make_product_list_cache_key(base, self.origin)
        changed_values = {
            "category": "2",
            "keyword": "camera",
            "min_price": "11",
            "max_price": "21",
            "ordering": "-price",
            "page": "2",
            "page_size": "20",
        }

        for parameter, value in changed_values.items():
            with self.subTest(parameter=parameter):
                changed = base.copy()
                changed[parameter] = value
                self.assertNotEqual(
                    base_key,
                    make_product_list_cache_key(changed, self.origin),
                )

    def test_unknown_and_empty_parameters_do_not_fragment_cache(self):
        baseline = QueryDict("category=1")
        noisy = QueryDict("category=1&foo=ignored&keyword=")

        self.assertEqual(
            make_product_list_cache_key(baseline, self.origin),
            make_product_list_cache_key(noisy, self.origin),
        )

    def test_version_and_origin_change_list_cache_key(self):
        params = QueryDict("category=1&page=1")
        first_version = get_product_list_cache_version()
        first_key = make_product_list_cache_key(params, self.origin)

        new_version = invalidate_product_list_cache()
        second_key = make_product_list_cache_key(params, self.origin)
        other_origin_key = make_product_list_cache_key(
            params,
            "https://shop.example.com",
        )

        self.assertEqual(new_version, first_version + 1)
        self.assertNotEqual(first_key, second_key)
        self.assertNotEqual(second_key, other_origin_key)

    def test_list_cache_helpers_round_trip_payload(self):
        cache_key = make_product_list_cache_key(QueryDict("page=1"), self.origin)
        payload = {
            "code": 0,
            "message": "success",
            "data": {"count": 1, "results": [{"id": 1}]},
        }

        set_product_list_cache(cache_key, payload)

        self.assertEqual(get_product_list_cache(cache_key), payload)

    def test_list_cache_helpers_fail_open(self):
        params = QueryDict("page=1")
        cache_key = make_product_list_cache_key(params, self.origin)

        with patch(
            "apps.products.services.cache.get",
            side_effect=RuntimeError("cache read failed"),
        ):
            self.assertIsNone(get_product_list_cache(cache_key))

        with patch(
            "apps.products.services.cache.set",
            side_effect=RuntimeError("cache write failed"),
        ):
            self.assertIsNone(set_product_list_cache(cache_key, {"code": 0}))

        with patch(
            "apps.products.services.cache.incr",
            side_effect=RuntimeError("cache increment failed"),
        ):
            self.assertIsNone(invalidate_product_list_cache())

        with patch(
            "apps.products.services.cache.get",
            side_effect=RuntimeError("version read failed"),
        ):
            self.assertIsNone(make_product_list_cache_key(params, self.origin))
```

- [ ] **Step 2: Run the service tests and verify RED**

Run:

```powershell
python manage.py test apps.products.tests.ProductListCacheServiceTests -v 2
```

Expected: test discovery fails with an import error because the five list-cache service functions do not exist yet.

- [ ] **Step 3: Implement the cache-service primitives**

Replace `apps/products/services.py` with:

```python
import hashlib
import json
import logging

from django.core.cache import cache


logger = logging.getLogger(__name__)

PRODUCT_DETAIL_CACHE_KEY = "product:detail:{product_id}"
PRODUCT_DETAIL_CACHE_TTL = 300
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


def make_product_detail_cache_key(product_id: int) -> str:
    return PRODUCT_DETAIL_CACHE_KEY.format(product_id=product_id)


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


def normalize_product_list_query_params(query_params):
    normalized = []
    for name in PRODUCT_LIST_CACHE_ALLOWED_PARAMS:
        value = query_params.get(name)
        if value in (None, ""):
            continue
        normalized.append((name, str(value)))
    return normalized


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


def get_product_list_cache(cache_key):
    if cache_key is None:
        return None
    try:
        return cache.get(cache_key)
    except Exception as exc:
        logger.warning("Failed to read product list cache: %s", exc)
        return None


def set_product_list_cache(cache_key, data) -> None:
    if cache_key is None:
        return None
    try:
        cache.set(cache_key, data, timeout=PRODUCT_LIST_CACHE_TTL)
    except Exception as exc:
        logger.warning("Failed to write product list cache: %s", exc)
    return None


def invalidate_product_list_cache():
    try:
        cache.add(PRODUCT_LIST_CACHE_VERSION_KEY, 1, timeout=None)
        return cache.incr(PRODUCT_LIST_CACHE_VERSION_KEY)
    except Exception as exc:
        logger.warning("Failed to invalidate product list cache: %s", exc)
        return None


def get_product_detail_cache(product_id: int):
    try:
        return cache.get(make_product_detail_cache_key(product_id))
    except Exception as exc:
        logger.warning("Failed to read product detail cache: %s", exc)
        return None


def set_product_detail_cache(product_id: int, data) -> None:
    try:
        cache.set(
            make_product_detail_cache_key(product_id),
            data,
            timeout=PRODUCT_DETAIL_CACHE_TTL,
        )
    except Exception as exc:
        logger.warning("Failed to write product detail cache: %s", exc)


def delete_product_detail_cache(product_id: int) -> None:
    try:
        cache.delete(make_product_detail_cache_key(product_id))
    except Exception as exc:
        logger.warning("Failed to delete product detail cache: %s", exc)
```

- [ ] **Step 4: Run the service tests and verify GREEN**

Run:

```powershell
python manage.py test apps.products.tests.ProductListCacheServiceTests -v 2
```

Expected: all six service tests pass. Warning logs from deliberately mocked cache failures are acceptable; no exception escapes the helper functions.

- [ ] **Step 5: Run existing product tests**

Run:

```powershell
python manage.py test apps.products.tests.ProductApiTests -v 2
```

Expected: all existing product API tests pass; detail cache behavior remains unchanged.

- [ ] **Step 6: Commit the service layer**

Run:

```powershell
git add -- apps/products/services.py apps/products/tests.py
git commit -m "feat: add product list cache services"
```

Expected: one commit containing only the cache primitives and their service tests.

---

### Task 2: Cache the public product-list response

**Files:**
- Modify: `apps/products/views.py:4-21`
- Modify: `apps/products/views.py:80-156`
- Modify: `apps/products/tests.py`

**Interfaces:**
- Consumes: Task 1 `make_product_list_cache_key(query_params, origin)`、`get_product_list_cache(cache_key)`、`set_product_list_cache(cache_key, data)`。
- Produces: `ProductViewSet.list()` with public cache lookup/write and administrator bypass.

- [ ] **Step 1: Add failing public-list cache tests**

Append these methods to `ProductApiTests`:

```python
    def test_product_list_uses_cached_paginated_response(self):
        url = reverse("product-list")
        first_response = self.client.get(url)
        self.assertEqual(first_response.status_code, 200)

        Product.objects.filter(id=self.active_product.id).update(
            name="Database Only Name"
        )
        second_response = self.client.get(url)

        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.data, first_response.data)
        names = [item["name"] for item in second_response.data["data"]["results"]]
        self.assertIn("MacBook Pro 14", names)
        self.assertNotIn("Database Only Name", names)

    def test_list_cache_isolated_by_ordering_and_page(self):
        Product.objects.create(
            category=self.category,
            name="Budget Laptop",
            slug="budget-laptop",
            description="Budget",
            price=Decimal("99.00"),
            stock=3,
            status=Product.Status.ACTIVE,
        )
        url = reverse("product-list")

        page_one = self.client.get(
            url,
            {"ordering": "price", "page_size": 1, "page": 1},
        )
        page_two = self.client.get(
            url,
            {"ordering": "price", "page_size": 1, "page": 2},
        )
        descending = self.client.get(
            url,
            {"ordering": "-price", "page_size": 1, "page": 1},
        )

        self.assertEqual(page_one.data["data"]["results"][0]["name"], "Budget Laptop")
        self.assertEqual(page_two.data["data"]["results"][0]["name"], "MacBook Pro 14")
        self.assertEqual(descending.data["data"]["results"][0]["name"], "MacBook Pro 14")

    def test_normal_user_shares_anonymous_public_list_cache(self):
        url = reverse("product-list")
        first_response = self.client.get(url)
        Product.objects.filter(id=self.active_product.id).update(
            name="Database Only Name"
        )

        self.client.force_authenticate(self.user)
        second_response = self.client.get(url)

        self.assertEqual(second_response.data, first_response.data)

    def test_inflight_response_writes_only_to_original_cache_version(self):
        params = QueryDict("")
        origin = "http://testserver"
        original_key = make_product_list_cache_key(params, origin)

        def invalidate_during_read(cache_key):
            self.assertEqual(cache_key, original_key)
            invalidate_product_list_cache()
            return None

        with patch(
            "apps.products.views.get_product_list_cache",
            side_effect=invalidate_during_read,
        ), patch("apps.products.views.set_product_list_cache") as cache_set:
            response = self.client.get(reverse("product-list"))

        self.assertEqual(response.status_code, 200)
        cache_set.assert_called_once()
        self.assertEqual(cache_set.call_args.args[0], original_key)
        self.assertNotEqual(
            original_key,
            make_product_list_cache_key(params, origin),
        )

    def test_admin_bypasses_public_list_cache(self):
        url = reverse("product-list")
        public_response = self.client.get(url)
        public_names = [
            item["name"] for item in public_response.data["data"]["results"]
        ]
        self.assertNotIn("Old Laptop", public_names)

        self.client.force_authenticate(self.admin)
        admin_response = self.client.get(url)
        admin_names = [
            item["name"] for item in admin_response.data["data"]["results"]
        ]

        self.assertIn("Old Laptop", admin_names)

    def test_admin_product_list_does_not_use_public_cache(self):
        self.client.get(reverse("product-list"))
        Product.objects.filter(id=self.active_product.id).update(
            name="Database Only Name"
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("admin-product-list"))
        names = [item["name"] for item in response.data["data"]["results"]]

        self.assertIn("Database Only Name", names)

    def test_invalid_product_filter_response_is_not_cached(self):
        with patch("apps.products.views.set_product_list_cache") as cache_set:
            response = self.client.get(
                reverse("product-list"),
                {"category": "not-an-integer"},
            )

        self.assertEqual(response.status_code, 400)
        cache_set.assert_not_called()

    def test_list_cache_backend_failures_fall_back_to_database(self):
        with patch(
            "apps.products.services.cache.get",
            side_effect=RuntimeError("cache read failed"),
        ):
            read_failure_response = self.client.get(reverse("product-list"))

        cache.clear()
        with patch(
            "apps.products.services.cache.set",
            side_effect=RuntimeError("cache write failed"),
        ):
            write_failure_response = self.client.get(reverse("product-list"))

        self.assertEqual(read_failure_response.status_code, 200)
        self.assertEqual(write_failure_response.status_code, 200)
        self.assertIn(
            "MacBook Pro 14",
            [
                item["name"]
                for item in write_failure_response.data["data"]["results"]
            ],
        )
```

- [ ] **Step 2: Run the new API tests and verify RED**

Run:

```powershell
python manage.py test `
  apps.products.tests.ProductApiTests.test_product_list_uses_cached_paginated_response `
  apps.products.tests.ProductApiTests.test_normal_user_shares_anonymous_public_list_cache `
  apps.products.tests.ProductApiTests.test_invalid_product_filter_response_is_not_cached `
  -v 2
```

Expected: the cache-hit assertions fail because the list still reads the changed database row; the invalid-filter test errors because `apps.products.views.set_product_list_cache` has not been imported yet.

- [ ] **Step 3: Wire cache lookup and write into `ProductViewSet.list()`**

Add the DRF response import:

```python
from rest_framework.response import Response
```

Extend the `apps.products.services` import to:

```python
from apps.products.services import (
    delete_product_detail_cache,
    get_product_detail_cache,
    get_product_list_cache,
    make_product_list_cache_key,
    set_product_detail_cache,
    set_product_list_cache,
)
```

Insert this method at the beginning of `ProductViewSet`, before `get_serializer_class()`:

```python
    def list(self, request, *args, **kwargs):
        if is_admin_user(request.user):
            return super().list(request, *args, **kwargs)

        origin = f"{request.scheme}://{request.get_host()}"
        cache_key = make_product_list_cache_key(request.query_params, origin)
        cached_data = get_product_list_cache(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            set_product_list_cache(cache_key, response.data)
        return response
```

Do not recompute the cache key before `set_product_list_cache()`. Reusing `cache_key` guarantees that a concurrent version increment cannot make an older in-flight query populate the new version.

- [ ] **Step 4: Run the product-list cache tests and verify GREEN**

Run:

```powershell
python manage.py test apps.products.tests.ProductApiTests -v 2
```

Expected: existing product tests and all eight new list-cache tests pass. The invalid category filter remains HTTP 400, administrators see inactive products on the public endpoint, an in-flight response writes only to its original version key, and cache backend exceptions do not become API errors.

- [ ] **Step 5: Commit public list caching**

Run:

```powershell
git add -- apps/products/views.py apps/products/tests.py
git commit -m "feat: cache public product lists"
```

Expected: one commit containing `ProductViewSet.list()` and its API tests.

---

### Task 3: Invalidate lists after product and category management writes

**Files:**
- Modify: `apps/products/views.py:17-21`
- Modify: `apps/products/views.py:70-77`
- Modify: `apps/products/views.py:175-186`
- Modify: `apps/products/tests.py`

**Interfaces:**
- Consumes: Task 1 `invalidate_product_list_cache()` and existing DRF `perform_create()`、`perform_update()`、`perform_destroy()` hooks.
- Produces: exactly one list-version increment after each successful catalog management operation.

- [ ] **Step 1: Add failing product/category invalidation tests**

Append these methods to `ProductApiTests`:

```python
    def test_admin_product_create_update_destroy_increment_list_version(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "category": self.category.id,
            "name": "Cache Managed Product",
            "slug": "cache-managed-product",
            "description": "Cache invalidation",
            "price": "500.00",
            "stock": 4,
            "status": Product.Status.ACTIVE,
            "image_url": "",
        }

        before_create = get_product_list_cache_version()
        create_response = self.client.post(
            reverse("admin-product-list"),
            payload,
            format="json",
        )
        created_id = create_response.data["data"]["id"]
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(get_product_list_cache_version(), before_create + 1)

        before_update = get_product_list_cache_version()
        update_response = self.client.patch(
            reverse("admin-product-detail", args=[created_id]),
            {"price": "600.00"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(get_product_list_cache_version(), before_update + 1)

        before_destroy = get_product_list_cache_version()
        destroy_response = self.client.delete(
            reverse("admin-product-detail", args=[created_id])
        )
        self.assertEqual(destroy_response.status_code, 200)
        self.assertEqual(get_product_list_cache_version(), before_destroy + 1)

    def test_admin_category_create_update_destroy_increment_list_version(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "name": "Cache Category",
            "slug": "cache-category",
            "is_active": True,
        }

        before_create = get_product_list_cache_version()
        create_response = self.client.post(
            reverse("admin-category-list"),
            payload,
            format="json",
        )
        created_id = create_response.data["data"]["id"]
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(get_product_list_cache_version(), before_create + 1)

        before_update = get_product_list_cache_version()
        update_response = self.client.patch(
            reverse("admin-category-detail", args=[created_id]),
            {"name": "Renamed Cache Category"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(get_product_list_cache_version(), before_update + 1)

        before_destroy = get_product_list_cache_version()
        destroy_response = self.client.delete(
            reverse("admin-category-detail", args=[created_id])
        )
        self.assertEqual(destroy_response.status_code, 200)
        self.assertEqual(get_product_list_cache_version(), before_destroy + 1)

    def test_admin_product_update_refreshes_cached_public_list(self):
        first_response = self.client.get(reverse("product-list"))
        self.assertIn(
            "MacBook Pro 14",
            [item["name"] for item in first_response.data["data"]["results"]],
        )

        self.client.force_authenticate(self.admin)
        update_response = self.client.patch(
            reverse("admin-product-detail", args=[self.active_product.id]),
            {"name": "Updated MacBook"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)

        self.client.force_authenticate(user=None)
        second_response = self.client.get(reverse("product-list"))
        names = [item["name"] for item in second_response.data["data"]["results"]]
        self.assertIn("Updated MacBook", names)
        self.assertNotIn("MacBook Pro 14", names)

    def test_category_deactivation_refreshes_cached_public_list(self):
        first_response = self.client.get(reverse("product-list"))
        self.assertIn(
            "MacBook Pro 14",
            [item["name"] for item in first_response.data["data"]["results"]],
        )

        self.client.force_authenticate(self.admin)
        destroy_response = self.client.delete(
            reverse("admin-category-detail", args=[self.category.id])
        )
        self.assertEqual(destroy_response.status_code, 200)

        self.client.force_authenticate(user=None)
        second_response = self.client.get(reverse("product-list"))
        names = [item["name"] for item in second_response.data["data"]["results"]]
        self.assertNotIn("MacBook Pro 14", names)
```

- [ ] **Step 2: Run catalog invalidation tests and verify RED**

Run:

```powershell
python manage.py test `
  apps.products.tests.ProductApiTests.test_admin_product_create_update_destroy_increment_list_version `
  apps.products.tests.ProductApiTests.test_admin_category_create_update_destroy_increment_list_version `
  apps.products.tests.ProductApiTests.test_admin_product_update_refreshes_cached_public_list `
  apps.products.tests.ProductApiTests.test_category_deactivation_refreshes_cached_public_list `
  -v 2
```

Expected: version assertions fail and cached public responses remain stale because catalog hooks do not yet call `invalidate_product_list_cache()`.

- [ ] **Step 3: Add catalog invalidation hooks**

Add `invalidate_product_list_cache` to the services import in `apps/products/views.py`:

```python
from apps.products.services import (
    delete_product_detail_cache,
    get_product_detail_cache,
    get_product_list_cache,
    invalidate_product_list_cache,
    make_product_list_cache_key,
    set_product_detail_cache,
    set_product_list_cache,
)
```

Replace `AdminCategoryViewSet` with:

```python
class AdminCategoryViewSet(ApiModelViewSetResponseMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = (IsAdminRole,)

    def perform_create(self, serializer):
        serializer.save()
        invalidate_product_list_cache()

    def perform_update(self, serializer):
        serializer.save()
        invalidate_product_list_cache()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        invalidate_product_list_cache()
```

Update `AdminProductViewSet` hooks to:

```python
    def perform_create(self, serializer):
        product = serializer.save()
        delete_product_detail_cache(product.id)
        invalidate_product_list_cache()

    def perform_update(self, serializer):
        product = serializer.save()
        delete_product_detail_cache(product.id)
        invalidate_product_list_cache()

    def perform_destroy(self, instance):
        instance.status = Product.Status.INACTIVE
        instance.save(update_fields=["status", "updated_at"])
        delete_product_detail_cache(instance.id)
        invalidate_product_list_cache()
```

- [ ] **Step 4: Run all product tests and verify GREEN**

Run:

```powershell
python manage.py test apps.products -v 2
```

Expected: all cache-service, public-list, catalog invalidation, route permission, serializer and detail-cache tests pass.

- [ ] **Step 5: Commit catalog invalidation**

Run:

```powershell
git add -- apps/products/views.py apps/products/tests.py
git commit -m "feat: invalidate product lists after catalog writes"
```

Expected: one commit containing only product/category invalidation hooks and their tests.

---

### Task 4: Invalidate lists after successful order transactions

**Files:**
- Modify: `apps/orders/services.py:13-16`
- Modify: `apps/orders/services.py:109-114`
- Modify: `apps/orders/services.py:171-175`
- Modify: `apps/orders/tests.py:1-12`
- Modify: `apps/orders/tests.py`

**Interfaces:**
- Consumes: Task 1 `invalidate_product_list_cache()` and Django `transaction.on_commit()`.
- Produces: one version increment after successful order creation, one after successful cancellation, none after payment or rollback.

- [ ] **Step 1: Add failing order transaction tests**

Replace the product-service import section of `apps/orders/tests.py` with:

```python
from apps.products.models import Category, Product
from apps.products.services import get_product_list_cache_version
```

Append these methods to `OrderApiTests`:

```python
    def test_order_creation_invalidates_list_cache_once_after_commit(self):
        second_product = Product.objects.create(
            category=self.category,
            name="Camera Lens",
            slug="camera-lens",
            description="Lens",
            price=Decimal("1000.00"),
            stock=4,
            status=Product.Status.ACTIVE,
        )
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)
        CartItem.objects.create(user=self.user, product=second_product, quantity=1)
        version_before = get_product_list_cache_version()

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client.post(reverse("order-list"), {}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(get_product_list_cache_version(), version_before + 1)

    def test_order_creation_rollback_does_not_invalidate_list_cache(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=6)
        version_before = get_product_list_cache_version()

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client.post(reverse("order-list"), {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(callbacks), 0)
        self.assertEqual(get_product_list_cache_version(), version_before)

    def test_order_cancellation_invalidates_list_cache_once_after_commit(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)
        with self.captureOnCommitCallbacks(execute=True) as create_callbacks:
            create_response = self.client.post(
                reverse("order-list"),
                {},
                format="json",
            )
        order_id = create_response.data["data"]["id"]
        self.assertEqual(len(create_callbacks), 1)
        version_before_cancel = get_product_list_cache_version()

        with self.captureOnCommitCallbacks(execute=True) as cancel_callbacks:
            cancel_response = self.client.post(
                reverse("order-cancel", args=[order_id])
            )

        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(len(cancel_callbacks), 1)
        self.assertEqual(
            get_product_list_cache_version(),
            version_before_cancel + 1,
        )

    def test_order_payment_does_not_invalidate_list_cache(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)
        with self.captureOnCommitCallbacks(execute=True):
            create_response = self.client.post(
                reverse("order-list"),
                {},
                format="json",
            )
        order_id = create_response.data["data"]["id"]
        version_before_payment = get_product_list_cache_version()

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            pay_response = self.client.post(reverse("order-pay", args=[order_id]))

        self.assertEqual(pay_response.status_code, 200)
        self.assertEqual(len(callbacks), 0)
        self.assertEqual(
            get_product_list_cache_version(),
            version_before_payment,
        )
```

- [ ] **Step 2: Run order invalidation tests and verify RED**

Run:

```powershell
python manage.py test `
  apps.orders.tests.OrderApiTests.test_order_creation_invalidates_list_cache_once_after_commit `
  apps.orders.tests.OrderApiTests.test_order_creation_rollback_does_not_invalidate_list_cache `
  apps.orders.tests.OrderApiTests.test_order_cancellation_invalidates_list_cache_once_after_commit `
  apps.orders.tests.OrderApiTests.test_order_payment_does_not_invalidate_list_cache `
  -v 2
```

Expected: successful create/cancel tests fail because no `on_commit()` callback is registered; rollback and payment tests establish the unchanged-version baseline.

- [ ] **Step 3: Register invalidation after successful commits**

Replace the product-service import in `apps/orders/services.py` with:

```python
from apps.products.services import (
    delete_product_detail_cache,
    invalidate_product_list_cache,
)
```

In `create_order_from_cart()`, insert the callback after selected cart items are deleted and before returning the order:

```python
            OrderItem.objects.bulk_create(order_items)
            order.total_amount = total_amount
            order.save(update_fields=["total_amount", "updated_at"])
            CartItem.objects.filter(id__in=[item.id for item in cart_items]).delete()
            transaction.on_commit(invalidate_product_list_cache)

            return get_order_for_response(order.id)
```

In `cancel_order()`, insert the callback after saving the cancelled order and while still inside `transaction.atomic()`:

```python
        order.status = Order.Status.CANCELLED
        order.cancelled_at = timezone.now()
        order.save(update_fields=["status", "cancelled_at", "updated_at"])
        transaction.on_commit(invalidate_product_list_cache)

    return get_order_for_response(order.id)
```

Do not add a callback to `pay_order()` because payment does not change product list fields.

- [ ] **Step 4: Run order tests and verify GREEN**

Run:

```powershell
python manage.py test apps.orders -v 2
```

Expected: all existing order behavior tests and the four new transaction-aware cache tests pass. Successful multi-item creation and cancellation each capture exactly one callback.

- [ ] **Step 5: Commit order invalidation**

Run:

```powershell
git add -- apps/orders/services.py apps/orders/tests.py
git commit -m "feat: invalidate product lists after order commits"
```

Expected: one commit containing only order transaction callbacks and tests.

---

### Task 5: Complete regression verification

**Files:**
- Verify: `apps/products/services.py`
- Verify: `apps/products/views.py`
- Verify: `apps/products/tests.py`
- Verify: `apps/orders/services.py`
- Verify: `apps/orders/tests.py`

**Interfaces:**
- Consumes: all functions and hooks implemented in Tasks 1-4.
- Produces: a clean, fully verified implementation with no unrelated changes.

- [ ] **Step 1: Run product tests**

Run:

```powershell
python manage.py test apps.products -v 2
```

Expected: exit code 0 and `OK`; service, cache-hit, cache isolation, administrator bypass, catalog invalidation and existing route-contract tests all pass.

- [ ] **Step 2: Run order tests**

Run:

```powershell
python manage.py test apps.orders -v 2
```

Expected: exit code 0 and `OK`; successful commits invalidate once, rollback/payment do not invalidate, and existing stock/order-state behavior remains correct.

- [ ] **Step 3: Run Django system checks**

Run:

```powershell
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Run the complete test suite**

Run:

```powershell
python manage.py test -v 2
```

Expected: exit code 0 and `OK` with no failures or errors.

- [ ] **Step 5: Inspect repository state and implementation diff**

Run:

```powershell
git diff --check
git status --short
git log -5 --oneline
```

Expected: no whitespace errors, no uncommitted implementation files, and the recent history contains the four focused implementation commits from Tasks 1-4.
