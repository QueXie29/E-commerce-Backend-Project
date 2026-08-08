from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.common.permissions import is_admin_user
from apps.common.responses import api_response
from apps.orders.models import Order
from apps.orders.serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
)
from apps.orders.services import cancel_order, create_order_from_cart, pay_order


class OrderViewSet(viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = Order.objects.select_related("user").prefetch_related(
            "items",
            "items__product",
        )
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(user=self.request.user)

        status_value = self.request.query_params.get("status")
        if status_value:
            valid_statuses = {choice[0] for choice in Order.Status.choices}
            if status_value not in valid_statuses:
                raise ValidationError({"status": "订单状态不合法"})
            queryset = queryset.filter(status=status_value)

        return queryset.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        if self.action == "create":
            return OrderCreateSerializer
        return OrderDetailSerializer

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = OrderListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = OrderListSerializer(queryset, many=True)
        return api_response(data=serializer.data)

    def retrieve(self, request, pk=None):
        order = self.get_object()
        return api_response(data=OrderDetailSerializer(order).data)

    def create(self, request):
        serializer = OrderCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        result = create_order_from_cart(
            user=request.user,
            idempotency_key=serializer.validated_data["idempotency_key"],
            remark=serializer.validated_data.get("remark", ""),
        )
        response = api_response(
            data=OrderDetailSerializer(result.order).data,
            status=status.HTTP_201_CREATED,
        )
        if result.replayed:
            response["Idempotency-Replayed"] = "true"
        return response

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        order = pay_order(request.user, pk)
        return api_response(data=OrderDetailSerializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = cancel_order(request.user, pk)
        return api_response(data=OrderDetailSerializer(order).data)
