# Report 06 — EC2, Elastic IP e Session Manager

| Campo | Valor |
|---|---|
| Responsável | Jailson Zarur |
| Issue | #22 |
| Data | `<preencher: AAAA-MM-DD da execução>` |
| Projeto (AWS Settings) | `proto-tes` |
| Região | `us-east-2` (Ohio) |
| Como foi criado | Script `infra/scripts/06_ec2.sh` no CloudShell (seção 4) |
| Script relacionado | `infra/scripts/06_ec2.sh` e `infra/ec2/user-data.sh` (usam `00_env.sh` e `lib.sh` do report 01) |

## 1. Objetivo

Criar a máquina onde a aplicação roda: a EC2 **`proto1-app`**, na subnet pública, com um endereço fixo na internet (**Elastic IP `proto1-eip`**). No primeiro boot, o *user data* deixa a máquina pronta para o deploy da #23: Docker, Docker Compose, git, swap e o repositório clonado em `/opt/proto1`.

A instância não tem porta 22 nem chave SSH. O acesso administrativo é pelo **Session Manager**, que abre um terminal no navegador ou no CloudShell usando a role da EC2 (report 03) e o login de cada membro.

## 2. Pré-requisitos

- Report 01 (#17): `proto1-vpc` (`vpc-0e3944afb658f063f`) e a subnet `proto1-public-a` (`subnet-020460f423e4aa900`), com rota para o Internet Gateway.
- Report 02 (#18): `proto1-sg-web` (`sg-09b1318a081965dfc`), com 80 e 443 abertos e sem 22.
- Report 03 (#19): instance profile `proto1-ec2-role`, com `AmazonSSMManagedInstanceCore` (Session Manager) e a policy `proto1-ec2-app` (S3 e Parameter Store). O script aborta se ele não existir.
- CloudShell (ícone `>_`), na raiz do repositório clonado.

O RDS (#20) **não** é pré-requisito para criar a EC2; só para o teste `nc -zv` da seção 7.

## 3. Decisões e configurações

| Configuração | Valor | Por quê |
|---|---|---|
| AMI | Amazon Linux 2023 (x86_64), a mais recente | Mantida pela AWS, já traz o agente do SSM e o AWS CLI. O script lê o ID no parâmetro público `/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64` |
| Tipo | `t3.micro` (2 vCPU, 1 GB RAM) | Suficiente para Nginx + API de um protótipo; elegível ao plano gratuito |
| CPU credits | `standard` | O padrão da família T3 é `unlimited`, que cobra à parte se a CPU ficar muito tempo acima da linha de base. Com `standard`, no pior caso a máquina fica lenta, mas não gera custo extra |
| Subnet | `proto1-public-a` (us-east-2a) | Precisa receber tráfego da internet. O RDS fica nas privadas |
| Security group | `proto1-sg-web` | 80 e 443 da internet, sem SSH (report 02) |
| IAM | instance profile `proto1-ec2-role` | Credenciais temporárias para Session Manager, S3 e Parameter Store; nenhuma chave fica na máquina |
| Key pair | **nenhum** | Sem SSH: acesso só pelo Session Manager (ADR-004) |
| Disco | 20 GB gp3, **criptografado**, apagado com a instância | Espaço para imagens Docker e logs; gp3 é mais barato que gp2 |
| Metadata (IMDS) | **IMDSv2 obrigatório**, hop limit **2** | O IMDSv2 exige token e protege contra SSRF. O hop limit 2 é necessário porque a API roda **dentro de um container**: a resposta do metadata precisa atravessar dois "pulos" de rede. Com o padrão (1), a API não recebe as credenciais da role e o upload para o S3 falha |
| Endereço público | Elastic IP `proto1-eip` | IP fixo: não muda ao parar e ligar a EC2. É o endereço do deploy e do HTTPS da #23 |
| User data | `infra/ec2/user-data.sh` | Prepara a máquina no primeiro boot, sem acesso manual (abaixo) |

### User data

O `infra/ec2/user-data.sh` roda uma vez, como root, no primeiro boot:

1. Instala `docker`, `git` e `nmap-ncat` (o `nc` do teste com o RDS) e habilita o Docker no boot.
2. Instala os plugins **Docker Compose** e **Buildx**, que não vêm no pacote do Amazon Linux 2023.
3. Cria **2 GB de swap**: com 1 GB de RAM, o build do frontend (`npm ci` + Vite) poderia ser encerrado por falta de memória.
4. Clona o repositório (público) em **`/opt/proto1`**.

Log em `/var/log/proto1-user-data.log`; ao terminar, cria `/var/lib/proto1/user-data.done`.

### Acesso sem SSH (Session Manager)

| | SSH tradicional | Session Manager |
|---|---|---|
| Porta de entrada | 22 aberta para a internet | **Nenhuma**: o agente na EC2 abre a conexão de saída para a AWS |
| Credencial | Arquivo `.pem` compartilhado entre a equipe | Login individual de cada membro, com MFA |
| Auditoria | Nenhuma por padrão | Cada sessão aparece no CloudTrail com quem abriu |

O agente usa a permissão `AmazonSSMManagedInstanceCore` da role (report 03) e precisa de saída para a internet, que a EC2 tem pela subnet pública.

## 4. Passo a passo

Executado no CloudShell, na raiz do repositório:

```bash
git clone https://github.com/vickminari/aws-prototype.git && cd aws-prototype
export OWNER=Jailson
bash infra/scripts/06_ec2.sh
```

Saída do script:

```text
<preencher: colar a saída do script>
```

No console, em **EC2 → Instances** e **EC2 → Elastic IPs**:

<!-- Prints a anexar em docs/aws/img/:
![Instância proto1-app em execução](img/report_06_instancia.png)
![Elastic IP proto1-eip associado à instância](img/report_06_eip.png)
![Terminal aberto pelo Session Manager](img/report_06_session_manager.png)
-->

## 5. Equivalente via AWS CLI

O script cria a EC2 e o Elastic IP numa conta limpa (com os recursos dos reports 01, 02 e 03) e aborta se `proto1-app` ou `proto1-eip` já existirem.

| Bloco | O que faz |
|---|---|
| 0/5 | Localiza `proto1-vpc`, `proto1-public-a` e `proto1-sg-web` pelo nome; confere se o instance profile `proto1-ec2-role` existe e tem role; aborta se a instância ou o EIP já existirem |
| 1/5 | `ssm get-parameter` da AMI mais recente do Amazon Linux 2023 |
| 2/5 | `run-instances` com as configurações da seção 3 e o `user-data.sh`; espera o estado `running` |
| 3/5 | `allocate-address` (com a tag `proto1-eip`) e `associate-address` |
| 4/5 | Espera a instância ficar `Online` no Session Manager (até 10 min) |
| 5/5 | `describe-instances` com tipo, AMI, rede, IPs, role e metadata |

Os IDs ficam em `infra/.state/outputs.env` (`INSTANCE_ID`, `EIP_ALLOCATION_ID`, `ELASTIC_IP`, `AMI_ID`), fora do Git.

## 6. Recursos criados

| Recurso | Nome | ID |
|---|---|---|
| Instância EC2 | `proto1-app` | `<preencher: i-...>` |
| Volume raiz (EBS) | `proto1-app-root` | `<preencher: vol-...>` |
| Elastic IP | `proto1-eip` | `<preencher: eipalloc-...>` / `<preencher: IP>` |
| AMI usada | Amazon Linux 2023 | `<preencher: ami-...>` |

## 7. Verificação

**Instância** (saída do bloco 5/5 do script):

```text
<preencher: tabela do describe-instances>
```

Conferir: `IMDSv2 = required`, `HopLimit = 2`, `SG = proto1-sg-web`, `IpPublico` igual ao Elastic IP.

**Dentro da EC2**, pelo Session Manager (`aws ssm start-session --target <INSTANCE_ID>` no CloudShell, ou **Connect → Session Manager** no console):

```bash
sudo cloud-init status --wait          # espera o user data terminar
ls /var/lib/proto1/user-data.done      # existe = user data concluído
docker compose version
free -h                                # deve mostrar Swap: 2.0Gi
aws sts get-caller-identity            # Arn com assumed-role/proto1-ec2-role
ls /opt/proto1                         # repositório clonado
```

```text
<preencher: saída dos comandos acima>
```

**Credenciais da role dentro de um container** (comprova o hop limit 2, necessário para a API acessar o S3):

```bash
sudo docker run --rm public.ecr.aws/aws-cli/aws-cli sts get-caller-identity
```

```text
<preencher: deve mostrar o mesmo Arn assumed-role/proto1-ec2-role>
```

### Teste de conexão com o RDS (pendente: depende da #20)

```bash
nc -zv <endpoint-do-rds> 5432          # da EC2: deve conectar (succeeded)
```

O mesmo comando no CloudShell, fora da VPC, deve falhar por timeout (report 02, seção 7).

## 8. Como conectar / integrar

- **Terminal na EC2:** `aws ssm start-session --target <INSTANCE_ID>` no CloudShell, ou **EC2 → proto1-app → Connect → Session Manager**. A sessão abre como `ssm-user`; use `sudo` para o Docker.
- **Deploy (#23):** com o `.env` de produção na raiz do repositório (gerado a partir do Parameter Store, #21), rodar `cd /opt/proto1 && sudo ./infra/ec2/deploy.sh`.
- **Aplicação:** `http://<ELASTIC_IP>` após o deploy. O HTTPS (cookie `Secure`, `docs/DECISAO_AUTENTICACAO.md`) é configurado na #23 sobre este mesmo IP.
- **RDS (#20):** a EC2 está no `proto1-sg-web`, a única origem aceita pelo `proto1-sg-db` na porta 5432.

## 9. Custos

Valores sob demanda em `us-east-2`, consumidos dos créditos do plano gratuito:

| Item | Preço | Por mês (24/7) |
|---|---|---|
| EC2 `t3.micro` | ~US$ 0,0104/hora | ~US$ 7,60 |
| EBS gp3 20 GB | ~US$ 0,08/GB-mês | ~US$ 1,60 |
| IPv4 público (Elastic IP) | US$ 0,005/hora | ~US$ 3,60 |

Desde 2024 a AWS cobra **todo IPv4 público**, associado ou não. O Elastic IP **continua sendo cobrado com a EC2 parada**; para zerar o custo é preciso liberá-lo (seção 11).

**Como parar quando não estiver em uso** (o disco e o Elastic IP continuam cobrando, a hora da EC2 não):

```bash
aws ec2 stop-instances --instance-ids <INSTANCE_ID>    # parar
aws ec2 start-instances --instance-ids <INSTANCE_ID>   # ligar de novo (o Elastic IP é mantido)
```

Os containers sobem sozinhos ao ligar (`restart: unless-stopped` no `docker-compose.prod.yml`).

## 10. Problemas encontrados e soluções

| Problema | Solução |
|---|---|
| 1ª execução: o script parou em 4/5 (instância não ficou `Online` no Session Manager). `aws iam list-attached-role-policies --role-name proto1-ec2-role` veio **vazio**: a role existia e estava associada à EC2, mas sem nenhuma policy | O report 03 não tinha sido concluído. Anexar as policies rodando o `03_s3_iam_role.sh`. O `06_ec2.sh` passou a conferir a `AmazonSSMManagedInstanceCore` no bloco 0/5, **antes** de criar qualquer recurso |
| 1ª execução: o user data parou no meio (`curl: (23) Failure writing output` no `get-console-output`): Docker e Compose instalados, mas sem Buildx, swap e clone | A versão do Buildx era lida com `curl \| grep -m1`; o `grep` fecha o pipe ao achar a 1ª linha, o `curl` falha e o `pipefail` aborta o script. A versão passou a ser lida do redirecionamento de `/releases/latest`, sem pipe |
| A instância não fica `Online` no Session Manager | Conferir se o `proto1-ec2-role` tem a policy `AmazonSSMManagedInstanceCore` (report 03) e se a instância recebeu IP público (sem ele não há saída para a internet, pois não existe NAT) |
| `permission denied` ao usar o Docker pelo Session Manager | A sessão abre como `ssm-user`, que não está no grupo `docker`. Usar `sudo docker ...` |
| User data falhou | Ver `sudo cat /var/log/proto1-user-data.log`. O user data só roda no primeiro boot; para repetir, corrigir e rodar o script como root: `sudo bash /opt/proto1/infra/ec2/user-data.sh` |

## 11. Como desfazer

Ordem (o report 08 consolida o teardown de todo o projeto):

1. Desassociar e **liberar** o Elastic IP (sem isso ele continua sendo cobrado).
2. Terminar a instância. O volume raiz é apagado junto (`DeleteOnTermination=true`).

```bash
aws ec2 disassociate-address --association-id "$(aws ec2 describe-addresses \
  --allocation-ids <EIP_ALLOCATION_ID> --query 'Addresses[0].AssociationId' --output text)"
aws ec2 release-address --allocation-id <EIP_ALLOCATION_ID>
aws ec2 terminate-instances --instance-ids <INSTANCE_ID>
```

## 12. Referências

- [Amazon Linux 2023 — AMIs no Parameter Store](https://docs.aws.amazon.com/linux/al2023/ug/ec2.html)
- [User data na inicialização da EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html)
- [IMDSv2 e hop limit](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-IMDS-existing-instances.html)
- [Instâncias T3: modos standard e unlimited](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-unlimited-mode.html)
- [Elastic IP addresses](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html)
- [Cobrança de IPv4 público](https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights/)
- [AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
