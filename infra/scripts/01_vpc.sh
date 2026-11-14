#!/usr/bin/env bash
# Report 01 — VPC, subnets, Internet Gateway, tabelas de rotas e endpoint do S3.
# Issue #17 · ARQUITETURA.md §8.2–8.3 · docs/aws/report_01_vpc_rede.md
#
# Como rodar (AWS CloudShell, na raiz do repositório):
#   export OWNER=SeuNome
#   bash infra/scripts/01_vpc.sh
#
# Script linear (ARQUITETURA.md §10.5): recria a rede numa conta limpa.
# Os IDs criados vão para infra/.state/outputs.env e são usados pelos
# scripts seguintes (security groups, RDS, EC2).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/00_env.sh
source "${SCRIPT_DIR}/00_env.sh"
# shellcheck source=infra/scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_env

# Proteção contra execução dupla: a AWS aceita duas VPCs com o mesmo nome,
# e rodar de novo criaria uma rede duplicada.
EXISTING_VPC="$(aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=${PROJECT}-vpc" \
  --query 'Vpcs[0].VpcId' --output text)"
if [ "${EXISTING_VPC}" != "None" ]; then
  fail "Já existe ${PROJECT}-vpc (${EXISTING_VPC}). Apague-a antes de rodar de novo."
fi

# As duas AZs precisam existir na região (o RDS exige subnets em 2 AZs).
aws ec2 describe-availability-zones --zone-names "${AZ_A}" "${AZ_B}" \
  --query 'AvailabilityZones[].ZoneName' --output text >/dev/null \
  || fail "AZs ${AZ_A}/${AZ_B} não encontradas em ${AWS_REGION}."

printf 'Região: %s · AZs: %s, %s · Owner: %s\n' "${AWS_REGION}" "${AZ_A}" "${AZ_B}" "${OWNER}"

# ---------------------------------------------------------------------------
# 1. VPC 10.0.0.0/16 com DNS habilitado
#    DNS hostnames é necessário para o endpoint do RDS resolver dentro da VPC.
# ---------------------------------------------------------------------------
log "1/6 Criando a VPC ${PROJECT}-vpc (${VPC_CIDR})"
VPC_ID="$(aws ec2 create-vpc \
  --cidr-block "${VPC_CIDR}" \
  --tag-specifications "$(tag_spec vpc "${PROJECT}-vpc")" \
  --query 'Vpc.VpcId' --output text)"
aws ec2 wait vpc-available --vpc-ids "${VPC_ID}"
aws ec2 modify-vpc-attribute --vpc-id "${VPC_ID}" --enable-dns-support '{"Value":true}'
aws ec2 modify-vpc-attribute --vpc-id "${VPC_ID}" --enable-dns-hostnames '{"Value":true}'
save_output VPC_ID "${VPC_ID}"

# ---------------------------------------------------------------------------
# 2. Subnets: 2 públicas e 2 privadas, uma de cada em cada AZ
#    Auto-assign de IP público fica LIGADO nas públicas: a EC2 precisa de
#    internet já no primeiro boot (user data instala Docker e clona o repo),
#    antes de o Elastic IP ser associado. O EIP depois substitui esse IP,
#    então não há custo extra. Nas privadas fica desligado.
# ---------------------------------------------------------------------------
log "2/6 Criando as 4 subnets"
create_subnet() {
  local name="$1" cidr="$2" az="$3" public_ip_flag="$4"
  local id
  id="$(aws ec2 create-subnet \
    --vpc-id "${VPC_ID}" \
    --cidr-block "${cidr}" \
    --availability-zone "${az}" \
    --tag-specifications "$(tag_spec subnet "${name}")" \
    --query 'Subnet.SubnetId' --output text)"
  aws ec2 modify-subnet-attribute --subnet-id "${id}" "${public_ip_flag}"
  printf '%s' "${id}"
}
SUBNET_PUBLIC_A_ID="$(create_subnet "${PROJECT}-public-a" "${SUBNET_PUBLIC_A_CIDR}" "${AZ_A}" --map-public-ip-on-launch)"
SUBNET_PUBLIC_B_ID="$(create_subnet "${PROJECT}-public-b" "${SUBNET_PUBLIC_B_CIDR}" "${AZ_B}" --map-public-ip-on-launch)"
SUBNET_PRIVATE_A_ID="$(create_subnet "${PROJECT}-private-a" "${SUBNET_PRIVATE_A_CIDR}" "${AZ_A}" --no-map-public-ip-on-launch)"
SUBNET_PRIVATE_B_ID="$(create_subnet "${PROJECT}-private-b" "${SUBNET_PRIVATE_B_CIDR}" "${AZ_B}" --no-map-public-ip-on-launch)"
save_output SUBNET_PUBLIC_A_ID "${SUBNET_PUBLIC_A_ID}"
save_output SUBNET_PUBLIC_B_ID "${SUBNET_PUBLIC_B_ID}"
save_output SUBNET_PRIVATE_A_ID "${SUBNET_PRIVATE_A_ID}"
save_output SUBNET_PRIVATE_B_ID "${SUBNET_PRIVATE_B_ID}"

# ---------------------------------------------------------------------------
# 3. Internet Gateway anexado à VPC
# ---------------------------------------------------------------------------
log "3/6 Criando e anexando o ${PROJECT}-igw"
IGW_ID="$(aws ec2 create-internet-gateway \
  --tag-specifications "$(tag_spec internet-gateway "${PROJECT}-igw")" \
  --query 'InternetGateway.InternetGatewayId' --output text)"
aws ec2 attach-internet-gateway --internet-gateway-id "${IGW_ID}" --vpc-id "${VPC_ID}"
save_output IGW_ID "${IGW_ID}"

# ---------------------------------------------------------------------------
# 4. Tabela de rotas pública: 0.0.0.0/0 → IGW. É essa rota que torna
#    uma subnet "pública".
# ---------------------------------------------------------------------------
log "4/6 Criando ${PROJECT}-rt-public e associando às subnets públicas"
RT_PUBLIC_ID="$(aws ec2 create-route-table \
  --vpc-id "${VPC_ID}" \
  --tag-specifications "$(tag_spec route-table "${PROJECT}-rt-public")" \
  --query 'RouteTable.RouteTableId' --output text)"
aws ec2 create-route \
  --route-table-id "${RT_PUBLIC_ID}" \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id "${IGW_ID}" >/dev/null
aws ec2 associate-route-table --route-table-id "${RT_PUBLIC_ID}" --subnet-id "${SUBNET_PUBLIC_A_ID}" >/dev/null
aws ec2 associate-route-table --route-table-id "${RT_PUBLIC_ID}" --subnet-id "${SUBNET_PUBLIC_B_ID}" >/dev/null
save_output RT_PUBLIC_ID "${RT_PUBLIC_ID}"

# ---------------------------------------------------------------------------
# 5. Tabela de rotas privada: só a rota local (sem NAT Gateway).
#    A tabela principal (main) da VPC fica sem associações explícitas e sem
#    rota para a internet; só recebe a tag Name para ser reconhecida no console.
# ---------------------------------------------------------------------------
log "5/6 Criando ${PROJECT}-rt-private e associando às subnets privadas"
RT_PRIVATE_ID="$(aws ec2 create-route-table \
  --vpc-id "${VPC_ID}" \
  --tag-specifications "$(tag_spec route-table "${PROJECT}-rt-private")" \
  --query 'RouteTable.RouteTableId' --output text)"
aws ec2 associate-route-table --route-table-id "${RT_PRIVATE_ID}" --subnet-id "${SUBNET_PRIVATE_A_ID}" >/dev/null
aws ec2 associate-route-table --route-table-id "${RT_PRIVATE_ID}" --subnet-id "${SUBNET_PRIVATE_B_ID}" >/dev/null
save_output RT_PRIVATE_ID "${RT_PRIVATE_ID}"

RT_MAIN_ID="$(aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=${VPC_ID}" "Name=association.main,Values=true" \
  --query 'RouteTables[0].RouteTableId' --output text)"
aws ec2 create-tags --resources "${RT_MAIN_ID}" \
  --tags "Key=Name,Value=${PROJECT}-rt-main" "Key=Project,Value=${PROJECT}" "Key=Owner,Value=${OWNER}"
save_output RT_MAIN_ID "${RT_MAIN_ID}"

# ---------------------------------------------------------------------------
# 6. Gateway Endpoint do S3 nas duas tabelas (gratuito). O tráfego da EC2
#    para o bucket de avatares não passa pela internet.
# ---------------------------------------------------------------------------
log "6/6 Criando o ${PROJECT}-s3-endpoint (Gateway)"
S3_ENDPOINT_ID="$(aws ec2 create-vpc-endpoint \
  --vpc-id "${VPC_ID}" \
  --vpc-endpoint-type Gateway \
  --service-name "com.amazonaws.${AWS_REGION}.s3" \
  --route-table-ids "${RT_PUBLIC_ID}" "${RT_PRIVATE_ID}" \
  --tag-specifications "$(tag_spec vpc-endpoint "${PROJECT}-s3-endpoint")" \
  --query 'VpcEndpoint.VpcEndpointId' --output text)"
save_output S3_ENDPOINT_ID "${S3_ENDPOINT_ID}"

# ---------------------------------------------------------------------------
# Verificação (colar a saída no report 01, seção 7)
# ---------------------------------------------------------------------------
log "Verificação: subnets"
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'Subnets[].{Nome:Tags[?Key==`Name`]|[0].Value,ID:SubnetId,CIDR:CidrBlock,AZ:AvailabilityZone,IpPublicoAuto:MapPublicIpOnLaunch}' \
  --output table

log "Verificação: tabelas de rotas"
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'RouteTables[].{Nome:Tags[?Key==`Name`]|[0].Value,ID:RouteTableId,Subnets:Associations[].SubnetId,Rotas:Routes[].{Destino:DestinationCidrBlock||DestinationPrefixListId,Alvo:GatewayId}}' \
  --output table

log "Verificação completa (JSON) — exigida pela issue #17"
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=${VPC_ID}"

printf '\nPronto. IDs gravados em %s\n' "${OUTPUTS_FILE}"
