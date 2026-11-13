#!/usr/bin/env bash
# Deploy na EC2 (ARQ §9): atualiza o código da main, recria os containers e testa a API.
#   cd /opt/proto1 && ./infra/ec2/deploy.sh
# Pré-requisito: .env na raiz do repositório, gerado a partir do Parameter Store (#21).
set -euo pipefail

cd "$(dirname "$0")/../.."
COMPOSE=(docker compose -f docker-compose.prod.yml)
HEALTH_URL="http://localhost/api/health"

if [[ ! -f .env ]]; then
  echo "ERRO: .env não encontrado em $(pwd). Gere-o a partir do Parameter Store antes do deploy." >&2
  exit 1
fi

echo "==> Atualizando o código"
git pull --ff-only

echo "==> Construindo e subindo os containers"
# --wait: só retorna quando os containers estão healthy (falha se algum ficar unhealthy)
if ! "${COMPOSE[@]}" up -d --build --wait --wait-timeout 180; then
  echo "ERRO: containers não ficaram saudáveis. Últimos logs:" >&2
  "${COMPOSE[@]}" ps >&2
  "${COMPOSE[@]}" logs --tail 50 >&2
  exit 1
fi

echo "==> Removendo imagens antigas"
docker image prune -f

echo "==> Verificando $HEALTH_URL"
curl -fsS "$HEALTH_URL"
echo
echo "Deploy concluído."
