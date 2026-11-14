#!/usr/bin/env bash
# Report 02 — Security groups da aplicação (web) e do banco (db).
# Issue #18 · ARQUITETURA.md §8.4 · docs/aws/report_02_security_groups.md
#
# Como rodar (AWS CloudShell, na raiz do repositório):
#   export OWNER=SeuNome
#   bash infra/scripts/02_security_groups.sh
#
# Pré-requisito: proto1-vpc criada (report 01). A VPC é buscada pela tag Name,
# então o script funciona mesmo sem o infra/.state do CloudShell de quem criou a rede.
# Script linear (ARQUITETURA.md §10.5): recria os security groups numa conta limpa.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/00_env.sh
source "${SCRIPT_DIR}/00_env.sh"
# shellcheck source=infra/scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_env

SG_WEB_NAME="${PROJECT}-sg-web"
SG_DB_NAME="${PROJECT}-sg-db"

# ---------------------------------------------------------------------------
# 0. VPC onde os security groups serão criados
# ---------------------------------------------------------------------------
log "0/3 Localizando a ${PROJECT}-vpc"
VPC_ID="$(aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=${PROJECT}-vpc" \
  --query 'Vpcs[0].VpcId' --output text)"
[ "${VPC_ID}" != "None" ] || fail "${PROJECT}-vpc não encontrada. Crie a rede antes (report 01)."
save_output VPC_ID "${VPC_ID}"

# Proteção contra execução dupla: o nome do SG é único por VPC.
for name in "${SG_WEB_NAME}" "${SG_DB_NAME}"; do
  existing="$(aws ec2 describe-security-groups \
    --filters "Name=vpc-id,Values=${VPC_ID}" "Name=group-name,Values=${name}" \
    --query 'SecurityGroups[0].GroupId' --output text)"
  [ "${existing}" = "None" ] || fail "Já existe ${name} (${existing}). Apague-o antes de rodar de novo."
done

printf 'Região: %s · VPC: %s · Owner: %s\n' "${AWS_REGION}" "${VPC_ID}" "${OWNER}"

# ---------------------------------------------------------------------------
# 1. proto1-sg-web (EC2): HTTP e HTTPS abertos para a internet, SEM porta 22.
#    O acesso administrativo é pelo Session Manager (ADR-004), que não usa porta
#    de entrada. 443 atende ao HTTPS exigido pelo cookie Secure (#9/#23).
#    Saída: a regra padrão (tudo liberado) fica, pois a EC2 baixa imagens Docker,
#    clona o repositório e fala com SSM/S3.
# ---------------------------------------------------------------------------
log "1/3 Criando ${SG_WEB_NAME}"
SG_WEB_ID="$(aws ec2 create-security-group \
  --group-name "${SG_WEB_NAME}" \
  --description "proto1 web (EC2): HTTP e HTTPS da internet, sem SSH" \
  --vpc-id "${VPC_ID}" \
  --tag-specifications "$(tag_spec security-group "${SG_WEB_NAME}")" \
  --query 'GroupId' --output text)"
aws ec2 authorize-security-group-ingress \
  --group-id "${SG_WEB_ID}" \
  --ip-permissions '[
    {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80,
     "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTP publico (redireciona para HTTPS)"}]},
    {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,
     "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTPS publico"}]}
  ]' >/dev/null
save_output SG_WEB_ID "${SG_WEB_ID}"

# ---------------------------------------------------------------------------
# 2. proto1-sg-db (RDS): PostgreSQL 5432 SOMENTE de quem está no proto1-sg-web.
#    A origem é o SG, não um IP: qualquer EC2 com o sg-web acessa o banco, mesmo
#    que o IP mude; nada fora dele (inclusive a internet) consegue conectar.
# ---------------------------------------------------------------------------
log "2/3 Criando ${SG_DB_NAME}"
SG_DB_ID="$(aws ec2 create-security-group \
  --group-name "${SG_DB_NAME}" \
  --description "proto1 db (RDS): PostgreSQL somente a partir do proto1-sg-web" \
  --vpc-id "${VPC_ID}" \
  --tag-specifications "$(tag_spec security-group "${SG_DB_NAME}")" \
  --query 'GroupId' --output text)"
aws ec2 authorize-security-group-ingress \
  --group-id "${SG_DB_ID}" \
  --ip-permissions "[
    {\"IpProtocol\": \"tcp\", \"FromPort\": 5432, \"ToPort\": 5432,
     \"UserIdGroupPairs\": [{\"GroupId\": \"${SG_WEB_ID}\", \"Description\": \"PostgreSQL somente da EC2 (${SG_WEB_NAME})\"}]}
  ]" >/dev/null
save_output SG_DB_ID "${SG_DB_ID}"

# ---------------------------------------------------------------------------
# 3. Verificação: regras de entrada dos dois SGs (colar no report 02, seção 7)
# ---------------------------------------------------------------------------
log "3/3 Verificação"
aws ec2 describe-security-groups \
  --group-ids "${SG_WEB_ID}" "${SG_DB_ID}" \
  --query 'SecurityGroups[].{Nome:GroupName,ID:GroupId,Entrada:IpPermissions[].{Porta:FromPort,Origem_CIDR:IpRanges[].CidrIp|join(`,`,@),Origem_SG:UserIdGroupPairs[].GroupId|join(`,`,@)}}' \
  --output json

log "Pronto. IDs salvos em infra/.state/outputs.env (SG_WEB_ID, SG_DB_ID)."
