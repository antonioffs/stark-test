.PHONY: migrate makemigrations check shell test build up up-d down logs

# Runs a one-off `manage.py` command: starts redis, executes the command in
# a throwaway web container, then stops redis. Assumes no stack is running.
define run_management_command
	@docker compose run --rm web python manage.py $(1); \
	status=$$?; \
	docker compose stop redis; \
	exit $$status
endef

migrate:
	$(call run_management_command,migrate)

makemigrations:
	$(call run_management_command,makemigrations)

check:
	$(call run_management_command,check)

shell:
	$(call run_management_command,shell)

test:
	$(call run_management_command,test)

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