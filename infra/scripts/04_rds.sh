#!/usr/bin/env bash
# Report 04 — RDS PostgreSQL (proto1-db) nas subnets privadas.
# Issue #20 · ARQUITETURA.md §8.6 e ADR-001 · docs/aws/report_04_rds.md
#
# Como rodar (AWS CloudShell, na raiz do repositório):
#   export OWNER=SeuNome
#   bash infra/scripts/04_rds.sh
#
# Pré-requisitos: proto1-vpc com as subnets privadas (report 01) e proto1-sg-db
# (report 02). Tudo é buscado pelas tags/nomes, então o script funciona mesmo sem
# o infra/.state do CloudShell de quem criou a rede.
#
# A criação do banco leva de 10 a 15 minutos. A senha é gerada aqui, gravada
# direto no Parameter Store (SecureString) e NUNCA é impressa nem salva em arquivo.
# Script linear (ARQUITETURA.md §10.5): recria o banco numa conta limpa.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/00_env.sh
source "${SCRIPT_DIR}/00_env.sh"
# shellcheck source=infra/scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_env

DB_INSTANCE_ID="${PROJECT}-db"
DB_SUBNET_GROUP="${PROJECT}-db-subnets"
DB_NAME="${PROJECT}"
DB_USER="${PROJECT}_admin"
DB_PORT=5432
DB_CLASS="db.t4g.micro"
DB_ENGINE_MAJOR="16"          # mesma versão do postgres:16 do docker-compose de dev
DB_STORAGE_GB=20

# Parâmetros no Parameter Store (ARQUITETURA.md §8.9).
# - A senha do admin fica FORA de /proto1/prod/: o load-env.sh (#21) copia tudo
#   de /proto1/prod/ para o .env, e a aplicação só precisa da DATABASE_URL.
# - A DATABASE_URL usa o driver psycopg 3, igual ao backend/.env.example.
PARAM_DB_PASSWORD="/${PROJECT}/rds/MASTER_PASSWORD"
PARAM_DATABASE_URL="/${PROJECT}/prod/DATABASE_URL"

# Tags no formato da API do RDS e do SSM (Key=...,Value=...).
TAGS_BASE=("Key=Project,Value=${PROJECT}" "Key=Owner,Value=${OWNER}")

# ---------------------------------------------------------------------------
# 0. Recursos dos reports anteriores e proteção contra execução dupla
# ---------------------------------------------------------------------------
log "0/5 Localizando VPC, subnets privadas e ${PROJECT}-sg-db"
VPC_ID="$(aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=${PROJECT}-vpc" \
  --query 'Vpcs[0].VpcId' --output text)"
[ "${VPC_ID}" != "None" ] || fail "${PROJECT}-vpc não encontrada. Crie a rede antes (report 01)."

SUBNET_PRIVATE_A_ID="$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=${VPC_ID}" "Name=tag:Name,Values=${PROJECT}-private-a" \
  --query 'Subnets[0].SubnetId' --output text)"
SUBNET_PRIVATE_B_ID="$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=${VPC_ID}" "Name=tag:Name,Values=${PROJECT}-private-b" \
  --query 'Subnets[0].SubnetId' --output text)"
[ "${SUBNET_PRIVATE_A_ID}" != "None" ] || fail "${PROJECT}-private-a não encontrada (report 01)."
[ "${SUBNET_PRIVATE_B_ID}" != "None" ] || fail "${PROJECT}-private-b não encontrada (report 01)."

# Troca do SG default pelo proto1-sg-db (report 02, seção 8).
SG_DB_ID="$(aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=${VPC_ID}" "Name=group-name,Values=${PROJECT}-sg-db" \
  --query 'SecurityGroups[0].GroupId' --output text)"
[ "${SG_DB_ID}" != "None" ] || fail "${PROJECT}-sg-db não encontrado (report 02)."

# Nada pode existir antes: o script não sobrescreve banco, subnet group nem segredos.
if aws rds describe-db-instances --db-instance-identifier "${DB_INSTANCE_ID}" >/dev/null 2>&1; then
  fail "Já existe a instância ${DB_INSTANCE_ID}. Apague-a antes de rodar de novo (seção 11 do report)."
fi
if aws rds describe-db-subnet-groups --db-subnet-group-name "${DB_SUBNET_GROUP}" >/dev/null 2>&1; then
  fail "Já existe o DB subnet group ${DB_SUBNET_GROUP}. Apague-o antes de rodar de novo."
fi
for param in "${PARAM_DB_PASSWORD}" "${PARAM_DATABASE_URL}"; do
  if aws ssm get-parameter --name "${param}" >/dev/null 2>&1; then
    fail "O parâmetro ${param} já existe no Parameter Store. Apague-o antes de rodar de novo."
  fi
done

save_output VPC_ID "${VPC_ID}"
save_output SUBNET_PRIVATE_A_ID "${SUBNET_PRIVATE_A_ID}"
save_output SUBNET_PRIVATE_B_ID "${SUBNET_PRIVATE_B_ID}"
save_output SG_DB_ID "${SG_DB_ID}"
printf 'Região: %s · VPC: %s · SG: %s · Owner: %s\n' "${AWS_REGION}" "${VPC_ID}" "${SG_DB_ID}" "${OWNER}"

# ---------------------------------------------------------------------------
# 1. DB subnet group com as duas subnets privadas
#    O RDS exige subnets em pelo menos 2 AZs, mesmo sem Multi-AZ. As subnets
#    privadas não têm rota para o Internet Gateway (report 01).
# ---------------------------------------------------------------------------
log "1/5 Criando o DB subnet group ${DB_SUBNET_GROUP}"
aws rds create-db-subnet-group \
  --db-subnet-group-name "${DB_SUBNET_GROUP}" \
  --db-subnet-group-description "proto1: subnets privadas (2 AZs) do RDS" \
  --subnet-ids "${SUBNET_PRIVATE_A_ID}" "${SUBNET_PRIVATE_B_ID}" \
  --tags "Key=Name,Value=${DB_SUBNET_GROUP}" "${TAGS_BASE[@]}" >/dev/null
save_output DB_SUBNET_GROUP "${DB_SUBNET_GROUP}"

# ---------------------------------------------------------------------------
# 2. Senha do admin, gravada direto no Parameter Store
#    Hexadecimal: só [0-9a-f], então não precisa de escape na DATABASE_URL e
#    respeita as restrições do RDS (sem / ' " @ e espaço). Gravada ANTES de criar
#    o banco: se o CloudShell cair durante a espera, a senha não se perde.
# ---------------------------------------------------------------------------
log "2/5 Gerando a senha e gravando em ${PARAM_DB_PASSWORD} (SecureString)"
DB_PASSWORD="$(openssl rand -hex 24)"
aws ssm put-parameter \
  --name "${PARAM_DB_PASSWORD}" \
  --description "proto1: senha do usuario ${DB_USER} do RDS ${DB_INSTANCE_ID}" \
  --type SecureString \
  --value "${DB_PASSWORD}" \
  --tags "${TAGS_BASE[@]}" >/dev/null
printf '    Senha gravada (não é exibida).\n'

# ---------------------------------------------------------------------------
# 3. Instância proto1-db
#    - Versão: a 16.x mais recente que aceita db.t4g.micro com gp3.
#    - Single-AZ em us-east-2a, a mesma AZ da EC2 (sem tráfego entre AZs).
#    - Sem acesso público e só com o proto1-sg-db (5432 somente do proto1-sg-web).
#    - 20 GB gp3 criptografado; sem --max-allocated-storage = autoscaling desligado.
#    - Backup de 1 dia e sem proteção contra exclusão (facilita o teardown).
# ---------------------------------------------------------------------------
log "3/5 Criando a instância ${DB_INSTANCE_ID} (${DB_CLASS})"
DB_ENGINE_VERSION="$(aws rds describe-orderable-db-instance-options \
  --engine postgres --db-instance-class "${DB_CLASS}" \
  --query "OrderableDBInstanceOptions[?starts_with(EngineVersion, '${DB_ENGINE_MAJOR}.') && StorageType=='gp3'].EngineVersion" \
  --output text | tr '\t' '\n' | sort -uV | tail -n 1)"
[ -n "${DB_ENGINE_VERSION}" ] || fail "Nenhuma versão ${DB_ENGINE_MAJOR}.x do PostgreSQL disponível para ${DB_CLASS}."
save_output DB_ENGINE_VERSION "${DB_ENGINE_VERSION}"

aws rds create-db-instance \
  --db-instance-identifier "${DB_INSTANCE_ID}" \
  --db-instance-class "${DB_CLASS}" \
  --engine postgres \
  --engine-version "${DB_ENGINE_VERSION}" \
  --db-name "${DB_NAME}" \
  --master-username "${DB_USER}" \
  --master-user-password "${DB_PASSWORD}" \
  --port "${DB_PORT}" \
  --allocated-storage "${DB_STORAGE_GB}" \
  --storage-type gp3 \
  --storage-encrypted \
  --db-subnet-group-name "${DB_SUBNET_GROUP}" \
  --vpc-security-group-ids "${SG_DB_ID}" \
  --availability-zone "${AZ_A}" \
  --no-multi-az \
  --no-publicly-accessible \
  --backup-retention-period 1 \
  --no-deletion-protection \
  --copy-tags-to-snapshot \
  --tags "Key=Name,Value=${DB_INSTANCE_ID}" "${TAGS_BASE[@]}" >/dev/null
unset DB_PASSWORD
save_output DB_INSTANCE_ID "${DB_INSTANCE_ID}"

log "    Aguardando a instância ficar available (10 a 15 min; não feche o CloudShell)"
aws rds wait db-instance-available --db-instance-identifier "${DB_INSTANCE_ID}"

DB_ENDPOINT="$(aws rds describe-db-instances --db-instance-identifier "${DB_INSTANCE_ID}" \
  --query 'DBInstances[0].Endpoint.Address' --output text)"
save_output DB_ENDPOINT "${DB_ENDPOINT}"

# ---------------------------------------------------------------------------
# 4. DATABASE_URL da aplicação no Parameter Store
#    A senha é lida de volta do SSM, então este bloco também serve para
#    recuperar uma execução interrompida na espera do bloco 3 (seção 10 do report).
# ---------------------------------------------------------------------------
log "4/5 Gravando ${PARAM_DATABASE_URL} (SecureString)"
DB_PASSWORD="$(aws ssm get-parameter --name "${PARAM_DB_PASSWORD}" --with-decryption \
  --query 'Parameter.Value' --output text)"
aws ssm put-parameter \
  --name "${PARAM_DATABASE_URL}" \
  --description "proto1: conexao da API com o RDS ${DB_INSTANCE_ID}" \
  --type SecureString \
  --value "postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@${DB_ENDPOINT}:${DB_PORT}/${DB_NAME}" \
  --tags "${TAGS_BASE[@]}" >/dev/null
unset DB_PASSWORD
printf '    DATABASE_URL gravada (não é exibida).\n'

# ---------------------------------------------------------------------------
# 5. Verificação (colar no report 04, seção 7)
#    MaxStorage vazio (None) = autoscaling desligado.
#    Parâmetros listados SEM --with-decryption: aparecem só nome e tipo.
# ---------------------------------------------------------------------------
log "5/5 Verificação"
aws rds describe-db-instances --db-instance-identifier "${DB_INSTANCE_ID}" \
  --query 'DBInstances[0].{ID:DBInstanceIdentifier,Estado:DBInstanceStatus,Engine:Engine,Versao:EngineVersion,Classe:DBInstanceClass,GB:AllocatedStorage,Disco:StorageType,MaxStorage:MaxAllocatedStorage,Criptografado:StorageEncrypted,MultiAZ:MultiAZ,AZ:AvailabilityZone,PubliclyAccessible:PubliclyAccessible,SG:VpcSecurityGroups[0].VpcSecurityGroupId,SubnetGroup:DBSubnetGroup.DBSubnetGroupName,Subnets:DBSubnetGroup.Subnets[].SubnetIdentifier|join(`,`,@),BackupDias:BackupRetentionPeriod,ProtecaoExclusao:DeletionProtection,Endpoint:Endpoint.Address,Porta:Endpoint.Port}' \
  --output table
aws ssm get-parameters-by-path --path "/${PROJECT}/" --recursive \
  --query 'Parameters[].{Nome:Name,Tipo:Type,Versao:Version}' --output table

log "Pronto. IDs salvos em infra/.state/outputs.env (DB_INSTANCE_ID, DB_ENDPOINT, DB_SUBNET_GROUP)."
