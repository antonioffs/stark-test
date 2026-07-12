# Starkbank challenge

Stark Bank backend developer challenge.

## Requirements

- Docker and Docker Compose (`docker compose` plugin)
- `make`

## Setup

Create the `.env` file from the example:

```bash
cp .env.example .env
```

## Commands

```bash
make build            # build the images
make up               # start the services (web, redis, celery-worker, celery-beat)
make up-d             # start the services in the background
make down             # stop the services
make logs             # follow the logs

make migrate          # apply migrations
make makemigrations   # generate new migrations
make createsuperuser  # create a superuser for admin access
make check            # run Django's system check
make shell            # open the Django shell
make format           # format files
make test             # run the tests
```

The application is available at `http://localhost:8000`.