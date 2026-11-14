# shellcheck shell=bash
# Variáveis compartilhadas por todos os scripts de infra/scripts/.
# Uso: este arquivo é carregado com `source`, nunca executado diretamente.
#
# Antes de rodar qualquer script no CloudShell, defina quem é o responsável:
#   export OWNER=SeuNome

# Região imposta pela nova experiência da AWS (ADR-008). Se o projeto mostrar
# outra região em AWS Settings, troque aqui e na ARQUITETURA.md §8.1.
export AWS_REGION="${AWS_REGION:-us-east-2}"
export AWS_DEFAULT_REGION="${AWS_REGION}"
export AZ_A="${AZ_A:-${AWS_REGION}a}"
export AZ_B="${AZ_B:-${AWS_REGION}b}"

# Convenções de nomes e tags (ARQUITETURA.md §8.1).
export PROJECT="proto1"
export OWNER="${OWNER:-}"

# Endereçamento da VPC (ARQUITETURA.md §8.2).
export VPC_CIDR="10.0.0.0/16"
export SUBNET_PUBLIC_A_CIDR="10.0.1.0/24"
export SUBNET_PUBLIC_B_CIDR="10.0.2.0/24"
export SUBNET_PRIVATE_A_CIDR="10.0.11.0/24"
export SUBNET_PRIVATE_B_CIDR="10.0.12.0/24"

# IDs gerados pelos scripts ficam aqui (pasta no .gitignore).
SCRIPTS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export SCRIPTS_DIR
export STATE_DIR="${SCRIPTS_DIR}/../.state"
export OUTPUTS_FILE="${STATE_DIR}/outputs.env"

# Carrega os IDs criados por scripts anteriores, se existirem.
if [ -f "${OUTPUTS_FILE}" ]; then
  # shellcheck source=/dev/null
  source "${OUTPUTS_FILE}"
fi
