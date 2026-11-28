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

# Marca um recurso da sprint 1 que foi modificado na sprint 2 (ADR-019):
# aplica Project=proto2, PreviousProject=proto1 e Owner=<quem modificou>.
# O Name não muda. Recursos de EC2/VPC recebem o ID; os demais, o ARN.
# Ex.: retag_as_proto2 sg-035eab28e4158d2d8
#      retag_as_proto2 arn:aws:rds:us-east-2:123456789012:db:proto1-db
retag_as_proto2() {
  local resource="$1"
  [ -n "${resource}" ] || fail "retag_as_proto2: informe o ID ou o ARN do recurso"
  [ -n "${OWNER}" ] || fail "Defina o responsável antes: export OWNER=SeuNome"

  case "${resource}" in
    arn:*)
      local failed
      failed="$(aws resourcegroupstaggingapi tag-resources \
        --resource-arn-list "${resource}" \
        --tags "Project=proto2,PreviousProject=proto1,Owner=${OWNER}" \
        --query 'length(FailedResourcesMap)' --output text)" \
        || fail "Não foi possível marcar ${resource}"
      # A API responde com sucesso mesmo quando o recurso falha; confere o mapa.
      [ "${failed}" = "0" ] || fail "A AWS recusou as tags em ${resource}"
      ;;
    *)
      aws ec2 create-tags --resources "${resource}" \
        --tags Key=Project,Value=proto2 Key=PreviousProject,Value=proto1 "Key=Owner,Value=${OWNER}" \
        || fail "Não foi possível marcar ${resource}"
      ;;
  esac
  log "${resource} marcado como Project=proto2 (PreviousProject=proto1)"
}
