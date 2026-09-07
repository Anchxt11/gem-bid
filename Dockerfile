FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copy the rest of the project (backend/, alembic/, src/, etc.)
COPY . .
RUN uv sync --frozen

# Put the venv on PATH so we don't need `uv run` for every command
ENV PATH="/app/.venv/bin:$PATH"

# main.py expects to be run with backend/ as the working directory
WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]