from rest_framework import serializers

from apps.products.models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")
        read_only_fields = fields


class ProductListSerializer(serializers.ModelSerializer):
    category = ProductCategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "name",
            "slug",
            "price",
            "stock",
            "sales_count",
            "status",
            "image_url",
            "created_at",
        )
        read_only_fields = fields


class ProductDetailSerializer(serializers.ModelSerializer):
    category = ProductCategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "name",
            "slug",
            "description",
            "price",
            "stock",
            "sales_count",
            "status",
            "image_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "name",
            "slug",
            "description",
            "price",
            "stock",
            "status",
            "image_url",
        )
        read_only_fields = ("id",)

    def validate_category(self, value):
        if not value.is_active:
            raise serializers.ValidationError("分类已停用")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("商品价格必须大于 0")
        return value
