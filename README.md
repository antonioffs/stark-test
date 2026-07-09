# stark-test

Desafio de desenvolvedor backend da Stark Bank.

## Requisitos

- Docker e Docker Compose (plugin `docker compose`)
- `make`

## Configuração

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

## Comandos

```bash
make build            # builda as imagens
make up               # sobe os serviços (web, redis, celery-worker, celery-beat)
make up-d             # sobe os serviços em background
make down             # derruba os serviços
make logs             # acompanha os logs

make migrate          # aplica as migrations
make makemigrations   # gera novas migrations
make check            # roda o system check do Django
make shell            # abre o shell do Django
make test             # roda os testes
```

A aplicação fica disponível em `http://localhost:8000`.