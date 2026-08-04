from datetime import timedelta

from django.db import migrations, models


LEGACY_ORDER_TIMEOUT = timedelta(minutes=30)


def backfill_order_expiry(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    orders = Order.objects.filter(expires_at__isnull=True).only("id", "created_at")
    pending_updates = []
    for order in orders.iterator(chunk_size=500):
        order.expires_at = order.created_at + LEGACY_ORDER_TIMEOUT
        pending_updates.append(order)
        if len(pending_updates) == 500:
            Order.objects.bulk_update(pending_updates, ["expires_at"])
            pending_updates.clear()
    if pending_updates:
        Order.objects.bulk_update(pending_updates, ["expires_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="expires_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.RunPython(backfill_order_expiry, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="expires_at",
            field=models.DateTimeField(),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["status", "expires_at"],
                name="idx_order_status_expires",
            ),
        ),
    ]
