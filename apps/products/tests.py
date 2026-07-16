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


User = get_user_model()


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


class ProductApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="user", password="Test123456")
        self.admin = User.objects.create_user(
            username="admin",
            password="Test123456",
            role="admin",
        )
        self.category = Category.objects.create(name="Laptop", slug="laptop")
        self.active_product = Product.objects.create(
            category=self.category,
            name="MacBook Pro 14",
            slug="macbook-pro-14",
            description="Apple laptop",
            price=Decimal("12999.00"),
            stock=10,
            status=Product.Status.ACTIVE,
        )
        self.inactive_product = Product.objects.create(
            category=self.category,
            name="Old Laptop",
            slug="old-laptop",
            description="Inactive product",
            price=Decimal("3999.00"),
            stock=5,
            status=Product.Status.INACTIVE,
        )

    def test_anonymous_product_list_only_returns_active_products(self):
        response = self.client.get(reverse("product-list"))

        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.data["data"]["results"]]
        self.assertIn("MacBook Pro 14", names)
        self.assertNotIn("Old Laptop", names)

    def test_only_admin_can_create_product(self):
        payload = {
            "category": self.category.id,
            "name": "ThinkPad X1",
            "slug": "thinkpad-x1",
            "description": "Business laptop",
            "price": "8999.00",
            "stock": 8,
            "status": Product.Status.ACTIVE,
            "image_url": "",
        }

        self.client.force_authenticate(self.user)
        user_response = self.client.post(reverse("admin-product-list"), payload, format="json")
        self.assertEqual(user_response.status_code, 403)

        self.client.force_authenticate(self.admin)
        admin_response = self.client.post(reverse("admin-product-list"), payload, format="json")
        self.assertEqual(admin_response.status_code, 201)
        self.assertEqual(admin_response.data["code"], 0)
        self.assertTrue(Product.objects.filter(slug="thinkpad-x1").exists())

    def test_product_detail_uses_cache(self):
        url = reverse("product-detail", args=[self.active_product.id])
        first_response = self.client.get(url)
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_response.data["data"]["name"], "MacBook Pro 14")

        cache_key = make_product_detail_cache_key(self.active_product.id)
        self.assertIsNotNone(cache.get(cache_key))

        Product.objects.filter(id=self.active_product.id).update(name="Changed Name")
        second_response = self.client.get(url)

        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.data["data"]["name"], "MacBook Pro 14")

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
