# Report 03 — Bucket S3 e IAM role da EC2

| Campo | Valor |
|---|---|
| Responsável | `Pedro` |
| Issue | #19 |
| Data | `13-11-2026` |
| Região | `us-east-2` |
| Script relacionado | `infra/scripts/03_s3_iam_role.sh` |

## 1. Objetivo

Criar o bucket privado usado para armazenar avatares e a role que será assumida
pela EC2. A aplicação acessa o S3 usando credenciais temporárias da role, sem
access keys no código ou na instância. A leitura no navegador ocorre por URL
pré-assinada com validade limitada.

## 2. Pré-requisitos

- Usuário IAM próprio, com MFA, no grupo `proto1-equipe`.
- Região definida no CloudShell.
- Conta e tags configuradas pela task #2.
- CloudShell autenticado com `aws sts get-caller-identity`.

## 3. Decisões e configurações

| Configuração | Valor | Por quê |
|---|---|---|
| Bucket | `proto1-avatars-grupob31641132` | Nome globalmente único |
| Região | `us-east-2` | Região real do bucket criado |
| Acesso público | Bloqueado totalmente | Avatares não devem ser públicos |
| Object Ownership | Bucket owner enforced | ACLs desnecessárias e desabilitadas |
| Criptografia | SSE-S3 (`AES256`) | Criptografia padrão em repouso |
| Versionamento | Desligado | Não é necessário para avatares |
| Prefixo permitido | `avatars/*` | Limita o escopo dos objetos da aplicação |
| Role | `proto1-ec2-role` | Credenciais temporárias para a EC2 |

## 4. Passo a passo

O recurso foi configurado pelo script no CloudShell:

```bash
AWS_REGION=us-east-2 \
SUFIXO=grupob31641132 \
OWNER=<nome> \
bash infra/scripts/03_s3_iam_role.sh
```

Anexar os prints:

- `img/report_03_bucket_config.png`: bloqueio público, ownership e criptografia.
- `img/report_03_role_permissions.png`: policies da role.
- `img/report_03_cloudtrail.png`: evento registrado pelo usuário IAM.

## 5. Equivalente via AWS CLI

O script configura:

1. Bucket S3 na região selecionada.
2. Block Public Access em todas as quatro opções.
3. Bucket owner enforced.
4. SSE-S3 como criptografia padrão.
5. Tags `Project=proto1` e `Owner=<nome>`.
6. Trust policy permitindo somente `ec2.amazonaws.com`.
7. `AmazonSSMManagedInstanceCore` para o Session Manager.
8. Policy inline `proto1-ec2-app`.
9. Instance profile `proto1-ec2-role`.

A policy inline permite somente:

- `s3:PutObject`, `s3:GetObject` e `s3:DeleteObject` em
  `arn:aws:s3:::proto1-avatars-<sufixo>/avatars/*`;
- `ssm:GetParametersByPath` e `ssm:GetParameter` em
  `arn:aws:ssm:<região>:<account-id>:parameter/proto1/*`.

## 6. Recursos criados

| Recurso | Nome | ID/ARN |
|---|---|---|
| Bucket S3 | `proto1-avatars-grupob31641132` | `arn:aws:s3:::proto1-avatars-grupob31641132` |
| IAM role | `proto1-ec2-role` | `<preencher ARN>` |
| Instance profile | `proto1-ec2-role` | `<preencher ARN>` |
| Policy inline | `proto1-ec2-app` | `<preencher>` |

## 7. Verificação

Objeto de teste:

```bash
printf 'teste s3 proto1' > /tmp/teste.txt
aws s3 cp /tmp/teste.txt \
  s3://proto1-avatars-grupob31641132/avatars/teste.txt
```

URL direta esperada: `AccessDenied`.

```text
https://proto1-avatars-grupob31641132.s3.us-east-2.amazonaws.com/avatars/teste.txt
```

URL pré-assinada:

```bash
aws s3 presign \
  s3://proto1-avatars-grupob31641132/avatars/teste.txt \
  --region us-east-2 \
  --expires-in 3600
```

Resultado esperado: a URL pré-assinada abre o objeto no navegador. Anexar
prints dos dois resultados, sem incluir credenciais ou parâmetros sensíveis.

## 8. Como conectar / integrar

Em produção, a EC2 recebe o instance profile `proto1-ec2-role`. O backend usa
`STORAGE_BACKEND=s3` e `S3_BUCKET=proto1-avatars-grupob31641132`. A aplicação
usa o SDK AWS para obter credenciais temporárias da role e gera URLs
pré-assinadas para leitura.

## 9. Custos

O S3 cobra por armazenamento, requisições e transferência. O objeto de teste e
os avatares do protótipo são pequenos; acompanhar o Free Tier e o Budget da
conta. A role e o instance profile não têm custo direto.

## 10. Problemas encontrados e soluções

Uma primeira URL pré-assinada apontou para a região incorreta e retornou
`PermanentRedirect`. O bucket foi confirmado em `us-east-2` com
`get-bucket-location` e a URL foi regenerada com `--region us-east-2`.

## 11. Como desfazer

Antes de remover o bucket, apagar os objetos:

```bash
aws s3 rm s3://proto1-avatars-grupob31641132 --recursive
aws s3api delete-bucket \
  --bucket proto1-avatars-grupob31641132 \
  --region us-east-2
```

Depois, remover a role pela ordem: instance profile, policy inline, policy
gerenciada e role. O teardown completo da infraestrutura deve ser registrado
na task #26.

## 12. Referências

- [Amazon S3 Block Public Access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)
- [S3 Object Ownership](https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html)
- [IAM roles for Amazon EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)
- [AWS CLI `s3 presign`](https://docs.aws.amazon.com/cli/latest/reference/s3/presign.html)

<!-- NUNCA incluir senhas, access keys, JWT_SECRET ou DATABASE_URL completa. -->
