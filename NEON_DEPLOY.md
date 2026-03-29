# Neon Deployment Guide for fap_cache

Este proyecto ya tiene un `Dockerfile` listo para producción.

## Qué usar en Neon

- Construye el contenedor usando `Dockerfile`.
- La app escucha en `0.0.0.0:8000`.
- Usa `uvicorn` con `API_PORT` y `API_WORKERS` configurables.

## Variables de entorno recomendadas

Configura estas variables en Neon:

- `REDIS_HOST`: host de Redis (por ejemplo, la URL de tu instancia Redis gestionada).
- `REDIS_PORT`: `6379`
- `REDIS_DB`: `0`
- `REDIS_PASSWORD`: contraseña de Redis si es necesaria. Déjalo vacío si no se usa.
- `CACHE_TTL_SECONDS`: `60` o el valor por defecto deseado.
- `API_PORT`: `8000`
- `API_WORKERS`: `4`
- `CACHE_LIST_LIMIT`: `100`

## Redis en Neon

Si tu despliegue en Neon incluye tanto el servicio de Redis como el servicio `cache-api` en el mismo Docker Compose, entonces dentro del contenedor de la aplicación el host debe ser:

- `REDIS_HOST=redis`

Esto funciona porque el servicio Redis se llama `redis` en `docker-compose.yml`.

Si en cambio Neon solo despliega el contenedor de la aplicación y Redis está en otro servicio externo, entonces `REDIS_HOST` debe ser la URL/host real de esa instancia Redis.

Recomendación:

- Si usas Docker Compose completo, mantén `REDIS_HOST=redis`.
- Si usas Redis gestionado o externo, define `REDIS_HOST` con ese host.
- Nunca expongas Redis sin autenticación.

## Ejemplo de despliegue típico

1. En Neon, configura el servicio de aplicación usando el repositorio o la imagen del Dockerfile.
2. Define las variables de entorno listadas arriba.
3. Asegúrate de que el puerto `8000` esté expuesto por la aplicación.
4. Apunta `REDIS_HOST` a la instancia Redis correcta.

## Endpoints clave

- `GET /cache/health`
- `GET /cache/{key}`
- `GET /cache?pattern=...&limit=...`
- `POST /cache`
- `DELETE /cache/{key}`
- `DELETE /cache`

## Notas importantes

- Para producción, usa `API_WORKERS=4` o más según la carga.
- Ajusta `CACHE_TTL_SECONDS` y `CACHE_LIST_LIMIT` según tu uso.
- Si Redis está en un servicio de red privada, asegúrate de que Neon pueda conectarse.
