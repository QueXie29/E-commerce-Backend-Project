from django.conf import settings
from django.db import models

from apps.products.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待支付"
        PAID = "paid", "已支付"
        CANCELLED = "cancelled", "已取消"

    order_no = models.CharField(max_length=40, unique=True)
    idempotency_key = models.CharField(max_length=64, null=True, blank=True)
    request_hash = models.CharField(max_length=64, null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="orders",
        on_delete=models.CASCADE,
        db_index=True,
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    remark = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user"], name="idx_order_user"),
            models.Index(fields=["status"], name="idx_order_status"),
            models.Index(fields=["created_at"], name="idx_order_created_at"),
            models.Index(
                fields=["status", "expires_at"],
                name="idx_order_status_expires",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key"],
                name="uq_order_user_idem_key",
            )
        ]

    def __str__(self) -> str:
        return self.order_no


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name="items",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        related_name="order_items",
        on_delete=models.PROTECT,
    )
    product_name = models.CharField(max_length=200)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="order_item_quantity_gte_1",
            )
        ]

    def __str__(self) -> str:
        return f"{self.order_id}:{self.product_name} x {self.quantity}"
