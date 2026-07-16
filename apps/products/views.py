from decimal import Decimal, InvalidOperation

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.permissions import IsAdminRole, is_admin_user
from apps.common.responses import api_response
from apps.products.models import Category, Product
from apps.products.serializers import (
    CategorySerializer,
    ProductCreateUpdateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)
from apps.products.services import (
    canonicalize_product_list_pagination_links,
    delete_product_detail_cache,
    get_product_detail_cache,
    get_product_list_cache,
    invalidate_product_list_cache,
    make_product_list_cache_key,
    set_product_detail_cache,
    set_product_list_cache,
)


class ApiReadOnlyViewSetResponseMixin:
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(data=serializer.data)


class ApiModelViewSetResponseMixin(ApiReadOnlyViewSetResponseMixin):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return api_response(data=serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return api_response(data=serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return api_response(data=None)


class CategoryViewSet(ApiReadOnlyViewSetResponseMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by("name")


class AdminCategoryViewSet(ApiModelViewSetResponseMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = (IsAdminRole,)

    def perform_create(self, serializer):
        serializer.save()
        invalidate_product_list_cache()

    def perform_update(self, serializer):
        serializer.save()
        invalidate_product_list_cache()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        invalidate_product_list_cache()


class ProductViewSet(ApiReadOnlyViewSetResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)

    def list(self, request, *args, **kwargs):
        if is_admin_user(request.user):
            return super().list(request, *args, **kwargs)

        origin = f"{request.scheme}://{request.get_host()}"
        cache_key = make_product_list_cache_key(request.query_params, origin)
        cached_data = get_product_list_cache(cache_key)
        if cached_data is not None:
            canonicalize_product_list_pagination_links(cached_data)
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            canonicalize_product_list_pagination_links(response.data)
            set_product_list_cache(cache_key, response.data)
        return response

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        queryset = Product.objects.select_related("category")
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(
                status=Product.Status.ACTIVE,
                category__is_active=True,
            )
        return self.apply_product_filters(queryset)

    def apply_product_filters(self, queryset):
        params = self.request.query_params
        category = params.get("category")
        keyword = params.get("keyword")
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        ordering = params.get("ordering")

        if category:
            try:
                category_id = int(category)
            except (TypeError, ValueError):
                raise ValidationError({"category": "分类 ID 必须是整数"})
            queryset = queryset.filter(category_id=category_id)
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword) | Q(description__icontains=keyword)
            )
        if min_price:
            queryset = queryset.filter(price__gte=self.parse_price(min_price, "min_price"))
        if max_price:
            queryset = queryset.filter(price__lte=self.parse_price(max_price, "max_price"))

        allowed_ordering = {
            "created_at",
            "price",
            "sales_count",
            "-created_at",
            "-price",
            "-sales_count",
        }
        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering)

        return queryset

    def parse_price(self, value, field_name):
        try:
            price = Decimal(value)
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({field_name: "价格必须是合法数字"})
        if price < 0:
            raise ValidationError({field_name: "价格不能小于 0"})
        return price

    def retrieve(self, request, *args, **kwargs):
        product_id = kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        if not is_admin_user(request.user):
            cached_data = get_product_detail_cache(product_id)
            if cached_data is not None:
                return api_response(data=cached_data)

        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        if instance.status == Product.Status.ACTIVE:
            set_product_detail_cache(instance.id, data)

        return api_response(data=data)
    
    ''' def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(data=serializer.data)'''


class AdminProductViewSet(ApiModelViewSetResponseMixin, viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").all()
    permission_classes = (IsAdminRole,)

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ProductCreateUpdateSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def perform_create(self, serializer):
        product = serializer.save()
        delete_product_detail_cache(product.id)
        invalidate_product_list_cache()

    def perform_update(self, serializer):
        product = serializer.save()
        delete_product_detail_cache(product.id)
        invalidate_product_list_cache()

    def perform_destroy(self, instance):
        instance.status = Product.Status.INACTIVE
        instance.save(update_fields=["status", "updated_at"])
        delete_product_detail_cache(instance.id)
        invalidate_product_list_cache()
