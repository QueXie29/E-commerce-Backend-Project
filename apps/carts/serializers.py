from rest_framework import serializers

from apps.carts.models import CartItem
from apps.common.exceptions import BusinessException
from apps.products.models import Product


class CartProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock", "status", "image_url")
        read_only_fields = fields


class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "quantity",
            "selected",
            "subtotal",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_subtotal(self, obj):
        return f"{obj.subtotal:.2f}"


class AddCartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)
 
    def validate(self, attrs):
        try:
            product = Product.objects.select_related("category").get(id=attrs["product_id"])
        except Product.DoesNotExist as exc:
            raise serializers.ValidationError({"product_id": "商品不存在"}) from exc

        if product.status != Product.Status.ACTIVE or not product.category.is_active:
            raise BusinessException("商品已下架", code=40002)

        if product.stock < attrs["quantity"]:
            raise BusinessException("商品库存不足", code=40001)

        attrs["product"] = product
        return attrs


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, required=False)
    selected = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("请至少提交一个可修改字段")

        cart_item = self.context["cart_item"]
        quantity = attrs.get("quantity")

        if cart_item.product.status != Product.Status.ACTIVE or not cart_item.product.category.is_active:
            raise BusinessException("商品已下架", code=40002)

        if quantity is not None and quantity > cart_item.product.stock:
            raise BusinessException("商品库存不足", code=40001)

        return attrs
