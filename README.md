# gem-bid

AI-powered bid compliance verification platform for India's Government e-Marketplace (GeM).

## Stack

- FastAPI (backend)
- PostgreSQL
- SQLAlchemy + Alembic (migrations)
- uv (dependency management)
- Docker Compose (local dev environment)

## Prerequisites

- Docker & Docker Compose
- (Optional, for local non-Docker dev) Python 3.12 and [uv](https://docs.astral.sh/uv/)

## Getting Started

```bash
git clone <repo-url>
cd gem-bid
cp .env.example .env       # fill in any required values
make up                    # builds and starts backend + postgres
make migrate                # applies database migrations
```

The API will be running at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

## Common Commands

Run `make help` to see all available commands, including:

- `make logs` — tail container logs
- `make shell` — open a shell inside the backend container
- `make db-shell` — open a psql shell inside the database container
- `make migration msg="add users table"` — create a new alembic migration

## Project Structure

```
gem-bid/ 
├── alembic/ # migration scripts
├── backend/
│ ├── app/ # FastAPI application
│ └── tests/
├── src/ # (describe what this is for)
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── uv.lock
```

## Local Development Without Docker

```bash
uv sync
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload
```

