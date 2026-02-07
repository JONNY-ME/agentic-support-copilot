.PHONY: dev down logs api-shell worker-shell fmt test


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