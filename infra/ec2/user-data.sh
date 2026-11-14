#!/bin/bash
# User data da EC2 proto1-app (report 06, issue #22 · ARQUITETURA.md §8.5).
# Roda uma única vez, como root, no primeiro boot (cloud-init). Prepara a máquina
# para o deploy da #23: Docker + Compose + Buildx, git, swap e o repositório.
#
# Log: /var/log/proto1-user-data.log · Concluído: /var/lib/proto1/user-data.done
# Acompanhar pelo Session Manager: sudo tail -f /var/log/proto1-user-data.log
set -euxo pipefail
exec > >(tee -a /var/log/proto1-user-data.log) 2>&1

REPO_URL="https://github.com/vickminari/aws-prototype.git"
APP_DIR="/opt/proto1"
PLUGINS_DIR="/usr/local/lib/docker/cli-plugins"

# 1. Pacotes: Docker (repositório do AL2023), git e nc (teste de conexão com o RDS)
dnf install -y docker git nmap-ncat
systemctl enable --now docker
# ec2-user usa docker sem sudo; no Session Manager (ssm-user) use sudo
usermod -aG docker ec2-user

# 2. Plugins do Docker: Compose e Buildx não vêm no pacote do AL2023.
#    O Compose usa o Buildx para o "up --build" do deploy.sh.
mkdir -p "${PLUGINS_DIR}"
curl -fsSL -o "${PLUGINS_DIR}/docker-compose" \
  "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64"
BUILDX_VERSION="$(curl -fsSL https://api.github.com/repos/docker/buildx/releases/latest \
  | grep -m1 '"tag_name"' | cut -d'"' -f4)"
curl -fsSL -o "${PLUGINS_DIR}/docker-buildx" \
  "https://github.com/docker/buildx/releases/download/${BUILDX_VERSION}/buildx-${BUILDX_VERSION}.linux-amd64"
chmod +x "${PLUGINS_DIR}/docker-compose" "${PLUGINS_DIR}/docker-buildx"

# 3. Swap de 2 GB: a t3.micro tem 1 GB de RAM, pouco para o build do frontend (npm ci + vite)
if [ ! -f /swapfile ]; then
  dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
swapon -a

# 4. Código da aplicação (repositório público; deploy pela #23 com infra/ec2/deploy.sh)
if [ ! -d "${APP_DIR}/.git" ]; then
  git clone "${REPO_URL}" "${APP_DIR}"
fi

# Versões instaladas, para conferir no log
docker --version
docker compose version
docker buildx version
git --version

mkdir -p /var/lib/proto1
touch /var/lib/proto1/user-data.done
