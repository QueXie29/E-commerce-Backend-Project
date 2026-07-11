from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.carts.models import CartItem
from apps.carts.serializers import (
    AddCartItemSerializer,
    CartItemSerializer,
    UpdateCartItemSerializer,
)
from apps.common.exceptions import BusinessException
from apps.common.responses import api_response


class CartView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        cart_items = self.get_cart_queryset(request.user)
        serializer = CartItemSerializer(cart_items, many=True)
        total_amount = sum(
            (item.subtotal for item in cart_items if item.selected),
            Decimal("0.00"),
        )
        return api_response(
            data={
                "items": serializer.data,
                "total_amount": f"{total_amount:.2f}",
            }
        )

    def get_cart_queryset(self, user):
        return (
            CartItem.objects.select_related("product", "product__category")
            .filter(user=user)
            .order_by("-created_at")
        )


class CartItemCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        cart_item, created = CartItem.objects.select_related("product").get_or_create(
            user=request.user,
            product=product,
            defaults={"quantity": quantity, "selected": True},
        )

        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock:
                raise BusinessException("商品库存不足", code=40001)
            cart_item.quantity = new_quantity
            cart_item.selected = True
            cart_item.save(update_fields=["quantity", "selected", "updated_at"])

        data = CartItemSerializer(
            CartItem.objects.select_related("product", "product__category").get(id=cart_item.id)
        ).data
        return api_response(
            data=data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def patch(self, request, pk):
        cart_item = self.get_cart_item(request.user, pk)
        serializer = UpdateCartItemSerializer(
            data=request.data,
            context={"cart_item": cart_item},
        )
        serializer.is_valid(raise_exception=True)

        for field in ("quantity", "selected"):
            if field in serializer.validated_data:
                setattr(cart_item, field, serializer.validated_data[field])
        cart_item.save(update_fields=[*serializer.validated_data.keys(), "updated_at"])

        return api_response(data=CartItemSerializer(cart_item).data)

    def delete(self, request, pk):
        cart_item = self.get_cart_item(request.user, pk)
        cart_item.delete()
        return api_response(data=None)

    def get_cart_item(self, user, pk):
        return get_object_or_404(
            CartItem.objects.select_related("product", "product__category"),
            pk=pk,
            user=user,
        )


class CartClearView(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request):
        CartItem.objects.filter(user=request.user).delete()
        return api_response(data=None)
