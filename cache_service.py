import json
import logging
import os
import time
import zlib
from datetime import timedelta
from typing import Any, Optional, Generic, TypeVar, List, Union

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, Query, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Configuración Profesional ---
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    # Redis Config
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # App Config
    APP_TITLE: str = "FAP Cache Pro Service"
    APP_VERSION: str = "2.5.0"
    CACHE_DEFAULT_TTL: int = 3600  
    CACHE_KEY_PREFIX: str = "fap_cache"
    CACHE_LIST_LIMIT: int = 100
    
    # Security
    API_KEY: str = "super-secret-key-123"  # Cambiar en producción
    API_KEY_NAME: str = "X-API-Key"
    
    # Features
    COMPRESSION_THRESHOLD: int = 1024  # Bytes a partir de los cuales se comprime
    
    # Logging
    LOG_LEVEL: str = "INFO"

settings = Settings()

# --- Logging Setup ---
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cache-service")

# --- Security Dependency ---
api_key_header = APIKeyHeader(name=settings.API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return api_key

# --- Modelos de Datos (Pydantic) ---
T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    processing_time: Optional[float] = None

class CacheItem(BaseModel):
    key: str = Field(..., min_length=1, max_length=250)
    value: Any = Field(...)
    ttl: Optional[int] = Field(None, gt=0)

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        if ":" in v and v.startswith(":"):
             raise ValueError("Key cannot start with ':'")
        return v

class CacheDetail(BaseModel):
    key: str
    value: Any
    ttl: int
    compressed: bool = False

class CacheSummary(BaseModel):
    pattern: str
    keys: List[str]
    count: int

# --- Inicialización de FastAPI ---
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="Servicio de caché asíncrono, seguro y optimizado para alto rendimiento."
)

# --- Middleware de Tiempo de Respuesta ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# --- Manejador Global de Excepciones ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=BaseResponse(
            success=False,
            message="Internal server error",
            data=str(exc) if settings.LOG_LEVEL == "DEBUG" else None
        ).model_dump()
    )

# --- Cliente de Redis Asíncrono ---
async def get_redis():
    client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=False, # Necesario para manejar datos binarios (compresión)
    )
    try:
        yield client
    finally:
        await client.close()

# --- Helpers ---
def get_namespaced_key(key: str) -> str:
    if key.startswith(f"{settings.CACHE_KEY_PREFIX}:"):
        return key
    return f"{settings.CACHE_KEY_PREFIX}:{key}"

def strip_namespace(key: Union[str, bytes]) -> str:
    if isinstance(key, bytes):
        key = key.decode("utf-8")
    prefix = f"{settings.CACHE_KEY_PREFIX}:"
    if key.startswith(prefix):
        return key[len(prefix):]
    return key

def compress_value(data: str) -> bytes:
    """Comprime el valor si supera el umbral."""
    encoded = data.encode("utf-8")
    if len(encoded) > settings.COMPRESSION_THRESHOLD:
        return b"gz:" + zlib.compress(encoded)
    return encoded

def decompress_value(data: bytes) -> str:
    """Descomprime el valor si está marcado como comprimido."""
    if data.startswith(b"gz:"):
        return zlib.decompress(data[3:]).decode("utf-8")
    return data.decode("utf-8")

def serialize_value(value: Any) -> bytes:
    if not isinstance(value, str):
        value = json.dumps(value)
    return compress_value(value)

def deserialize_value(value: Optional[bytes]) -> Any:
    if value is None:
        return None
    try:
        decompressed = decompress_value(value)
        return json.loads(decompressed)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError, zlib.error):
        return decompress_value(value)

# --- Endpoints ---
@app.get("/", tags=["General"])
async def read_root():
    return {
        "service": settings.APP_TITLE,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", tags=["General"])
async def health(r: redis.Redis = Depends(get_redis)):
    try:
        await r.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/cache/{key}", 
         response_model=BaseResponse[CacheDetail], 
         tags=["Cache Operations"],
         dependencies=[Depends(verify_api_key)])
async def get_cache(key: str, r: redis.Redis = Depends(get_redis)):
    namespaced_key = get_namespaced_key(key)
    try:
        raw_value = await r.get(namespaced_key)
        if raw_value is None:
            raise HTTPException(status_code=404, detail=f"Key '{key}' not found")

        ttl = await r.ttl(namespaced_key)
        is_compressed = raw_value.startswith(b"gz:")
        
        return BaseResponse(
            data=CacheDetail(
                key=key,
                value=deserialize_value(raw_value),
                ttl=ttl,
                compressed=is_compressed
            )
        )
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        logger.error(f"Error fetching key {key}: {e}")
        raise HTTPException(status_code=503, detail="Database error")

@app.get("/cache", 
         response_model=BaseResponse[CacheSummary], 
         tags=["Cache Operations"],
         dependencies=[Depends(verify_api_key)])
async def list_cache(
    pattern: str = Query("*"), 
    limit: int = Query(settings.CACHE_LIST_LIMIT, le=1000),
    r: redis.Redis = Depends(get_redis)
):
    search_pattern = get_namespaced_key(pattern)
    try:
        keys = []
        async for key in r.scan_iter(match=search_pattern, count=100):
            keys.append(strip_namespace(key))
            if len(keys) >= limit:
                break

        return BaseResponse(
            data=CacheSummary(pattern=pattern, keys=keys, count=len(keys))
        )
    except Exception as e:
        logger.error(f"Error listing keys: {e}")
        raise HTTPException(status_code=503, detail="Database error")

@app.post("/cache", 
          response_model=BaseResponse, 
          status_code=status.HTTP_201_CREATED, 
          tags=["Cache Operations"],
          dependencies=[Depends(verify_api_key)])
async def set_cache(item: CacheItem, r: redis.Redis = Depends(get_redis)):
    namespaced_key = get_namespaced_key(item.key)
    ttl = item.ttl if item.ttl is not None else settings.CACHE_DEFAULT_TTL
    
    try:
        serialized = serialize_value(item.value)
        await r.set(namespaced_key, serialized, ex=ttl)
        return BaseResponse(message=f"Key '{item.key}' saved (Size: {len(serialized)} bytes)")
    except Exception as e:
        logger.error(f"Error saving key {item.key}: {e}")
        raise HTTPException(status_code=503, detail="Database error")

@app.delete("/cache/{key}", 
            response_model=BaseResponse, 
            tags=["Cache Operations"],
            dependencies=[Depends(verify_api_key)])
async def delete_cache(key: str, r: redis.Redis = Depends(get_redis)):
    namespaced_key = get_namespaced_key(key)
    try:
        deleted = await r.delete(namespaced_key)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
        return BaseResponse(message=f"Key '{key}' deleted")
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        logger.error(f"Error deleting key {key}: {e}")
        raise HTTPException(status_code=503, detail="Database error")

@app.delete("/cache", 
            response_model=BaseResponse, 
            tags=["Cache Operations"],
            dependencies=[Depends(verify_api_key)])
async def clear_cache(r: redis.Redis = Depends(get_redis)):
    try:
        pattern = f"{settings.CACHE_KEY_PREFIX}:*"
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
        return BaseResponse(message=f"Cleared {len(keys)} keys from namespace")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=503, detail="Database error")
