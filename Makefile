.PHONY: migrate makemigrations check shell test build up up-d down logs

# Runs a one-off command in a throwaway web container: starts redis,
# executes the command, then stops redis. Assumes no stack is running.
define run_in_container
	@docker compose run --rm web $(1); \
	status=$$?; \
	docker compose stop redis; \
	exit $$status
endef

migrate:
	$(call run_in_container,python manage.py migrate)

makemigrations:
	$(call run_in_container,python manage.py makemigrations)

check:
	$(call run_in_container,python manage.py check)

shell:
	$(call run_in_container,python manage.py shell)

test:
	$(call run_in_container,pytest)

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