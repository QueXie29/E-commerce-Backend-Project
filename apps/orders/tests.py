from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.carts.models import CartItem
from apps.orders.models import Order
from apps.orders.services import ORDER_CREATE_LOCK_KEY
from apps.products.models import Category, Product


User = get_user_model()


class OrderApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="buyer", password="Test123456")
        self.category = Category.objects.create(name="Camera", slug="camera")
        self.product = Product.objects.create(
            category=self.category,
            name="Sony Camera",
            slug="sony-camera",
            description="Camera",
            price=Decimal("5000.00"),
            stock=5,
            sales_count=0,
            status=Product.Status.ACTIVE,
        )
        self.client.force_authenticate(self.user)

    def test_create_order_from_cart_deducts_stock_and_clears_cart(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)

        response = self.client.post(
            reverse("order-list"),
            {"remark": "请尽快发货"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["code"], 0)
        self.assertEqual(response.data["data"]["total_amount"], "10000.00")

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.product.sales_count, 2)
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

        order = Order.objects.get(user=self.user)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().product_name, "Sony Camera")

    def test_order_create_fails_when_stock_is_insufficient(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=6)

        response = self.client.post(reverse("order-list"), {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], 40001)
        self.assertFalse(Order.objects.exists())

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_order_create_rejects_duplicate_submission_lock(self):
        lock_key = ORDER_CREATE_LOCK_KEY.format(user_id=self.user.id)
        cache.add(lock_key, "locked", timeout=10)
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)

        response = self.client.post(reverse("order-list"), {}, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], 40900)
        self.assertTrue(CartItem.objects.filter(user=self.user).exists())

    def test_pay_order_and_paid_order_cannot_be_cancelled(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)
        create_response = self.client.post(reverse("order-list"), {}, format="json")
        order_id = create_response.data["data"]["id"]

        pay_response = self.client.post(reverse("order-pay", args=[order_id]))
        self.assertEqual(pay_response.status_code, 200)
        self.assertEqual(pay_response.data["data"]["status"], Order.Status.PAID)

        cancel_response = self.client.post(reverse("order-cancel", args=[order_id]))
        self.assertEqual(cancel_response.status_code, 400)
        self.assertEqual(cancel_response.data["code"], 40004)

    def test_cancel_pending_order_restores_stock(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        create_response = self.client.post(reverse("order-list"), {}, format="json")
        order_id = create_response.data["data"]["id"]

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.product.sales_count, 2)

        cancel_response = self.client.post(reverse("order-cancel", args=[order_id]))

        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.data["data"]["status"], Order.Status.CANCELLED)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(self.product.sales_count, 0)
