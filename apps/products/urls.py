from rest_framework.routers import DefaultRouter

from apps.products.views import (
    AdminCategoryViewSet,
    AdminProductViewSet,
    CategoryViewSet,
    ProductViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("admin/categories", AdminCategoryViewSet, basename="admin-category")
router.register("admin/products", AdminProductViewSet, basename="admin-product")

urlpatterns = router.urls
