from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase

from apps.common.cache import AtomicRedisCacheClient, COMPARE_AND_DELETE_SCRIPT
from apps.orders.services import release_order_create_lock


class AtomicCompareAndDeleteTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_lock_owner_can_release_lock(self):
        cache.set("order-lock", "owner-token", timeout=10)

        released = release_order_create_lock("order-lock", "owner-token")

        self.assertTrue(released)
        self.assertIsNone(cache.get("order-lock"))

    def test_non_owner_cannot_release_lock(self):
        cache.set("order-lock", "new-owner-token", timeout=10)

        released = release_order_create_lock("order-lock", "expired-owner-token")

        self.assertFalse(released)
        self.assertEqual(cache.get("order-lock"), "new-owner-token")

    @patch("apps.orders.services.cache.compare_and_delete")
    def test_cache_failure_is_logged_and_does_not_mask_business_result(
        self,
        compare_and_delete,
    ):
        compare_and_delete.side_effect = ConnectionError("redis unavailable")

        with self.assertLogs("apps.orders.services", level="WARNING") as logs:
            released = release_order_create_lock("order-lock", "owner-token")

        self.assertFalse(released)
        self.assertIn("redis unavailable", logs.output[0])


class AtomicRedisCacheClientTests(SimpleTestCase):
    def test_compare_and_delete_executes_lua_with_serialized_owner_token(self):
        cache_client = AtomicRedisCacheClient(["redis://redis:6379/0"])
        redis_client = Mock()
        redis_client.eval.return_value = 1

        with patch.object(cache_client, "get_client", return_value=redis_client):
            released = cache_client.compare_and_delete(
                ":1:order-lock",
                "owner-token",
            )

        self.assertTrue(released)
        redis_client.eval.assert_called_once_with(
            COMPARE_AND_DELETE_SCRIPT,
            1,
            ":1:order-lock",
            cache_client._serializer.dumps("owner-token"),
        )

    def test_compare_and_delete_reports_owner_mismatch(self):
        cache_client = AtomicRedisCacheClient(["redis://redis:6379/0"])
        redis_client = Mock()
        redis_client.eval.return_value = 0

        with patch.object(cache_client, "get_client", return_value=redis_client):
            released = cache_client.compare_and_delete(
                ":1:order-lock",
                "expired-owner-token",
            )

        self.assertFalse(released)
