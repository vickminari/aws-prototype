# shellcheck shell=bash
# Funções auxiliares compartilhadas pelos scripts de infra/scripts/.
# Uso: carregar depois do 00_env.sh com `source`.

log() {
  printf '\n==> %s\n' "$*"
}

fail() {
  printf 'Erro: %s\n' "$*" >&2
  exit 1
}

# Confere se o script está num ambiente capaz de falar com a AWS
# (CloudShell já vem autenticado) e se o responsável foi informado.
require_env() {
  command -v aws >/dev/null 2>&1 || fail "AWS CLI não encontrado. Execute pelo CloudShell."
  [ -n "${OWNER}" ] || fail "Defina o responsável antes: export OWNER=SeuNome"
  case "${OWNER}" in
    *[[:space:],=\[\]{}]*) fail "OWNER não pode ter espaços nem os caracteres , = [ ] { }" ;;
  esac
  aws sts get-caller-identity --query Arn --output text >/dev/null \
    || fail "Sessão da AWS inválida. Abra o CloudShell novamente."
}

# Monta o --tag-specifications com Name, Project e Owner.
# Ex.: tag_spec vpc proto1-vpc
tag_spec() {
  local resource_type="$1" name="$2"
  printf 'ResourceType=%s,Tags=[{Key=Name,Value=%s},{Key=Project,Value=%s},{Key=Owner,Value=%s}]' \
    "${resource_type}" "${name}" "${PROJECT}" "${OWNER}"
}

# Grava (ou substitui) CHAVE=valor em infra/.state/outputs.env e exporta a variável.
# Ex.: save_output VPC_ID vpc-0123
save_output() {
  local key="$1" value="$2"
  mkdir -p "${STATE_DIR}"
  touch "${OUTPUTS_FILE}"
  local tmp
  tmp="$(mktemp)"
  grep -v "^${key}=" "${OUTPUTS_FILE}" > "${tmp}" || true
  printf '%s=%s\n' "${key}" "${value}" >> "${tmp}"
  mv "${tmp}" "${OUTPUTS_FILE}"
  export "${key}=${value}"
  printf '    %s=%s\n' "${key}" "${value}"
}
