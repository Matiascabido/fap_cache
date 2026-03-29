FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cache_service.py .

ENV API_PORT=8000
ENV API_WORKERS=4
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["sh", "-c", "uvicorn cache_service:app --host 0.0.0.0 --port ${API_PORT} --workers ${API_WORKERS} --log-level info"]
