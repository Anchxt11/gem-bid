.PHONY: help up down build restart logs shell db-shell migrate migration ps clean

help:
	@echo "Available commands:"
	@echo "  make up            - Start all containers in the background"
	@echo "  make down          - Stop all containers"
	@echo "  make build         - Rebuild containers (after dependency changes)"
	@echo "  make restart       - Restart all containers"
	@echo "  make logs          - Tail logs from all containers"
	@echo "  make shell         - Open a shell in the backend container"
	@echo "  make db-shell      - Open a psql shell in the db container"
	@echo "  make migrate       - Apply all pending alembic migrations"
	@echo "  make migration msg='description' - Create a new alembic migration"
	@echo "  make ps            - Show running containers"
	@echo "  make clean         - Stop containers and wipe the db volume (destructive)"

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

restart:
	docker-compose restart

logs:
	docker-compose logs -f

shell:
	docker-compose exec backend bash

db-shell:
	docker-compose exec db psql -U $${POSTGRES_USER:-gembid} -d $${POSTGRES_DB:-gembid}

# alembic.ini lives at project root, not inside backend/, so override the workdir
migrate:
	docker-compose exec -w /app backend uv run alembic upgrade head

migration:
	docker-compose exec -w /app backend uv run alembic revision --autogenerate -m "$(msg)"

ps:
	docker-compose ps

clean:
	docker-compose down -v