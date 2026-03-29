# Render Deployment Guide for fap_cache

Este proyecto está diseñado para usar Redis y una API de caché con Docker Compose.

## Importante

Render no construye automáticamente un `docker-compose.yml` como parte de una sola aplicación web.
Si el objetivo es desplegar en Render, tienes dos rutas reales:

1. Usar un entorno que soporte Docker Compose completo (no todos los planes/servicios de Render lo permiten).
2. Convertir tu despliegue a un solo contenedor que arranque Redis y la API juntos.

## Si quieres manejar Redis con Docker Compose

Esto funciona localmente o en un host con soporte Compose:

- `REDIS_HOST=redis`
- `REDIS_PORT=6379`
- `REDIS_DB=0`
- `REDIS_PASSWORD=` si no usas contraseña

En este caso, el servicio `redis` debe existir en el mismo stack de Compose:

```yaml
services:
  redis:
    image: redis:7.2-alpine
  cache-api:
    build: .
    env_file: .env
    depends_on:
      - redis
```

## Si desplegas en Render

Render Web Services usa un único `Dockerfile` para construir y ejecutar una sola imagen.

### Opción recomendada para Render

Si querés desplegar en un solo contenedor y no usar un servicio Redis externo, usa `Dockerfile.render`.
Este Dockerfile instala Redis dentro de la imagen y arranca Redis antes de iniciar la API.

En ese caso, la configuración correcta es:

- `REDIS_HOST=localhost`
- `REDIS_PORT=6379`
- `REDIS_DB=0`
- `REDIS_PASSWORD=` 
- `CACHE_TTL_SECONDS=60`
- `API_PORT=8000`
- `API_WORKERS=4`
- `CACHE_LIST_LIMIT=100`

### Start command para Render

Si Render usa `Dockerfile.render`, el start command puede ser:

```bash
/usr/local/bin/docker-entrypoint.sh
```

### Nota importante

`REDIS_HOST=redis` solo funciona si Redis está disponible en la misma red de contenedores y accesible por ese nombre.
En un solo contenedor con Redis integrado, el host debe ser `localhost`.
