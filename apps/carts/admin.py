from django.contrib import admin

from apps.carts.models import CartItem


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "quantity", "selected", "created_at")
    list_filter = ("selected",)
    search_fields = ("user__username", "product__name")
