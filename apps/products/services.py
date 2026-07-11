import hashlib
import json
import logging

from django.core.cache import cache


logger = logging.getLogger(__name__)

PRODUCT_DETAIL_CACHE_KEY = "product:detail:{product_id}"
PRODUCT_DETAIL_CACHE_TTL = 300
PRODUCT_LIST_KEYS_CACHE_KEY = "product:list:keys"


def make_product_detail_cache_key(product_id: int) -> str:
    return PRODUCT_DETAIL_CACHE_KEY.format(product_id=product_id)


def make_product_list_cache_key(query_params) -> str:
    normalized = json.dumps(
        sorted(query_params.items()),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()
    return f"product:list:{digest}"


def get_product_detail_cache(product_id: int):
    try:
        return cache.get(make_product_detail_cache_key(product_id))
    except Exception as exc:
        logger.warning("Failed to read product detail cache: %s", exc)
        return None


def set_product_detail_cache(product_id: int, data) -> None:
    try:
        cache.set(
            make_product_detail_cache_key(product_id),
            data,
            timeout=PRODUCT_DETAIL_CACHE_TTL,
        )
    except Exception as exc:
        logger.warning("Failed to write product detail cache: %s", exc)


def delete_product_detail_cache(product_id: int) -> None:
    try:
        cache.delete(make_product_detail_cache_key(product_id))
    except Exception as exc:
        logger.warning("Failed to delete product detail cache: %s", exc)
