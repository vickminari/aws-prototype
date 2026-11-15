# Report 05 — Segredos no Parameter Store

| Campo | Valor |
|---|---|
| Responsável | `Pedro` |
| Issue | #21 |
| Data | `2026-11-15` |
| Região | `us-east-2` |
| Script relacionado | `infra/scripts/05_ssm_parameters.sh` |
| Script da EC2 | `infra/ec2/load-env.sh` |

## 1. Objetivo

Armazenar a configuração de produção da aplicação no AWS Systems Manager
Parameter Store e permitir que a EC2 gere o `.env` local usando somente a
IAM role da instância.

Os segredos não ficam no repositório, em imagens Docker, em access keys ou
impressos no terminal. A `DATABASE_URL` é criada pelo report 04 e apenas
consumida por este fluxo.

## 2. Pré-requisitos

- Report 03 (#19): bucket S3, role `proto1-ec2-role` e policy com
  `ssm:GetParameter` e `ssm:GetParametersByPath`.
- Report 04 (#20): parâmetro `/proto1/prod/DATABASE_URL` criado como
  `SecureString`.
- `openssl` e AWS CLI disponíveis no CloudShell.
- Variáveis `OWNER`, `SUFIXO` e `CSRF_TRUSTED_ORIGINS` definidas.
- Variável `PUBLIC_HOST` definida com o domínio público da aplicação.
- EC2 `proto1-app` criada com a role `proto1-ec2-role` para validar o
  `load-env.sh`.

## 3. Decisões e configurações

| Configuração | Valor | Por quê |
|---|---|---|
| Caminho | `/proto1/prod/` | Separa a configuração de produção das demais |
| Tipo dos parâmetros | `SecureString` | Evita armazenar os valores em texto simples |
| Chave de criptografia | Chave gerenciada pela AWS | Não é necessário administrar uma CMK para o protótipo |
| `JWT_SECRET` | `openssl rand -hex 32` | Segredo aleatório com 64 caracteres hexadecimais |
| `CSRF_SECRET` | `openssl rand -hex 32` | Segredo separado do JWT |
| `CSRF_TRUSTED_ORIGINS` | Origem ou origens HTTPS definidas pelo responsável | Obrigatório para CSRF em produção |
| `STORAGE_BACKEND` | `s3` | Avatares são armazenados no bucket privado |
| `S3_BUCKET` | `proto1-avatars-<sufixo>` | Integração com o bucket do report 03 |
| `AWS_REGION` | `us-east-2` | Região da infraestrutura |
| `LOG_LEVEL` | `INFO` por padrão | Evita logs excessivamente verbosos em produção |
| `PUBLIC_HOST` | Domínio público sem `https://` | Identifica o host público da aplicação |
| `DATABASE_URL` | Criada pela #20 | Evita duplicar ou expor a credencial do RDS |

### Parâmetros criados

| Nome | Tipo | Responsável pelo valor |
|---|---|---|
| `/proto1/prod/JWT_SECRET` | `SecureString` | `05_ssm_parameters.sh` |
| `/proto1/prod/CSRF_SECRET` | `SecureString` | `05_ssm_parameters.sh` |
| `/proto1/prod/CSRF_TRUSTED_ORIGINS` | `SecureString` | `05_ssm_parameters.sh` |
| `/proto1/prod/S3_BUCKET` | `SecureString` | `05_ssm_parameters.sh` |
| `/proto1/prod/STORAGE_BACKEND` | `SecureString` | `05_ssm_parameters.sh` |
| `/proto1/prod/AWS_REGION` | `SecureString` | `05_ssm_parameters.sh` |
| `/proto1/prod/DATABASE_URL` | `SecureString` | Report 04 |

## 4. Passo a passo

### 4.1 Criação no CloudShell

Na raiz do repositório, definir os valores públicos de contexto:

```bash
export AWS_REGION=us-east-2
export OWNER=<nome>
export SUFIXO=<sufixo-do-bucket>
export CSRF_TRUSTED_ORIGINS=https://<dominio-de-producao>
export PUBLIC_HOST=<dominio-de-producao>
export LOG_LEVEL=INFO
export AWS_PAGER=""
```

Executar:

```bash
bash infra/scripts/05_ssm_parameters.sh
```

O script:

1. Confere se `/proto1/prod/DATABASE_URL` já existe.
2. Aborta se algum parâmetro que ele administra já existir.
3. Gera os segredos localmente com `openssl`.
4. Grava os valores como `SecureString`.
5. Lista somente nome, tipo e versão dos parâmetros.

Nenhum comando de verificação deve usar `--with-decryption` no CloudShell.

### 4.2 Carregamento na EC2

Conectar à EC2 pelo Session Manager e executar:

```bash
cd /opt/proto1
sudo ./infra/ec2/load-env.sh
```

O script usa a IAM role da instância para ler `/proto1/prod/` com
`--with-decryption`, gera `/opt/proto1/.env` e aplica permissão `600`.
Os valores não são exibidos no terminal.

## 5. Equivalente via AWS CLI

Listar os parâmetros sem revelar valores:

```bash
aws ssm get-parameters-by-path \
  --path /proto1/prod/ \
  --recursive \
  --query 'Parameters[].{Nome:Name,Tipo:Type,Versao:Version}' \
  --output table
```

Ler os parâmetros descriptografados é permitido somente dentro do
`load-env.sh` na EC2:

```bash
aws ssm get-parameters-by-path \
  --path /proto1/prod/ \
  --recursive \
  --with-decryption
```

Esse comando não deve ser usado em prints, relatórios ou mensagens.

## 6. Recursos criados

| Recurso | Nome | ID/ARN |
|---|---|---|
| Parâmetros SSM | `/proto1/prod/*` | `<preencher versão após execução>` |
| Policy da role | `proto1-ec2-app` | `<preencher ARN da role>` |

## 7. Verificação

### 7.1 Existência e tipo dos parâmetros

```bash
aws ssm get-parameters-by-path \
  --path /proto1/prod/ \
  --recursive \
  --query 'Parameters[].{Nome:Name,Tipo:Type,Versao:Version}' \
  --output table
```

Saída esperada: todos os parâmetros listados com tipo `SecureString`.

Anexar o print como `img/report_05_parameters_metadata.png`, sem clicar em
**Show decrypted value**.

### 7.2 Permissões da IAM role

```bash
aws iam get-role-policy \
  --role-name proto1-ec2-role \
  --policy-name proto1-ec2-app \
  --query 'PolicyDocument.Statement[?Sid==`LerSegredosDaAplicacao`]'
```

Saída esperada: permissões `ssm:GetParameter` e
`ssm:GetParametersByPath` para `parameter/proto1/*`.

### 7.3 `.env` na EC2

Após executar o `load-env.sh`:

```bash
sudo stat -c '%a %n' /opt/proto1/.env
```

Saída esperada:

```text
600 /opt/proto1/.env
```

Verificar somente os nomes das variáveis:

```bash
sudo awk -F= '{print $1}' /opt/proto1/.env
```

Não executar `cat /opt/proto1/.env`, `printenv` ou qualquer comando que revele
os valores.

### 7.4 Validação da aplicação

Com o `.env` carregado:

```bash
cd /opt/proto1
sudo docker compose -f docker-compose.prod.yml config --quiet
sudo docker compose -f docker-compose.prod.yml up -d --wait
curl -fsS http://localhost/api/health
```

Resultado esperado: a configuração é aceita e `/api/health` responde com
status HTTP 200.

## 8. Como conectar / integrar

O `docker-compose.prod.yml` lê o `.env` da raiz do repositório usando
`env_file`. A API recebe `DATABASE_URL`, `JWT_SECRET`, `CSRF_SECRET`,
`CSRF_TRUSTED_ORIGINS`, `STORAGE_BACKEND`, `S3_BUCKET` e `AWS_REGION`.
O `.env` também contém `LOG_LEVEL` e `PUBLIC_HOST`; o carregador inclui
automaticamente qualquer parâmetro criado em `/proto1/prod/`.

A EC2 não precisa de access keys armazenadas no disco: a AWS CLI usa as
credenciais temporárias fornecidas pela role `proto1-ec2-role`.

O `load-env.sh` substitui o `.env` local. Antes de executá-lo em uma EC2 que já
possui configuração, confirmar que os parâmetros do SSM estão completos e
corretos.

## 9. Custos

Parâmetros Standard do Parameter Store não têm custo adicional de
armazenamento. O uso de `SecureString` usa o serviço AWS KMS; a chave
gerenciada pela AWS não exige administração de uma chave própria. As chamadas
e demais recursos permanecem sujeitos aos limites e preços vigentes da AWS.

## 10. Problemas encontrados e soluções

Preencher após a execução:

| Problema | Solução |
|---|---|
| `<descrever problema>` | `<descrever solução>` |

## 11. Como desfazer

Remover somente os parâmetros criados por este report:

```bash
aws ssm delete-parameters \
  --names \
    /proto1/prod/JWT_SECRET \
    /proto1/prod/CSRF_SECRET \
    /proto1/prod/CSRF_TRUSTED_ORIGINS \
    /proto1/prod/S3_BUCKET \
    /proto1/prod/STORAGE_BACKEND \
    /proto1/prod/AWS_REGION \
    /proto1/prod/LOG_LEVEL \
    /proto1/prod/PUBLIC_HOST
```

Não remover `/proto1/prod/DATABASE_URL` neste passo: esse parâmetro pertence
ao report 04 e é necessário para a aplicação.

Depois, remover o `.env` da EC2 somente quando os containers não dependerem
mais dele:

```bash
sudo rm -f /opt/proto1/.env
```

## 12. Referências

- [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [AWS CLI `put-parameter`](https://docs.aws.amazon.com/cli/latest/reference/ssm/put-parameter.html)
- [AWS CLI `get-parameters-by-path`](https://docs.aws.amazon.com/cli/latest/reference/ssm/get-parameters-by-path.html)
- [IAM roles for Amazon EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)
- [AWS Secrets Manager versus Parameter Store](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)

<!-- NUNCA incluir senhas, access keys, JWT_SECRET ou DATABASE_URL completa. -->
