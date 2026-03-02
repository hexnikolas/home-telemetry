FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Copy the shared module to match the path referenced in pyproject.toml
COPY shared/ /home/nikos/home-telemetry/shared/

# Copy the api service
COPY services/api/ .

# Remove lock file so poetry resolves paths fresh from pyproject.toml
# (lock file has the host machine's path for the local shared package)
RUN rm -f poetry.lock && poetry install --without dev

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
