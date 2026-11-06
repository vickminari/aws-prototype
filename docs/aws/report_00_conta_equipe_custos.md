# Report 00 — Conta, Equipe e custos

| Campo | Valor |
|---|---|
| Responsável | José Victor |
| Issue | #2 |
| Data | 2026-11-06 |
| Script relacionado | Não se aplica (tudo feito pelo console, no navegador) |

## 1. Objetivo

Preparar a conta AWS onde o protótipo vai rodar: criar a conta, dar acesso aos 5 membros da equipe com login individual e colocar um controle de custos antes de criar qualquer recurso.

## 2. Pré-requisitos

Nenhum. Este é o primeiro report.

## 3. Decisões e configurações

| Configuração | Valor | Por quê |
|---|---|---|
| Tipo de conta | Nova experiência da AWS, plano gratuito | Créditos iniciais sem cobrança no cartão enquanto houver saldo |
| Projeto | `proto1` | Todos os recursos do protótipo ficam neste projeto |
| Região | `us-east-2` (Ohio) | Atribuída pela AWS conforme o país do cadastro (Brasil); não dá para trocar |
| Acesso da equipe | Convite pela página **Equipe** do AWS Settings | Na nova experiência não existem IAM users para pessoas |
| Login de cada membro | AWS Builder ID próprio, com MFA | Cada um tem sua identidade; nada de senha compartilhada |
| Linha de comando | AWS CloudShell (ícone `>_` no console) | Já vem autenticado; ninguém cria access keys |
| Orçamento | AWS Budget `proto1-budget`, US$ 10/mês, alertas em 50%, 80% e 100% | Avisa por email se algum recurso esquecido estiver gastando créditos |
| Recursos avançados | **Não ativados** | A ativação é irreversível e remove os limites de gasto do plano gratuito |

## 4. Passo a passo

### 4.1 Conta e projeto

1. Conta criada em "Sign up for AWS (new)", no plano gratuito.
2. MFA ativado no AWS Builder ID do proprietário.
   ![MFA ativado](img/report_00_mfa.png)
3. Projeto `proto1` em AWS Settings → **Projetos**.
4. Região conferida em Projeto → Visão geral → Informações adicionais → Região: `us-east-2`.

### 4.2 Equipe

1. AWS Settings → **Equipe** → *Convidar um novo membro* → email do membro + projeto `proto1` (repetido para os 4 membros).
2. Cada membro recebe um email, tem **14 dias** para aceitar, cria o próprio AWS Builder ID e ativa o MFA.
3. Na aba **Membros**, os 5 aparecem com acesso ao `proto1`.
   ![Membros da equipe](img/report_00_membros.png)

### 4.3 Custos

1. Créditos e validade conferidos em AWS Settings → **Faturamento** (seção 9).
2. Budget `proto1-budget` criado: custo mensal de US$ 10, com alertas por email em 50%, 80% e 100%.
   ![Budget](img/report_00_budget.png)

## 5. Como funciona o acesso (por que não há IAM users)

Na nova experiência da AWS, as pessoas não são IAM users: o proprietário convida cada membro pela página Equipe, e cada um entra com o próprio AWS Builder ID.

| Papel | Quem | O que pode fazer |
|---|---|---|
| Proprietário | José Victor | Tudo, inclusive faturamento, créditos e convidar/remover membros |
| Administrador do projeto | Os outros 4 membros | Criar, editar e apagar qualquer recurso do `proto1`; **não** veem faturamento nem convidam pessoas |

A AWS não permite restringir a permissão dos membros. Por isso a equipe combinou:

- cada um mexe **só nos recursos da sua frente**;
- todo recurso criado leva as tags `Project=proto1` e `Owner=<nome de quem criou>`;
- o **CloudTrail → Event history** (ligado por padrão, gratuito, 90 dias) registra quem fez cada ação.

## 6. Recursos criados

| Recurso | Nome | ID |
|---|---|---|
| Projeto | `proto1` | 490711050705 |
| AWS Budget | `proto1-budget` | — |

## 7. Verificação

Cada membro entrou com o próprio login, pode abrir o CloudShell e rodar:

```bash
aws sts get-caller-identity
```

A saída mostra só a identidade (conta e ARN), sem nenhuma chave.

## 8. Como os outros usam isto

- **Entrar na AWS:** aceitar o convite, fazer login com o Builder ID e escolher o projeto `proto1`.
- **Rodar comandos:** pelo CloudShell, sempre na região `us-east-2`.
- **Criar recursos:** prefixo `proto1-` no nome e as tags `Project=proto1` e `Owner=<seu nome>`.

## 9. Custos

No plano gratuito não há cobrança enquanto houver créditos e a conta não for convertida para o plano pago (só o proprietário pode fazer isso). O que mais pode gastar créditos no projeto: EC2, RDS e o IPv4 público do Elastic IP. O cuidado é parar EC2 e RDS quando não estiverem em uso e **nunca** criar NAT Gateway.

## 10. Problemas encontrados e soluções

- A região não pode ser escolhida na nova experiência; ficou `us-east-2` e todos os scripts usam essa região.

## 11. Como desfazer

- Remover membros: AWS Settings → Equipe → Membros → remover.
- Apagar o Budget: Billing → Budgets → `proto1-budget` → Delete.
- Os recursos do projeto são apagados no report 08 (teardown).

## 12. Referências

- AWS Budgets: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- AWS CloudShell: https://docs.aws.amazon.com/cloudshell/latest/userguide/welcome.html
- CloudTrail Event history: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html
