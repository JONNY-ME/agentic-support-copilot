.PHONY: dev down logs api-shell worker-shell fmt test migrate seed

dev:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

api-shell:
	docker compose exec api bash

worker-shell:
	docker compose exec worker bash

fmt:
	python -m ruff format .

test:
	pytest -q

migrate:
	docker compose exec api alembic -c /app/alembic.ini upgrade head

seed:
	docker compose exec api python /app/scripts/dev/seed_demo.py