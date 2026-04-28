FROM python:3.12-slim@sha256:804ddf3251a60bbf9c92e73b7566c40428d54d0e79d3428194edf40da6521286

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/parallax/.venv \
    PATH="/opt/parallax/.venv/bin:${PATH}" \
    PYTHONPATH="/app/services/worker:/app/services/api:/app/packages/contracts:/app/packages/db"

WORKDIR /app

RUN groupadd --gid 1000 parallax \
    && useradd --uid 10001 --gid 1000 --create-home parallax \
    && python -m pip install --no-cache-dir uv==0.9.17

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY packages/contracts packages/contracts
COPY packages/db packages/db
COPY services/api services/api
COPY services/worker services/worker

USER 10001:1000

CMD ["python", "-m", "parallax_worker.main"]
