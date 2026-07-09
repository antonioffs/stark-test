.PHONY: migrate makemigrations check shell test build up up-d down logs

migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

check:
	docker compose exec web python manage.py check

shell:
	docker compose exec web python manage.py shell

test:
	docker compose exec web python manage.py test

build:
	docker compose build

up:
	docker compose up

up-d:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f