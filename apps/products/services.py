import hashlib
import json
import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.core.cache import cache

from apps.products.models import Product


logger = logging.getLogger(__name__)

PRODUCT_DETAIL_CACHE_KEY = "product:detail:{product_id}"
PRODUCT_DETAIL_CACHE_TTL = 300
#详情缓存

def make_product_detail_cache_key(product_id: int) -> str:
    return PRODUCT_DETAIL_CACHE_KEY.format(product_id=product_id)

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


#列表缓存
PRODUCT_LIST_CACHE_KEY = "product:list:v{version}:{digest}"
PRODUCT_LIST_CACHE_TTL = 300
PRODUCT_LIST_CACHE_VERSION_KEY = "product:list:version"
PRODUCT_LIST_CACHE_ALLOWED_PARAMS = (
    "category",
    "keyword",
    "min_price",
    "max_price",
    "ordering",
    "page",
    "page_size",
)

def get_product_list_cache_version():
    try:
        version = cache.get(PRODUCT_LIST_CACHE_VERSION_KEY)
        if version is None:
            cache.add(PRODUCT_LIST_CACHE_VERSION_KEY, 1, timeout=None)
            version = cache.get(PRODUCT_LIST_CACHE_VERSION_KEY)
        return int(version if version is not None else 1)
    except Exception as exc:
        logger.warning("Failed to read product list cache version: %s", exc)
        return None


def normalize_product_list_query_params(query_params):
    normalized = []
    for name in PRODUCT_LIST_CACHE_ALLOWED_PARAMS:
        value = query_params.get(name)
        if value in (None, ""):
            continue
        normalized.append((name, str(value)))
    return normalized


def canonicalize_product_list_pagination_link(link):
    if link is None:
        return None

    parsed = urlsplit(link)
    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    canonical_query = urlencode(normalize_product_list_query_params(query_params))
    return urlunsplit(parsed._replace(query=canonical_query))


def canonicalize_product_list_pagination_links(payload):
    if not isinstance(payload, dict):
        return payload

    pagination_data = payload.get("data")
    if not isinstance(pagination_data, dict):
        return payload

    for relation in ("next", "previous"):
        if relation in pagination_data:
            pagination_data[relation] = canonicalize_product_list_pagination_link(
                pagination_data[relation]
            )
    return payload


def make_product_list_cache_key(query_params, origin: str):
    version = get_product_list_cache_version()
    if version is None:
        return None

    normalized = json.dumps(
        {
            "origin": origin,
            "params": normalize_product_list_query_params(query_params),
        },
        ensure_ascii=False,    #中文不强制转换成 \uXXXX。
        separators=(",", ":"),  #去掉多余空格，保证字符串紧凑、稳定。
        sort_keys=True,          #字典键顺序固定，避免顺序不同导致结果不同。
    )
    digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()
    return PRODUCT_LIST_CACHE_KEY.format(version=version, digest=digest)


def get_product_list_cache(cache_key):
    if cache_key is None:
        return None
    try:
        return cache.get(cache_key)
    except Exception as exc:
        logger.warning("Failed to read product list cache: %s", exc)
        return None


def set_product_list_cache(cache_key, data) -> None:
    if cache_key is None:
        return None
    try:
        cache.set(cache_key, data, timeout=PRODUCT_LIST_CACHE_TTL)
    except Exception as exc:
        logger.warning("Failed to write product list cache: %s", exc)
    return None


def invalidate_product_list_cache():
    try:
        cache.add(PRODUCT_LIST_CACHE_VERSION_KEY, 1, timeout=None)
        return cache.incr(PRODUCT_LIST_CACHE_VERSION_KEY)
    except Exception as exc:
        logger.warning("Failed to invalidate product list cache: %s", exc)
        return None

def delete_category_product_detail_caches(category_id: int) -> None:
    try:
        product_ids = Product.objects.filter(category_id=category_id).values_list(
            "id",
            flat=True,
        )
        cache_keys = [
            make_product_detail_cache_key(product_id) for product_id in product_ids
        ]
        if cache_keys:
            cache.delete_many(cache_keys)
    except Exception as exc:
        logger.warning("Failed to delete category product detail caches: %s", exc)


def invalidate_category_caches(category_id: int) -> None:
    invalidate_product_list_cache()
    delete_category_product_detail_caches(category_id)
