#!/bin/sh
# Inicia a API. Argumentos extras vão para o uvicorn (ex.: --reload no docker-compose de dev).
set -e

# Aplica as migrações pendentes; com o banco inacessível o container encerra com erro (set -e).
# RUN_MIGRATIONS=0 pula este passo (o worker usa 0; só a API migra, ADR-027). Com várias
# instâncias subindo juntas, o pg_advisory_lock do alembic/env.py deixa uma migrar por vez.
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
