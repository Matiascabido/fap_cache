import json
import os
from typing import Any, Optional

import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
DEFAULT_TTL = int(os.getenv("CACHE_TTL_SECONDS", "60"))
CACHE_LIST_LIMIT = int(os.getenv("CACHE_LIST_LIMIT", "100"))

app = FastAPI(title="fap_cache_service", version="1.0.0")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD or None,
    decode_responses=True,
)


class CacheItem(BaseModel):
    key: str
    value: Any
    ttl: Optional[int] = None


def serialize_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value)


def deserialize_value(value: Optional[str]) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


@app.get("/cache/health")
def health() -> dict[str, str]:
    try:
        pong = redis_client.ping()
        return {"status": "ok" if pong else "error"}
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/cache/{key}")
def get_cache(key: str) -> dict[str, Any]:
    try:
        value = redis_client.get(key)
        if value is None:
            raise HTTPException(status_code=404, detail="Key not found")

        ttl = redis_client.ttl(key)
        return {"key": key, "value": deserialize_value(value), "ttl": ttl}
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/cache")
def list_cache(pattern: str = "*", limit: int = CACHE_LIST_LIMIT) -> dict[str, Any]:
    try:
        keys = []
        for key in redis_client.scan_iter(match=pattern, count=min(limit, 1000)):
            keys.append(key)
            if len(keys) >= limit:
                break

        return {"pattern": pattern, "keys": keys, "count": len(keys)}
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.delete("/cache")
def clear_cache() -> dict[str, Any]:
    try:
        redis_client.flushdb()
        return {"status": "ok", "message": "Cache cleared"}
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/cache")
def set_cache(item: CacheItem) -> dict[str, Any]:
    ttl = item.ttl if item.ttl is not None else DEFAULT_TTL
    try:
        serialized = serialize_value(item.value)
        redis_client.set(item.key, serialized, ex=ttl)
        return {"key": item.key, "ttl": ttl}
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.delete("/cache/{key}")
def delete_cache(key: str) -> dict[str, Any]:
    try:
        deleted = redis_client.delete(key)
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Key not found")
        return {"key": key, "deleted": bool(deleted)}
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
