import pickle

from django.core.cache.backends.locmem import LocMemCache
from django.core.cache.backends.redis import RedisCache, RedisCacheClient


COMPARE_AND_DELETE_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
end
return 0
""".strip()


class AtomicRedisCacheClient(RedisCacheClient):
    def compare_and_delete(self, key: str, expected_value) -> bool:
        client = self.get_client(key, write=True)
        serialized_value = self._serializer.dumps(expected_value)
        deleted = client.eval(
            COMPARE_AND_DELETE_SCRIPT,
            1,
            key,
            serialized_value,
        )
        return bool(deleted)


class AtomicRedisCache(RedisCache):
    """Redis cache backend with an atomic compare-and-delete operation."""

    def __init__(self, server, params):
        super().__init__(server, params)
        self._class = AtomicRedisCacheClient

    def compare_and_delete(self, key, expected_value, version=None) -> bool:
        key = self.make_and_validate_key(key, version=version)
        return self._cache.compare_and_delete(key, expected_value)


class AtomicLocMemCache(LocMemCache):
    """In-memory adapter that provides the same interface for the test suite."""

    def compare_and_delete(self, key, expected_value, version=None) -> bool:
        key = self.make_and_validate_key(key, version=version)
        with self._lock:
            if self._has_expired(key):
                self._delete(key)
                return False

            stored_value = pickle.loads(self._cache[key])
            if stored_value != expected_value:
                return False
            return self._delete(key)
