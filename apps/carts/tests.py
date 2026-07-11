from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.carts.models import CartItem
from apps.products.models import Category, Product


User = get_user_model()


class CartApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="Test123456")
        self.other_user = User.objects.create_user(username="other", password="Test123456")
        self.category = Category.objects.create(name="Phone", slug="phone")
        self.product = Product.objects.create(
            category=self.category,
            name="iPhone",
            slug="iphone",
            description="Phone",
            price=Decimal("6999.00"),
            stock=5,
            status=Product.Status.ACTIVE,
        )
        self.inactive_product = Product.objects.create(
            category=self.category,
            name="Old Phone",
            slug="old-phone",
            description="Inactive",
            price=Decimal("1999.00"),
            stock=5,
            status=Product.Status.INACTIVE,
        )

    def test_add_cart_item_and_increment_existing_item(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("cart-item-create"),
            {"product_id": self.product.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        second_response = self.client.post(
            reverse("cart-item-create"),
            {"product_id": self.product.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(second_response.status_code, 200)

        cart_item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(cart_item.quantity, 4)
        self.assertEqual(CartItem.objects.filter(user=self.user, product=self.product).count(), 1)

    def test_cannot_add_inactive_or_overstock_product(self):
        self.client.force_authenticate(self.user)

        inactive_response = self.client.post(
            reverse("cart-item-create"),
            {"product_id": self.inactive_product.id, "quantity": 1},
            format="json",
        )
        self.assertEqual(inactive_response.status_code, 400)
        self.assertEqual(inactive_response.data["code"], 40002)

        overstock_response = self.client.post(
            reverse("cart-item-create"),
            {"product_id": self.product.id, "quantity": 6},
            format="json",
        )
        self.assertEqual(overstock_response.status_code, 400)
        self.assertEqual(overstock_response.data["code"], 40001)

    def test_user_can_only_update_own_cart_item(self):
        cart_item = CartItem.objects.create(user=self.user, product=self.product, quantity=1)
        self.client.force_authenticate(self.other_user)

        response = self.client.patch(
            reverse("cart-item-detail", args=[cart_item.id]),
            {"quantity": 2},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_clear_cart(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)
        self.client.force_authenticate(self.user)

        response = self.client.delete(reverse("cart-clear"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())
