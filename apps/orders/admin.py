from django.contrib import admin

from apps.orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product",
        "product_name",
        "product_price",
        "quantity",
        "subtotal",
        "created_at",
    )
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order_no",
        "user",
        "total_amount",
        "status",
        "created_at",
        "paid_at",
        "cancelled_at",
    )
    list_filter = ("status",)
    search_fields = ("order_no", "user__username")
    readonly_fields = ("order_no", "total_amount", "created_at", "updated_at")
    inlines = (OrderItemInline,)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "product",
        "product_name",
        "product_price",
        "quantity",
        "subtotal",
    )
    search_fields = ("order__order_no", "product_name")
