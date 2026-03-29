#!/bin/sh
set -e

API_PORT="${PORT:-${API_PORT:-8000}}"
API_WORKERS="${API_WORKERS:-1}"

# Start Redis in background
redis-server /usr/local/etc/redis/redis.conf --daemonize yes

# Wait for Redis to be available
for i in 1 2 3 4 5; do
  if redis-cli ping >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

exec uvicorn cache_service:app --host 0.0.0.0 --port "$API_PORT" --workers "$API_WORKERS" --log-level info
