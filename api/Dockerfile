FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir uv \
    && addgroup --system app \
    && adduser --system --ingroup app app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN uv sync --frozen --no-dev \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["sh", "-c", "attempt=1; until alembic upgrade head; do if [ \"$attempt\" -ge 10 ]; then exit 1; fi; attempt=$((attempt + 1)); sleep 2; done; exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
