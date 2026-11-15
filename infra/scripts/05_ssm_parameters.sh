#!/usr/bin/env bash
# Report 05 — Segredos e configuração da aplicação no Parameter Store.
# Issue #21 · ARQUITETURA.md §8.9 · docs/aws/report_05_ssm_parameters.md
#
# Como rodar (AWS CloudShell, na raiz do repositório):
#   export OWNER=SeuNome
#   export SUFIXO=grupob31641132
#   export CSRF_TRUSTED_ORIGINS=https://app.example.com
#   bash infra/scripts/05_ssm_parameters.sh
#
# Pré-requisitos: report 03 (bucket e role da EC2) e report 04 (DATABASE_URL
# criada no RDS). O script não cria nem sobrescreve a DATABASE_URL.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/00_env.sh
source "${SCRIPT_DIR}/00_env.sh"
# shellcheck source=infra/scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_env
command -v openssl >/dev/null 2>&1 || fail "openssl não encontrado."

PARAM_PREFIX="/${PROJECT}/prod"
PARAM_DATABASE_URL="${PARAM_PREFIX}/DATABASE_URL"
BUCKET="${BUCKET:-}"
if [ -z "${BUCKET}" ]; then
  [ -n "${SUFIXO:-}" ] || fail "Defina BUCKET ou SUFIXO para localizar o bucket de avatares."
  BUCKET="proto1-avatars-${SUFIXO}"
fi

CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-}"
[ -n "${CSRF_TRUSTED_ORIGINS}" ] \
  || fail "Defina CSRF_TRUSTED_ORIGINS com uma ou mais origens HTTPS."

IFS=',' read -r -a TRUSTED_ORIGINS <<< "${CSRF_TRUSTED_ORIGINS}"
for origin in "${TRUSTED_ORIGINS[@]}"; do
  case "${origin}" in
    https://?*) ;;
    *) fail "CSRF_TRUSTED_ORIGINS deve conter somente origens HTTPS." ;;
  esac
done

put_parameter() {
  local name="$1" value="$2" description="$3"

  if aws ssm get-parameter --name "${name}" >/dev/null 2>&1; then
    fail "O parâmetro ${name} já existe. Apague-o antes de rodar de novo."
  fi

  aws ssm put-parameter \
    --name "${name}" \
    --description "${description}" \
    --type SecureString \
    --value "${value}" \
    --tags "Key=Project,Value=${PROJECT}" "Key=Owner,Value=${OWNER}" \
    >/dev/null
}

log "1/3 Validando parâmetros já existentes"
if aws ssm get-parameter --name "${PARAM_DATABASE_URL}" >/dev/null 2>&1; then
  printf '    %s já existe e será preservada.\n' "${PARAM_DATABASE_URL}"
else
  fail "${PARAM_DATABASE_URL} não encontrada. Conclua o report 04 antes."
fi

JWT_SECRET="$(openssl rand -hex 32)"
CSRF_SECRET="$(openssl rand -hex 32)"

log "2/3 Criando parâmetros SecureString"
put_parameter "${PARAM_PREFIX}/JWT_SECRET" "${JWT_SECRET}" \
  "proto1: segredo de assinatura dos tokens JWT"
put_parameter "${PARAM_PREFIX}/CSRF_SECRET" "${CSRF_SECRET}" \
  "proto1: segredo de assinatura dos tokens CSRF"
put_parameter "${PARAM_PREFIX}/CSRF_TRUSTED_ORIGINS" "${CSRF_TRUSTED_ORIGINS}" \
  "proto1: origens HTTPS confiáveis para CSRF"
put_parameter "${PARAM_PREFIX}/S3_BUCKET" "${BUCKET}" \
  "proto1: bucket S3 de imagens de perfil"
put_parameter "${PARAM_PREFIX}/STORAGE_BACKEND" "s3" \
  "proto1: backend de armazenamento de imagens"
put_parameter "${PARAM_PREFIX}/AWS_REGION" "${AWS_REGION}" \
  "proto1: região AWS da aplicação"
unset JWT_SECRET CSRF_SECRET

log "3/3 Verificação sem descriptografar valores"
aws ssm get-parameters-by-path \
  --path "${PARAM_PREFIX}/" \
  --recursive \
  --query 'Parameters[].{Nome:Name,Tipo:Type,Versao:Version}' \
  --output table

log "Pronto. Os valores não foram exibidos e a DATABASE_URL foi preservada."
