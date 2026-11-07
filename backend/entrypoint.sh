#!/bin/sh
# Inicia a API. Argumentos extras vão para o uvicorn (ex.: --reload no docker-compose de dev).
set -e

# Aplica as migrações pendentes; com o banco inacessível o container encerra com erro (set -e).
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
