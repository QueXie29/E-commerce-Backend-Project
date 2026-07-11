from django.urls import path

from apps.orders.views import OrderViewSet

order_list = OrderViewSet.as_view({"get": "list", "post": "create"})
order_detail = OrderViewSet.as_view({"get": "retrieve"})
order_pay = OrderViewSet.as_view({"post": "pay"})
order_cancel = OrderViewSet.as_view({"post": "cancel"})


urlpatterns = [
    path("", order_list, name="order-list"),
    path("<int:pk>/", order_detail, name="order-detail"),
    path("<int:pk>/pay/", order_pay, name="order-pay"),
    path("<int:pk>/cancel/", order_cancel, name="order-cancel"),
]
