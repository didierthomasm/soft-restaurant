FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --frozen --no-dev
COPY scripts/ /scripts/

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn --factory tabernas.main:create_app --host 0.0.0.0 --port 8000"]
