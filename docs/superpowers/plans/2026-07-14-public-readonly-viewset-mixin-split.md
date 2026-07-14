# Public Read-Only ViewSet Mixin Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove accidental write actions from the public category and product ViewSets so unsupported POST requests return HTTP 405 while management endpoints preserve their existing permission and CRUD behavior.

**Architecture:** Split the current response Mixin into a read-only base containing `list()` and `retrieve()`, plus a model ViewSet response Mixin containing `create()`, `update()`, and `destroy()`. Public `ReadOnlyModelViewSet` classes use only the read-only Mixin; management `ModelViewSet` classes use the full Mixin.

**Tech Stack:** Python 3, Django, Django REST Framework, `APITestCase`, SQLite test database, PowerShell.

## Global Constraints

- Public `/api/categories/` and `/api/products/` routes remain read-only.
- Unsupported public POST requests return HTTP 405 and do not write to the database.
- Management routes and their URLs remain unchanged.
- A normal user calling a management create endpoint receives HTTP 403 with business code `40300` before creation.
- Do not modify models, serializers, migrations, or the global exception response structure.

---

### Task 1: Add regression coverage for public and management category/product POST behavior

**Files:**
- Modify: `apps/products/tests.py`

**Interfaces:**
- Consumes: Django URL names `category-list`, `product-list`, `admin-category-list`, and existing `ProductApiTests` fixtures.
- Produces: Four regression tests that define the expected HTTP status, business code, and database side effects.

- [ ] **Step 1: Add tests for public POST rejection and management category permissions**

Append these methods to `ProductApiTests`:

```python
    def test_public_category_route_rejects_post_without_creating_category(self):
        payload = {
            "name": "Forbidden Public Category",
            "slug": "forbidden-public-category",
            "is_active": True,
        }
        category_count = Category.objects.count()
        self.client.force_authenticate(self.user)
        self.client.raise_request_exception = False

        response = self.client.post(reverse("category-list"), payload, format="json")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Category.objects.count(), category_count)
        self.assertFalse(Category.objects.filter(slug=payload["slug"]).exists())

    def test_public_product_route_rejects_post_without_creating_product(self):
        payload = {
            "category": self.category.id,
            "name": "Forbidden Public Product",
            "slug": "forbidden-public-product",
            "description": "Public routes are read-only",
            "price": "100.00",
            "stock": 1,
            "status": Product.Status.ACTIVE,
            "image_url": "",
        }
        product_count = Product.objects.count()
        self.client.force_authenticate(self.user)
        self.client.raise_request_exception = False

        response = self.client.post(reverse("product-list"), payload, format="json")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Product.objects.count(), product_count)
        self.assertFalse(Product.objects.filter(slug=payload["slug"]).exists())

    def test_normal_user_cannot_create_category_through_admin_route(self):
        payload = {
            "name": "Admin Only Category",
            "slug": "admin-only-category",
            "is_active": True,
        }
        category_count = Category.objects.count()
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("admin-category-list"), payload, format="json"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], 40300)
        self.assertEqual(Category.objects.count(), category_count)
        self.assertFalse(Category.objects.filter(slug=payload["slug"]).exists())

    def test_admin_can_create_category_through_admin_route(self):
        payload = {
            "name": "Admin Created Category",
            "slug": "admin-created-category",
            "is_active": True,
        }
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse("admin-category-list"), payload, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["code"], 0)
        self.assertTrue(Category.objects.filter(slug=payload["slug"]).exists())
```

- [ ] **Step 2: Run the public-route regression tests and verify RED**

Run:

```powershell
python manage.py test `
  apps.products.tests.ProductApiTests.test_public_category_route_rejects_post_without_creating_category `
  apps.products.tests.ProductApiTests.test_public_product_route_rejects_post_without_creating_product `
  -v 2
```

Expected: both tests fail because each response has HTTP 500 instead of HTTP 405. The failures must originate from the missing `perform_create()` methods, not from test setup or database errors.

- [ ] **Step 3: Run the management-route regression tests and establish the preserved baseline**

Run:

```powershell
python manage.py test `
  apps.products.tests.ProductApiTests.test_normal_user_cannot_create_category_through_admin_route `
  apps.products.tests.ProductApiTests.test_admin_can_create_category_through_admin_route `
  -v 2
```

Expected: both tests pass. This establishes that the fix must preserve HTTP 403/`40300` for normal users and HTTP 201 for administrators.

---

### Task 2: Split the read-only and writable response Mixins

**Files:**
- Modify: `apps/products/views.py:24-74`
- Modify: `apps/products/views.py:157-179`
- Test: `apps/products/tests.py`

**Interfaces:**
- Consumes: `viewsets.ReadOnlyModelViewSet`, `viewsets.ModelViewSet`, and their standard `perform_*` hooks.
- Produces: `ApiReadOnlyViewSetResponseMixin` for public ViewSets and `ApiModelViewSetResponseMixin` for management ViewSets.

- [ ] **Step 1: Split the response Mixin by read and write responsibility**

Replace `ApiViewSetResponseMixin` with these two classes, leaving each existing method body unchanged:

```python
class ApiReadOnlyViewSetResponseMixin:
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(data=serializer.data)


class ApiModelViewSetResponseMixin(ApiReadOnlyViewSetResponseMixin):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return api_response(data=serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return api_response(data=serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return api_response(data=None)
```

- [ ] **Step 2: Assign the read-only Mixin to public ViewSets**

Update the public class declarations:

```python
class CategoryViewSet(ApiReadOnlyViewSetResponseMixin, viewsets.ReadOnlyModelViewSet):
```

```python
class ProductViewSet(ApiReadOnlyViewSetResponseMixin, viewsets.ReadOnlyModelViewSet):
```

- [ ] **Step 3: Assign the writable Mixin to management ViewSets**

Update the management class declarations:

```python
class AdminCategoryViewSet(ApiModelViewSetResponseMixin, viewsets.ModelViewSet):
```

```python
class AdminProductViewSet(ApiModelViewSetResponseMixin, viewsets.ModelViewSet):
```

- [ ] **Step 4: Run the product application tests and verify GREEN**

Run:

```powershell
python manage.py test apps.products.tests.ProductApiTests -v 2
```

Expected: all `ProductApiTests` pass, including both public HTTP 405 regressions, the management category permission tests, the existing management product creation test, and the cache test.

- [ ] **Step 5: Verify router action mappings**

Run:

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings'
@'
import django
django.setup()
from django.urls import resolve

expected = {
    "/api/categories/": {"get": "list"},
    "/api/products/": {"get": "list"},
}
for path, actions in expected.items():
    actual = resolve(path).func.actions
    assert actual == actions, (path, actual)
    print(path, actual)

admin_actions = resolve("/api/admin/categories/").func.actions
assert admin_actions["post"] == "create", admin_actions
print("/api/admin/categories/", admin_actions)
'@ | python -
```

Expected: public list routes print only `{'get': 'list'}`; the management category route includes `'post': 'create'`.

---

### Task 3: Run full verification and commit the bug fix

**Files:**
- Modify: `apps/products/views.py`
- Modify: `apps/products/tests.py`

**Interfaces:**
- Consumes: all project tests and Django system checks.
- Produces: a verified regression fix with no unrelated file changes.

- [ ] **Step 1: Run Django system checks**

Run:

```powershell
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 2: Run the complete test suite**

Run:

```powershell
python manage.py test -v 2
```

Expected: the suite exits with code 0 and reports `OK` with no failures or errors.

- [ ] **Step 3: Inspect the final diff**

Run:

```powershell
git diff --check
git status --short
git diff -- apps/products/views.py apps/products/tests.py
```

Expected: no whitespace errors; only `apps/products/views.py` and `apps/products/tests.py` contain uncommitted implementation changes.

- [ ] **Step 4: Commit the verified fix**

Run:

```powershell
git add -- apps/products/views.py apps/products/tests.py
git commit -m "fix: keep public product routes read only"
```

Expected: one commit containing the Mixin split and its regression tests.
