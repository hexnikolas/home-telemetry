FROM python:3.11-slim

WORKDIR /app

# Install dependencies (will add pyproject.toml/requirements.txt soon)
RUN pip install --no-cache-dir redis aioredis httpx pyyaml loguru

# Copy shared code
COPY shared /shared
ENV PYTHONPATH="/:/shared"

# Copy local app
COPY services/notifier/app ./app

CMD ["python", "app/main.py"]
