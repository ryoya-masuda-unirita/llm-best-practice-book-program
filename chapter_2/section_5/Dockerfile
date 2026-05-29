FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS base
ENV UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

FROM base AS builder

ENV PROJECT_DIR=/app
WORKDIR ${PROJECT_DIR}

COPY pyproject.toml ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

COPY src ${PROJECT_DIR}/src/

FROM python:3.13-slim AS runtime

ENV PROJECT_DIR=/app
WORKDIR ${PROJECT_DIR}

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY src ${PROJECT_DIR}/src/

EXPOSE 8000

CMD ["uvicorn", "src.api.llm_server:app", "--host", "0.0.0.0", "--port", "8000"]
