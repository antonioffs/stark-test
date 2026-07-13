# Starkbank challenge

Stark Bank backend developer challenge, made to evaluate the skills to join the great house of the north.

## Requirements

- Docker and Docker Compose (`docker compose` plugin)
- `make`

## Setup

Create the `.env` file from the example:

```bash
cp .env.example .env
```

### Environment variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key. |
| `DEBUG` | Django debug mode. |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts. Already includes the ngrok domains needed for the webhook tunnel (see below). |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis connection used by Celery. |
| `STARKBANK_KEY` | Private key (EC) of your Stark Bank Sandbox Project. |
| `STARKBANK_PROJECT_ID` | Stark Bank Sandbox Project ID. |
| `STARKBANK_ENVIRONMENT` | Stark Bank environment (`sandbox` or `production`). |
| `NGROK_AUTHTOKEN` | ngrok authtoken, used to expose the local webhook endpoint (free account, see [ngrok.com](https://ngrok.com)). |

`STARKBANK_KEY`/`STARKBANK_PROJECT_ID` come from a Project created in your Stark Bank Sandbox account. Never commit real values — only `.env.example` is tracked, with placeholders.

## Webhook

The app exposes an invoice webhook endpoint at `/invoice-webhook/starkbank`, which validates the Stark Bank signature, deduplicates redelivered events, and reacts to `paid`/`overdue`/`canceled` invoice statuses (marking the invoice accordingly and, when paid, sending the net amount via a Transfer).

For local development, `docker compose up` also starts an `ngrok` tunnel and a one-shot `webhook-registrar` service that automatically discovers the tunnel's public URL and registers/updates it as a Webhook on your Stark Bank Sandbox Project — no manual step required. This only needs `NGROK_AUTHTOKEN` set in `.env`.

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