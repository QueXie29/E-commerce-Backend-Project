from django.conf import settings
from django.db import models

from apps.products.models import Product


class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="cart_items",
        on_delete=models.CASCADE,
        db_index=True,
    )
    product = models.ForeignKey(
        Product,
        related_name="cart_items",
        on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField()
    selected = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="unique_user_product_cart_item",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="cart_item_quantity_gte_1",
            ),
        ]

    '''@property 的作用，是让这个方法像普通属性一样使用：
    cart_item.subtotal
    而不需要写：
    cart_item.subtotal()'''
    @property
    def subtotal(self):
        return self.product.price * self.quantity
    
    def __str__(self) -> str:
        return f"{self.user_id}:{self.product_id} x {self.quantity}"
