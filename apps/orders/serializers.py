import re

from rest_framework import serializers

from apps.orders.models import Order, OrderItem


IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


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
            "expires_at",
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
            "expires_at",
            "paid_at",
            "cancelled_at",
            "updated_at",
        )
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    remark = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context.get("request")
        idempotency_key = (
            request.headers.get("Idempotency-Key", "") if request else ""
        )
        if not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key):
            raise serializers.ValidationError(
                {
                    "Idempotency-Key": (
                        "请求头必填，且只能包含字母、数字、点、下划线、冒号或短横线，"
                        "长度为 1～64 个字符"
                    )
                }
            )
# IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
        attrs["idempotency_key"] = idempotency_key.lower()
        return attrs
