#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
POLICY_DIR="${REPO_ROOT}/infra/policies"

AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(aws configure get region 2>/dev/null || true)}}"
SUFIXO="${SUFIXO:-}"
OWNER="${OWNER:-}"
BUCKET="${BUCKET:-}"
ROLE_NAME="${ROLE_NAME:-proto1-ec2-role}"
INSTANCE_PROFILE_NAME="${INSTANCE_PROFILE_NAME:-${ROLE_NAME}}"
INLINE_POLICY_NAME="${INLINE_POLICY_NAME:-proto1-ec2-app}"

fail() {
  printf 'Erro: %s\n' "$1" >&2
  exit 1
}

command -v aws >/dev/null 2>&1 || fail "AWS CLI não encontrado. Execute pelo CloudShell."
[ -n "${AWS_REGION}" ] || fail "Defina AWS_REGION, por exemplo: AWS_REGION=us-east-2."
[ -n "${SUFIXO}" ] || fail "Defina SUFIXO, por exemplo: SUFIXO=grupob31641132."
[ -n "${OWNER}" ] || fail "Defina OWNER com o nome do responsável."

if [ -z "${BUCKET}" ]; then
  BUCKET="proto1-avatars-${SUFIXO}"
fi

case "${BUCKET}" in
  proto1-avatars-*) ;;
  *) fail "BUCKET deve começar com proto1-avatars-." ;;
esac

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
[ -n "${ACCOUNT_ID}" ] || fail "Não foi possível descobrir o Account ID."

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
RENDERED_POLICY="${TMP_DIR}/ec2-app-policy.json"
sed \
  -e "s/proto1-avatars-SUFIXO/${BUCKET}/g" \
  -e "s/REGION/${AWS_REGION}/g" \
  -e "s/ACCOUNT_ID/${ACCOUNT_ID}/g" \
  "${POLICY_DIR}/ec2-app-policy.json" > "${RENDERED_POLICY}"

printf 'Região: %s\nBucket: %s\nRole: %s\nAccount: %s\n' \
  "${AWS_REGION}" "${BUCKET}" "${ROLE_NAME}" "${ACCOUNT_ID}"

if aws s3api head-bucket --bucket "${BUCKET}" 2>/dev/null; then
  BUCKET_LOCATION="$(aws s3api get-bucket-location \
    --bucket "${BUCKET}" \
    --query LocationConstraint \
    --output text)"
  [ "${BUCKET_LOCATION}" = "None" ] && BUCKET_LOCATION="us-east-1"
  [ "${BUCKET_LOCATION}" = "${AWS_REGION}" ] || fail \
    "O bucket já existe em ${BUCKET_LOCATION}, mas AWS_REGION está em ${AWS_REGION}."
  printf 'Bucket existente encontrado; configurações serão reforçadas.\n'
else
  if [ "${AWS_REGION}" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "${BUCKET}"
  else
    aws s3api create-bucket \
      --bucket "${BUCKET}" \
      --region "${AWS_REGION}" \
      --create-bucket-configuration LocationConstraint="${AWS_REGION}"
  fi
fi

aws s3api put-public-access-block \
  --bucket "${BUCKET}" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws s3api put-bucket-ownership-controls \
  --bucket "${BUCKET}" \
  --ownership-controls Rules="[{ObjectOwnership=BucketOwnerEnforced}]"

aws s3api put-bucket-encryption \
  --bucket "${BUCKET}" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws s3api put-bucket-tagging \
  --bucket "${BUCKET}" \
  --tagging "TagSet=[{Key=Project,Value=proto1},{Key=Owner,Value=${OWNER}}]"

TRUST_POLICY="${POLICY_DIR}/ec2-trust-policy.json"
if aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
  printf 'Role existente encontrada; trust policy será atualizada.\n'
else
  aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document "file://${TRUST_POLICY}" \
    --tags Key=Project,Value=proto1 Key=Owner,Value="${OWNER}"
fi

aws iam update-assume-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-document "file://${TRUST_POLICY}"

aws iam tag-role \
  --role-name "${ROLE_NAME}" \
  --tags Key=Project,Value=proto1 Key=Owner,Value="${OWNER}"

aws iam attach-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "${INLINE_POLICY_NAME}" \
  --policy-document "file://${RENDERED_POLICY}"

if ! aws iam get-instance-profile \
  --instance-profile-name "${INSTANCE_PROFILE_NAME}" >/dev/null 2>&1; then
  aws iam create-instance-profile \
    --instance-profile-name "${INSTANCE_PROFILE_NAME}" \
    --tags Key=Project,Value=proto1 Key=Owner,Value="${OWNER}"
fi

if ! aws iam get-instance-profile \
  --instance-profile-name "${INSTANCE_PROFILE_NAME}" \
  --query "InstanceProfile.Roles[?RoleName=='${ROLE_NAME}'].RoleName" \
  --output text | grep -qx "${ROLE_NAME}"; then
  aws iam add-role-to-instance-profile \
    --instance-profile-name "${INSTANCE_PROFILE_NAME}" \
    --role-name "${ROLE_NAME}"
fi

aws iam tag-instance-profile \
  --instance-profile-name "${INSTANCE_PROFILE_NAME}" \
  --tags Key=Project,Value=proto1 Key=Owner,Value="${OWNER}"

printf '\nVerificação:\n'
aws s3api get-public-access-block --bucket "${BUCKET}"
aws iam list-attached-role-policies --role-name "${ROLE_NAME}"
aws iam get-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "${INLINE_POLICY_NAME}" \
  --query PolicyDocument
aws iam get-instance-profile \
  --instance-profile-name "${INSTANCE_PROFILE_NAME}" \
  --query 'InstanceProfile.Roles[].RoleName'
