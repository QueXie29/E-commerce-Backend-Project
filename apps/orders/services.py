import uuid
import logging
from decimal import Decimal
from functools import partial

from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.carts.models import CartItem
from apps.common.exceptions import BusinessException
from apps.common.permissions import is_admin_user
from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.products.services import invalidate_product_caches


logger = logging.getLogger(__name__)

#防重复提交锁
ORDER_CREATE_LOCK_KEY = "lock:order:create:user:{user_id}"
ORDER_CREATE_LOCK_TTL = 10

#EC + 时间戳 + 随机后缀   EC-20260718153045123456-A8F31C9D
def generate_order_no() -> str:
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
    suffix = uuid.uuid4().hex[:8].upper()
    return f"EC{timestamp}{suffix}"


def create_order_from_cart(user, remark: str = "") -> Order:
    lock_key = ORDER_CREATE_LOCK_KEY.format(user_id=user.id)
    lock_value = uuid.uuid4().hex

    if not cache.add(lock_key, lock_value, timeout=ORDER_CREATE_LOCK_TTL):
        raise BusinessException(
            "订单正在处理中，请勿重复提交",
            code=40900,
            status_code=409,
        )

    try:
        with transaction.atomic():
            #list() 会立即执行 SQL，并把结果转换成普通 Python 列表
            cart_items = list(
                CartItem.objects.select_related("product", "product__category")
                .filter(user=user, selected=True)
                .order_by("id")
            )
            if not cart_items:
                raise BusinessException("购物车为空", code=40003)

            product_ids = [item.product_id for item in cart_items]
            products = (
                Product.objects.select_for_update()
                .select_related("category")
                .filter(id__in=product_ids)
            )
            product_map = {product.id: product for product in products}
            affected_product_ids = tuple(sorted(product_map))

            order = Order.objects.create(
                order_no=generate_order_no(),
                user=user,
                total_amount=Decimal("0.00"),
                status=Order.Status.PENDING,
                remark=remark or "",
            )

            total_amount = Decimal("0.00")
            order_items = []

            for cart_item in cart_items:
                product = product_map.get(cart_item.product_id)
                if product is None:
                    raise BusinessException("商品不存在", code=40400, status_code=404)

                if product.status != Product.Status.ACTIVE or not product.category.is_active:
                    raise BusinessException("商品已下架", code=40002)

                if product.stock < cart_item.quantity:
                    raise BusinessException(
                        "商品库存不足",
                        code=40001,
                        data={
                            "product_id": product.id,
                            "product_name": product.name,
                            "stock": product.stock,
                            "requested_quantity": cart_item.quantity,
                        },
                    )

                subtotal = product.price * cart_item.quantity
                total_amount += subtotal

                product.stock -= cart_item.quantity
                product.sales_count += cart_item.quantity
                product.save(update_fields=["stock", "sales_count", "updated_at"])

                order_items.append(
                    OrderItem(
                        order=order,
                        product=product,
                        product_name=product.name,
                        product_price=product.price,
                        quantity=cart_item.quantity,
                        subtotal=subtotal,
                    )
                )

            OrderItem.objects.bulk_create(order_items)
            order.total_amount = total_amount
            order.save(update_fields=["total_amount", "updated_at"])
            CartItem.objects.filter(id__in=[item.id for item in cart_items]).delete()
            transaction.on_commit(
                partial(invalidate_product_caches, affected_product_ids)
            )

            return get_order_for_response(order.id)
    finally:
        release_order_create_lock(lock_key, lock_value)


def release_order_create_lock(lock_key: str, lock_value: str) -> None:
    try:
        if cache.get(lock_key) == lock_value:
            cache.delete(lock_key)
    except Exception as exc:
        logger.warning("Failed to release order create lock: %s", exc)


def get_order_for_response(order_id: int) -> Order:
    return (
        Order.objects.select_related("user")
        .prefetch_related("items", "items__product")
        .get(id=order_id)
    )


def get_order_for_user(user, order_id: int, for_update: bool = False) -> Order:
    queryset = Order.objects.select_related("user").prefetch_related("items")
    if for_update:
        queryset = queryset.select_for_update()
    if not is_admin_user(user):
        queryset = queryset.filter(user=user)
    return get_object_or_404(queryset, id=order_id)


def pay_order(user, order_id: int) -> Order:
    with transaction.atomic():
        order = get_order_for_user(user, order_id, for_update=True)
        if order.status != Order.Status.PENDING:
            raise BusinessException("订单状态不允许该操作", code=40004)

        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at", "updated_at"])

    return get_order_for_response(order.id)


def cancel_order(user, order_id: int) -> Order:
    with transaction.atomic():
        order = get_order_for_user(user, order_id, for_update=True)
        if order.status != Order.Status.PENDING:
            raise BusinessException("订单状态不允许取消", code=40004)

        order_items = list(order.items.select_related("product").all())
        affected_product_ids = tuple(
            sorted({item.product_id for item in order_items})
        )
        for item in order_items:
            product = Product.objects.select_for_update().get(id=item.product_id)
            product.stock += item.quantity
            product.sales_count = max(product.sales_count - item.quantity, 0)
            product.save(update_fields=["stock", "sales_count", "updated_at"])

        order.status = Order.Status.CANCELLED
        order.cancelled_at = timezone.now()
        order.save(update_fields=["status", "cancelled_at", "updated_at"])
        transaction.on_commit(
            partial(invalidate_product_caches, affected_product_ids)
        )

    return get_order_for_response(order.id)
