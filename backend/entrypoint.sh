#!/bin/sh
# Inicia a API. Argumentos extras vão para o uvicorn (ex.: --reload no docker-compose de dev).
set -e

# TODO(#5): rodar "alembic upgrade head" aqui quando as migrações existirem.

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
