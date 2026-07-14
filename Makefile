.PHONY: install up down migrate upgrade run

install:
	pip install -r requirements.txt

up:
	docker-compose up -d

down:
	docker-compose down

# Autogenerate a new migration: make migrate m="add table"
migrate:
	cd app && alembic revision --autogenerate -m "$(m)"

upgrade:
	cd app && alembic upgrade head

run:
	python -m app.main
