import logging

from celery import shared_task
from django.conf import settings
from django.db import OperationalError
from django.utils import timezone

from apps.orders.models import Order


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    ignore_result=True,
    acks_late=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def cancel_expired_order(self, order_id: int):
    from apps.orders.services import expire_order

    result = expire_order(order_id)
    logger.info("Order timeout task finished: order_id=%s result=%s", order_id, result)
    return result


@shared_task(ignore_result=True)
def dispatch_expired_orders():
    """Compensate for timeout messages lost while the broker or worker was down."""
    order_ids = list(
        Order.objects.filter(
            status=Order.Status.PENDING,
            expires_at__lte=timezone.now(),
        )
        .order_by("expires_at")
        .values_list("id", flat=True)[: settings.ORDER_TIMEOUT_SWEEP_BATCH_SIZE]
    )
    for order_id in order_ids:
        cancel_expired_order.delay(order_id)
    return len(order_ids)
