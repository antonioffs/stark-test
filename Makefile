.PHONY: migrate makemigrations check shell test format build up up-d down logs

define run_in_container
	@redis_was_running=$$(docker compose ps --status running -q redis); \
	docker compose run --rm web $(1); \
	status=$$?; \
	if [ -z "$$redis_was_running" ]; then \
		docker compose stop redis; \
	fi; \
	exit $$status
endef

migrate:
	$(call run_in_container,python manage.py migrate)

makemigrations:
	$(call run_in_container,python manage.py makemigrations)

createsuperuser:
	$(call run_in_container,python manage.py createsuperuser)

check:
	$(call run_in_container,python manage.py check)

shell:
	$(call run_in_container,python manage.py shell)

test:
	$(call run_in_container,pytest)

format:
	$(call run_in_container,black .)

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