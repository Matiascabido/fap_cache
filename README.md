# fap_cache

Proyecto para deployar Redis con Docker y usarlo como caché de datos.

## Archivos principales

- `docker-compose.yml`: despliega Redis y un servicio HTTP de caché.
- `redis/redis.conf`: configuración de Redis optimizada para caché con `maxmemory-policy allkeys-lru`.
- `cache_service.py`: servicio FastAPI que expone endpoints para cargar, consultar y borrar cache.
- `example_cache.py`: ejemplo de uso directo de Redis desde Python.
- `Dockerfile`: define la imagen del servicio HTTP.
- `.env`: variables de entorno para configurar Redis y TTL por defecto.

## Cómo ejecutar

1. Levantar Redis y el servicio HTTP:

```bash
docker compose up -d --build
```

2. Verificar los contenedores:

```bash
docker compose ps
```

3. Probar el servicio HTTP:

```bash
curl http://localhost:8000/cache/health
```

4. Alternativa: ejecutar el ejemplo de caché directo con Redis (requiere `redis` para Python):

```bash
pip install redis
python3 example_cache.py
```

## Endpoints disponibles

- `GET /cache/health` - verifica la conexión con Redis.
- `GET /cache/{key}` - obtiene el valor y TTL de una clave.
- `GET /cache` - lista claves que coinciden con un patrón.
- `POST /cache` - guarda un valor en caché con TTL.
- `DELETE /cache/{key}` - elimina una clave de la caché.
- `DELETE /cache` - vacía la caché (flush DB).

### Ejemplo de petición para listar claves

```bash
curl "http://localhost:8000/cache?pattern=cache:*&limit=50"
```

### Ejemplo de petición para vaciar toda la caché

```bash
curl -X DELETE http://localhost:8000/cache
```

### Ejemplo de petición para guardar datos

```bash
curl -X POST http://localhost:8000/cache \
  -H "Content-Type: application/json" \
  -d '{"key":"cache:usuario:1","value":{"nombre":"Ana"},"ttl":120}'
```

### Ejemplo de petición para leer datos

```bash
curl http://localhost:8000/cache/cache:usuario:1
```

## Configuración por variables de entorno

El servicio HTTP y Redis pueden configurarse con variables de entorno en `.env`:

- `REDIS_HOST` - host de Redis.
  - Si usas `docker compose` con este `docker-compose.yml`, el valor es `redis`.
  - Si usas un solo contenedor con Redis integrado (por ejemplo Render con `Dockerfile` o `Dockerfile.render`), usa `localhost`.
  - En Render, usa las variables de entorno de la plataforma para anular este valor.
- `REDIS_PORT` - puerto de Redis (por defecto `6379`).
- `REDIS_DB` - base de datos Redis (por defecto `0`).
- `REDIS_PASSWORD` - contraseña de Redis si se usa.
- `CACHE_TTL_SECONDS` - TTL por defecto para nuevas claves cuando no se especifica.
- `API_PORT` - puerto de la API HTTP dentro del contenedor (por defecto `8000`).
- `API_WORKERS` - número de procesos Uvicorn para producción.
- `CACHE_LIST_LIMIT` - cantidad máxima de claves devueltas por `GET /cache`.

## Producción

- Para producción, usa `API_WORKERS` y `CACHE_LIST_LIMIT` para ajustar rendimiento.
- Si Redis queda expuesto fuera de la red Docker, configura `REDIS_PASSWORD` y protege el puerto.
- Si no necesitas acceso directo a Redis desde el host, mantén el servicio Redis accesible solo en la red interna de Docker.
- Usa `docker compose up -d --build` y supervisa con `docker compose ps`.

## Despliegue en Neon

Si despliegas tu aplicación en Neon usando Docker Compose y Redis está definido en el mismo stack, entonces el valor correcto es:

- `REDIS_HOST=redis`

Esto aplica porque el servicio Redis se llama `redis` en `docker-compose.yml`, y Docker Compose resuelve ese nombre dentro de la red interna del stack.

Usa el `Dockerfile` actual con estas variables de entorno:

- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_DB`
- `REDIS_PASSWORD`
- `CACHE_TTL_SECONDS`
- `API_PORT`
- `API_WORKERS`
- `CACHE_LIST_LIMIT`

Si en cambio usas un Redis externo fuera del stack, pon el host real de esa instancia.

Para más detalles, consulta `NEON_DEPLOY.md`.

## Despliegue en Render

Render no levanta un `docker-compose.yml` automáticamente dentro de una sola aplicación web.

- Con un solo contenedor que incluya Redis y la app, usa `REDIS_HOST=localhost`.
- `REDIS_HOST=redis` solo funciona si Redis está disponible en la misma red de contenedores y accesible por ese nombre.
- Si Render ejecuta solo el contenedor de la app, no habrá ningún host `redis`.

La alternativa es usar dos servicios Render conectados en red privada o empaquetar Redis y la app en una sola imagen.

### Comandos para Render

- `Build Command`:

```bash
docker build -t fap-cache .
```

- `Start Command`:

```bash
/usr/local/bin/docker-entrypoint.sh
```

Para más detalles, consulta `RENDER_DEPLOY.md`.

- Si el otro proyecto ya puede conectarse directamente a Redis, lo más eficiente es usar Redis como cache directo desde ese proyecto.
- Si necesitas desacoplar el acceso, exponer un pequeño servicio HTTP es una buena opción. Este repositorio ya ofrece ambos modelos:
  - `example_cache.py` para conexión directa.
  - `cache_service.py` para usar un servicio RESTful.

## Notas de configuración

- Redis escucha en `localhost:6379` desde el host.
- El servicio HTTP expone `localhost:8000`.
- Redis usa el volumen Docker `redis_data` para persistencia.
- `maxmemory 256mb` y `maxmemory-policy allkeys-lru` permiten usar Redis como caché de datos temporales.
