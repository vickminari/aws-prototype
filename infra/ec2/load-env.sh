#!/usr/bin/env bash
# Carrega a configuração de produção do Parameter Store na EC2.
# Issue #21 · ARQUITETURA.md §8.9
#
# Como rodar na EC2:
#   cd /opt/proto1
#   sudo ./infra/ec2/load-env.sh
#
# A autenticação usa exclusivamente a IAM role da instância. Os valores
# descriptografados ficam apenas no arquivo temporário e no .env final.
set -euo pipefail

APP_DIR="/opt/proto1"
PARAM_PATH="/proto1/prod/"
ENV_FILE="${APP_DIR}/.env"

command -v aws >/dev/null 2>&1 || {
  printf 'Erro: AWS CLI não encontrado.\n' >&2
  exit 1
}
[ -d "${APP_DIR}" ] || {
  printf 'Erro: diretório da aplicação não encontrado: %s\n' "${APP_DIR}" >&2
  exit 1
}

umask 077
TMP_DIR="$(mktemp -d)"
PARAMETERS_FILE="${TMP_DIR}/parameters"
ENV_FILE_TMP="$(mktemp "${APP_DIR}/.env.tmp.XXXXXX")"
cleanup() {
  rm -rf "${TMP_DIR}"
  rm -f "${ENV_FILE_TMP}"
}
trap cleanup EXIT

printf '==> Lendo parâmetros de %s\n' "${PARAM_PATH}"
if ! aws ssm get-parameters-by-path \
  --path "${PARAM_PATH}" \
  --recursive \
  --with-decryption \
  --query 'Parameters[].{Name:Name,Value:Value}' \
  --output text > "${PARAMETERS_FILE}"; then
  printf 'Erro: não foi possível ler os parâmetros. Verifique a IAM role da EC2.\n' >&2
  exit 1
fi

[ -s "${PARAMETERS_FILE}" ] || {
  printf 'Erro: nenhum parâmetro encontrado em %s.\n' "${PARAM_PATH}" >&2
  exit 1
}

parameter_count=0
while IFS=$'\t' read -r parameter_name parameter_value; do
  [ -n "${parameter_name}" ] || continue

  case "${parameter_name}" in
    "${PARAM_PATH}"*) ;;
    *)
      printf 'Erro: parâmetro fora do caminho esperado: %s\n' "${parameter_name}" >&2
      exit 1
      ;;
  esac

  env_name="${parameter_name##*/}"
  case "${env_name}" in
    ''|[0-9]*|*[!A-Z0-9_]*)
      printf 'Erro: nome de variável inválido no parâmetro %s.\n' "${parameter_name}" >&2
      exit 1
      ;;
    *)
      ;;
  esac

  printf '%s=%s\n' "${env_name}" "${parameter_value}" >> "${ENV_FILE_TMP}"
  parameter_count=$((parameter_count + 1))
done < "${PARAMETERS_FILE}"

[ "${parameter_count}" -gt 0 ] || {
  printf 'Erro: nenhum parâmetro válido foi carregado.\n' >&2
  exit 1
}

chmod 600 "${ENV_FILE_TMP}"
mv -f "${ENV_FILE_TMP}" "${ENV_FILE}"
chmod 600 "${ENV_FILE}"

printf 'Pronto: %s parâmetros carregados em %s (permissão 600).\n' \
  "${parameter_count}" "${ENV_FILE}"
