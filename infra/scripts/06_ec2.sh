#!/usr/bin/env bash
# Report 06 — EC2 da aplicação, Elastic IP e acesso pelo Session Manager.
# Issue #22 · ARQUITETURA.md §8.5 · docs/aws/report_06_ec2_elastic_ip.md
#
# Como rodar (AWS CloudShell, na raiz do repositório):
#   export OWNER=SeuNome
#   bash infra/scripts/06_ec2.sh
#
# Pré-requisitos: proto1-vpc e proto1-public-a (report 01), proto1-sg-web (report 02)
# e o instance profile proto1-ec2-role (report 03). Tudo é buscado pelo nome, então o
# script funciona sem o infra/.state de quem criou os outros recursos.
# Script linear (ARQUITETURA.md §10.5): recria a EC2 e o Elastic IP numa conta limpa.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/00_env.sh
source "${SCRIPT_DIR}/00_env.sh"
# shellcheck source=infra/scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_env

INSTANCE_NAME="${PROJECT}-app"
EIP_NAME="${PROJECT}-eip"
INSTANCE_PROFILE_NAME="${PROJECT}-ec2-role"
INSTANCE_TYPE="t3.micro"
ROOT_VOLUME_GB=20
# Parâmetro público da AWS que sempre aponta para a AMI mais recente do Amazon Linux 2023
AMI_PARAMETER="/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
USER_DATA_FILE="${SCRIPT_DIR}/../ec2/user-data.sh"

[ -f "${USER_DATA_FILE}" ] || fail "User data não encontrado em ${USER_DATA_FILE}."

# ---------------------------------------------------------------------------
# 0. Recursos dos reports anteriores e proteção contra execução dupla
# ---------------------------------------------------------------------------
log "0/5 Localizando VPC, subnet, security group e instance profile"
VPC_ID="$(aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=${PROJECT}-vpc" \
  --query 'Vpcs[0].VpcId' --output text)"
[ "${VPC_ID}" != "None" ] || fail "${PROJECT}-vpc não encontrada. Crie a rede antes (report 01)."

SUBNET_PUBLIC_A_ID="$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=${VPC_ID}" "Name=tag:Name,Values=${PROJECT}-public-a" \
  --query 'Subnets[0].SubnetId' --output text)"
[ "${SUBNET_PUBLIC_A_ID}" != "None" ] || fail "${PROJECT}-public-a não encontrada (report 01)."

SG_WEB_ID="$(aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=${VPC_ID}" "Name=group-name,Values=${PROJECT}-sg-web" \
  --query 'SecurityGroups[0].GroupId' --output text)"
[ "${SG_WEB_ID}" != "None" ] || fail "${PROJECT}-sg-web não encontrado (report 02)."

# A role dá à EC2 o Session Manager (AmazonSSMManagedInstanceCore), o S3 e o
# Parameter Store sem nenhuma chave guardada na máquina (report 03).
PROFILE_ROLE="$(aws iam get-instance-profile \
  --instance-profile-name "${INSTANCE_PROFILE_NAME}" \
  --query 'InstanceProfile.Roles[0].RoleName' --output text 2>/dev/null)" \
  || fail "Instance profile ${INSTANCE_PROFILE_NAME} não encontrado. Rode o report 03 antes."
[ "${PROFILE_ROLE}" != "None" ] || fail "O instance profile ${INSTANCE_PROFILE_NAME} não tem role associada (report 03)."
# Sem esta policy o agente não se registra e a EC2 fica sem acesso (não há SSH).
ROLE_POLICIES="$(aws iam list-attached-role-policies --role-name "${PROFILE_ROLE}" \
  --query 'AttachedPolicies[].PolicyName' --output text)"
grep -qw AmazonSSMManagedInstanceCore <<<"${ROLE_POLICIES}" \
  || fail "A role ${PROFILE_ROLE} não tem a policy AmazonSSMManagedInstanceCore. Rode o report 03 antes."

EXISTING_INSTANCE="$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=${INSTANCE_NAME}" \
  "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)"
[ "${EXISTING_INSTANCE}" = "None" ] \
  || fail "Já existe ${INSTANCE_NAME} (${EXISTING_INSTANCE}). Termine-a antes de rodar de novo."

EXISTING_EIP="$(aws ec2 describe-addresses \
  --filters "Name=tag:Name,Values=${EIP_NAME}" \
  --query 'Addresses[0].AllocationId' --output text)"
[ "${EXISTING_EIP}" = "None" ] \
  || fail "Já existe ${EIP_NAME} (${EXISTING_EIP}). Libere-o antes de rodar de novo."

save_output VPC_ID "${VPC_ID}"
save_output SUBNET_PUBLIC_A_ID "${SUBNET_PUBLIC_A_ID}"
save_output SG_WEB_ID "${SG_WEB_ID}"
printf 'Região: %s · Subnet: %s · SG: %s · Role: %s · Owner: %s\n' \
  "${AWS_REGION}" "${SUBNET_PUBLIC_A_ID}" "${SG_WEB_ID}" "${PROFILE_ROLE}" "${OWNER}"

# ---------------------------------------------------------------------------
# 1. AMI do Amazon Linux 2023 (x86_64), resolvida no momento da execução
# ---------------------------------------------------------------------------
log "1/5 Buscando a AMI mais recente do Amazon Linux 2023"
AMI_ID="$(aws ssm get-parameter --name "${AMI_PARAMETER}" \
  --query 'Parameter.Value' --output text)"
save_output AMI_ID "${AMI_ID}"

# ---------------------------------------------------------------------------
# 2. Instância proto1-app
#    - Sem key pair e sem porta 22: o acesso é só pelo Session Manager (ADR-004).
#    - IMDSv2 obrigatório (tokens) com hop limit 2: o limite padrão (1) não deixa a
#      resposta do metadata chegar aos containers Docker, e a API ficaria sem as
#      credenciais da role para acessar o S3.
#    - CPU credits "standard": o padrão da T3 é "unlimited", que cobra à parte se a
#      CPU ficar acima da linha de base por muito tempo.
#    - Disco gp3 de 20 GB criptografado, apagado junto com a instância.
# ---------------------------------------------------------------------------
log "2/5 Criando a instância ${INSTANCE_NAME} (${INSTANCE_TYPE})"
INSTANCE_ID="$(aws ec2 run-instances \
  --image-id "${AMI_ID}" \
  --instance-type "${INSTANCE_TYPE}" \
  --subnet-id "${SUBNET_PUBLIC_A_ID}" \
  --security-group-ids "${SG_WEB_ID}" \
  --iam-instance-profile "Name=${INSTANCE_PROFILE_NAME}" \
  --metadata-options "HttpEndpoint=enabled,HttpTokens=required,HttpPutResponseHopLimit=2" \
  --credit-specification "CpuCredits=standard" \
  --block-device-mappings "DeviceName=/dev/xvda,Ebs={VolumeSize=${ROOT_VOLUME_GB},VolumeType=gp3,Encrypted=true,DeleteOnTermination=true}" \
  --user-data "file://${USER_DATA_FILE}" \
  --tag-specifications \
  "$(tag_spec instance "${INSTANCE_NAME}")" \
  "$(tag_spec volume "${INSTANCE_NAME}-root")" \
  --query 'Instances[0].InstanceId' --output text)"
save_output INSTANCE_ID "${INSTANCE_ID}"

log "    Aguardando a instância ficar running"
aws ec2 wait instance-running --instance-ids "${INSTANCE_ID}"

# ---------------------------------------------------------------------------
# 3. Elastic IP: endereço público fixo, que não muda ao parar e ligar a EC2.
#    Substitui o IP automático da subnet pública (report 01).
# ---------------------------------------------------------------------------
log "3/5 Alocando o ${EIP_NAME} e associando à instância"
EIP_ALLOCATION_ID="$(aws ec2 allocate-address \
  --domain vpc \
  --tag-specifications "$(tag_spec elastic-ip "${EIP_NAME}")" \
  --query 'AllocationId' --output text)"
aws ec2 associate-address \
  --instance-id "${INSTANCE_ID}" \
  --allocation-id "${EIP_ALLOCATION_ID}" >/dev/null
ELASTIC_IP="$(aws ec2 describe-addresses \
  --allocation-ids "${EIP_ALLOCATION_ID}" \
  --query 'Addresses[0].PublicIp' --output text)"
save_output EIP_ALLOCATION_ID "${EIP_ALLOCATION_ID}"
save_output ELASTIC_IP "${ELASTIC_IP}"

# ---------------------------------------------------------------------------
# 4. Session Manager: o agente SSM (já vem no AL2023) se registra usando a role.
#    Leva de 1 a 5 minutos depois do boot.
# ---------------------------------------------------------------------------
log "4/5 Aguardando a instância aparecer no Session Manager (até 10 min)"
SSM_STATUS="None"
for _ in $(seq 1 60); do
  SSM_STATUS="$(aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=${INSTANCE_ID}" \
    --query 'InstanceInformationList[0].PingStatus' --output text)"
  [ "${SSM_STATUS}" = "Online" ] && break
  sleep 10
done
[ "${SSM_STATUS}" = "Online" ] || fail "A instância não ficou Online no Session Manager. Veja a seção 10 do report 06."
printf '    Session Manager: %s\n' "${SSM_STATUS}"

# ---------------------------------------------------------------------------
# 5. Verificação (colar no report 06, seção 7)
# ---------------------------------------------------------------------------
log "5/5 Verificação"
aws ec2 describe-instances --instance-ids "${INSTANCE_ID}" \
  --query 'Reservations[0].Instances[0].{ID:InstanceId,Tipo:InstanceType,AMI:ImageId,Estado:State.Name,Subnet:SubnetId,SG:SecurityGroups[0].GroupName,IpPrivado:PrivateIpAddress,IpPublico:PublicIpAddress,Role:IamInstanceProfile.Arn,IMDSv2:MetadataOptions.HttpTokens,HopLimit:MetadataOptions.HttpPutResponseHopLimit}' \
  --output table

log "Pronto. Elastic IP: ${ELASTIC_IP}"
cat <<EOF
Próximos passos (report 06, seção 7):
  1. Abrir um terminal na EC2, sem SSH:
       aws ssm start-session --target ${INSTANCE_ID}
     (ou no console: EC2 → ${INSTANCE_NAME} → Connect → Session Manager)
  2. Esperar o user data terminar (Docker, Compose, swap e git clone):
       sudo cloud-init status --wait && ls /var/lib/proto1/user-data.done
  3. Rodar a verificação da issue #22:
       docker compose version; free -h; aws sts get-caller-identity
EOF
