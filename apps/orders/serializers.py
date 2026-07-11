from rest_framework import serializers

from apps.orders.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_id",
            "product_name",
            "product_price",
            "quantity",
            "subtotal",
            "created_at",
        )
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            "id",
            "order_no",
            "total_amount",
            "status",
            "remark",
            "created_at",
            "paid_at",
            "cancelled_at",
        )
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "order_no",
            "user_id",
            "total_amount",
            "status",
            "remark",
            "items",
            "created_at",
            "paid_at",
            "cancelled_at",
            "updated_at",
        )
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    remark = serializers.CharField(max_length=255, required=False, allow_blank=True)
