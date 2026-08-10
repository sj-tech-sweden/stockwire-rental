FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

ARG VERSION=unknown
# Set default IMAGE_TAG from the build arg; container runtime can override it.
ENV IMAGE_TAG=$VERSION

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
RUN pip install --no-cache-dir .[dev]

COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY tests /app/tests
COPY scripts /app/scripts

# Write build-time VERSION into the image so the running app can expose it
RUN /bin/sh -c 'echo "${VERSION}" > /app/VERSION'

# Create non-root user and switch to it
RUN useradd -m -d /app -s /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
