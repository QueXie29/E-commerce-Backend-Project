from functools import partial

from django.contrib import admin
from django.db import transaction

from apps.products.models import Category, Product
from apps.products.services import (
    invalidate_category_caches,
    invalidate_product_caches,
    invalidate_product_list_cache,
)


class ProductListCacheInvalidationAdminMixin:
    def get_cache_invalidation_callback(self, obj=None):
        return invalidate_product_list_cache

    def get_queryset_cache_invalidation_callback(self, queryset):
        return self.get_cache_invalidation_callback()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        transaction.on_commit(self.get_cache_invalidation_callback(obj))

    def delete_model(self, request, obj):
        callback = self.get_cache_invalidation_callback(obj)
        super().delete_model(request, obj)
        transaction.on_commit(callback)

    def delete_queryset(self, request, queryset):
        callback = self.get_queryset_cache_invalidation_callback(queryset)
        super().delete_queryset(request, queryset)
        transaction.on_commit(callback)


@admin.register(Category)
class CategoryAdmin(ProductListCacheInvalidationAdminMixin, admin.ModelAdmin):
    list_display = ("id", "name", "slug", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    def get_cache_invalidation_callback(self, obj=None):
        if obj is None:
            return super().get_cache_invalidation_callback(obj)
        return partial(invalidate_category_caches, obj.id)


@admin.register(Product)
class ProductAdmin(ProductListCacheInvalidationAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "category",
        "price",
        "stock",
        "sales_count",
        "status",
        "created_at",
    )
    list_filter = ("status", "category")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}

    def get_cache_invalidation_callback(self, obj=None):
        if obj is None:
            return super().get_cache_invalidation_callback(obj)
        return partial(invalidate_product_caches, (obj.id,))

    def get_queryset_cache_invalidation_callback(self, queryset):
        product_ids = tuple(queryset.values_list("id", flat=True))
        return partial(invalidate_product_caches, product_ids)


# Register your models here.
