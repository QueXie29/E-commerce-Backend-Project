from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.products.models import Category, Product
from apps.products.services import make_product_detail_cache_key


User = get_user_model()


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
