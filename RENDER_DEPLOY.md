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

Este repositorio ya soporta un despliegue de un solo contenedor con Redis integrado.
Puedes usar el `Dockerfile` principal o `Dockerfile.render`, ambos están configurados para instalar Redis y copiar el entrypoint.

En ese caso, la configuración correcta es:

- `REDIS_HOST=localhost`
- `REDIS_PORT=6379`
- `REDIS_DB=0`
- `REDIS_PASSWORD=` 
- `CACHE_TTL_SECONDS=60`
- `API_PORT=8000`
- `API_WORKERS=4`
- `CACHE_LIST_LIMIT=100`

### Configuración en el Dashboard de Render

1. Crea un nuevo **Web Service**.
2. Conecta tu repositorio.
3. Elige **Docker** como el Runtime.
4. En **Environment Variables**, añade:
   - `REDIS_HOST`: `localhost` (Obligatorio para que la API encuentre el Redis interno)
   - `API_WORKERS`: `1` (Recomendado para el plan gratuito para evitar exceso de memoria)
   - `PORT`: `8000` (Render lo detectará automáticamente, pero puedes forzarlo)
   - `CACHE_TTL_SECONDS`: `60` (Opcional, tiempo de vida por defecto)
5. En **Health Check Path**, usa `/cache/health`.

### Ejecución Local con Docker (Modo Único)

Si quieres probar exactamente lo que se ejecutará en Render de forma local con un solo comando de Docker:

```bash
# Construir la imagen
docker build -t fap-cache-service .

# Ejecutar el contenedor
docker run -p 8000:8000 \
  -e REDIS_HOST=localhost \
  -e API_WORKERS=1 \
  fap-cache-service
```

### Persistencia en el plan gratuito

Ten en cuenta que en el plan **Free** de Render, los datos de Redis se perderán cuando el servicio entre en reposo (spin-down) o se reinicie, ya que no hay discos persistentes gratuitos para servicios web.
