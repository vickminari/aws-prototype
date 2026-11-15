#!/usr/bin/env bash
# Deploy na EC2 (ARQ §9): atualiza o código da main, recria os containers e testa a API.
#   cd /opt/proto1 && sudo ./infra/ec2/deploy.sh
# Pré-requisito: .env na raiz do repositório, gerado a partir do Parameter Store (#21).
# Com PUBLIC_HOST no .env (ex.: 52-15-241-143.sslip.io), o primeiro deploy também emite o
# certificado HTTPS do Let's Encrypt; os seguintes só o reaproveitam (o certbot renova).
#   CERTBOT_STAGING=1 ./infra/ec2/deploy.sh   → certificado de teste, sem gastar o limite
set -euo pipefail

cd "$(dirname "$0")/../.."
COMPOSE=(docker compose -f docker-compose.prod.yml)
HEALTH_URL="http://localhost/api/health"
CERT_NAME="proto1"

if [[ ! -f .env ]]; then
  echo "ERRO: .env não encontrado em $(pwd). Gere-o a partir do Parameter Store antes do deploy." >&2
  exit 1
fi
PUBLIC_HOST="$(sed -n 's/^PUBLIC_HOST=//p' .env | tail -n 1)"

# Sobe (ou recria) os containers e espera ficarem saudáveis; em falha mostra os logs
compose_up() {
  # --wait: só retorna quando os containers estão healthy (falha se algum ficar unhealthy)
  if ! "${COMPOSE[@]}" up -d --build --wait --wait-timeout 180 "$@"; then
    echo "ERRO: containers não ficaram saudáveis. Últimos logs:" >&2
    "${COMPOSE[@]}" ps >&2
    "${COMPOSE[@]}" logs --tail 50 >&2
    exit 1
  fi
}

has_certificate() {
  "${COMPOSE[@]}" run --rm --no-deps --entrypoint test certbot \
    -f "/etc/letsencrypt/live/${CERT_NAME}/fullchain.pem"
}

echo "==> Atualizando o código"
git pull --ff-only

echo "==> Construindo e subindo os containers"
compose_up

if [[ -n "${PUBLIC_HOST}" ]] && ! has_certificate; then
  echo "==> Emitindo o certificado HTTPS para ${PUBLIC_HOST}"
  # Webroot: o Nginx (ainda só HTTP) serve o desafio do Let's Encrypt na porta 80
  "${COMPOSE[@]}" run --rm --no-deps --entrypoint certbot certbot certonly \
    --webroot -w /var/www/certbot \
    -d "${PUBLIC_HOST}" --cert-name "${CERT_NAME}" \
    --agree-tos --register-unsafely-without-email --non-interactive \
    ${CERTBOT_STAGING:+--staging}
  echo "==> Reiniciando o Nginx com HTTPS"
  "${COMPOSE[@]}" restart web
  compose_up web
fi

echo "==> Removendo imagens antigas"
docker image prune -f

echo "==> Verificando $HEALTH_URL"
curl -fsS "$HEALTH_URL"
echo
if [[ -n "${PUBLIC_HOST}" ]]; then
  # --resolve: testa o certificado e o domínio reais sem sair da EC2
  echo "==> Verificando https://${PUBLIC_HOST}/api/health"
  curl -fsS ${CERTBOT_STAGING:+--insecure} --resolve "${PUBLIC_HOST}:443:127.0.0.1" \
    "https://${PUBLIC_HOST}/api/health"
  echo
fi
echo "Deploy concluído."
