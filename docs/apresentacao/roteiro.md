# Roteiro da apresentação: 1º protótipo

| Campo | Valor |
|---|---|
| Issue | #27 |
| Duração | 30 min |
| Formato | Aplicação em produção, console da AWS, GitHub e código |
| Endereço | <https://52-15-241-143.sslip.io> |

A especificação pede três coisas na apresentação: o **protótipo funcionando**, os **passos executados** e a **colaboração de cada membro**. O roteiro cobre as três com o que já existe no repositório: a aplicação em produção, os recursos no console e os reports da AWS.

A apresentação é fluida e todos participam de todos os blocos. Os nomes indicados em cada parte são um norte de quem conduz, seguindo quem fez aquela parte (seção 7).

## Sumário

1. [Preparação](#1-preparação)
2. [Visão geral](#2-visão-geral)
3. [Bloco 1: Abertura](#3-bloco-1-abertura)
4. [Bloco 2: Demo ao vivo](#4-bloco-2-demo-ao-vivo)
5. [Bloco 3: AWS no console](#5-bloco-3-aws-no-console)
6. [Bloco 4: Código](#6-bloco-4-código)
7. [Bloco 5: Contribuições e lições](#7-bloco-5-contribuições-e-lições)
8. [Opcionais e plano B](#8-opcionais-e-plano-b)
9. [Resumo por membro](#9-resumo-por-membro)

## 1. Preparação

### Antes de começar

- [ ] Não executar o teardown (#26) antes da apresentação.
- [ ] **Ligar o RDS e a EC2** no CloudShell (o RDS leva de 5 a 10 min para ficar disponível; reports 04 e 06):

  ```bash
  aws rds start-db-instance --db-instance-identifier proto1-db
  aws ec2 start-instances --instance-ids "$(aws ec2 describe-instances --filters Name=tag:Name,Values=proto1-app --query 'Reservations[0].Instances[0].InstanceId' --output text)"
  ```

- [ ] Conferir <https://52-15-241-143.sslip.io/api/health> → `{"status":"ok","db":"ok"}`.
- [ ] Ter à mão duas imagens: `foto.jpg` (até 2 MB) e `foto-grande.jpg` (mais de 2 MB).
- [ ] Uma máquina só projeta tudo.
- [ ] Abas abertas, nesta ordem:
  1. GitHub: [README](../../README.md) e [ARQUITETURA §1.1](../ARQUITETURA.md#11-requisitos-da-especificação--como-foram-atendidos).
  2. Aplicação: `https://52-15-241-143.sslip.io` numa **janela anônima** (sem sessão antiga).
  3. Console AWS (`us-east-2`): AWS Settings → Equipe, VPC, EC2, RDS, S3, IAM, Systems Manager.
  4. Editor com os arquivos da seção 6 abertos e terminal no repositório.
  5. GitHub: *Actions*, *Insights → Contributors* e a lista de issues fechadas.

### O que nunca aparece na tela

- Valores do Parameter Store (não clicar em **Mostrar** / *Show decrypted value*).
- O arquivo `/opt/proto1/.env`, `printenv` e `docker inspect` na EC2 (exibem os segredos, report 07 §8).
- Senha da conta de demonstração digitada em campo visível (os campos de senha já mascaram).

## 2. Visão geral

| # | Bloco | O que trata |
|---|---|---|
| 1 | Abertura | O que a especificação pedia e como foi atendido, a arquitetura em um diagrama e como a equipe trabalhou |
| 2 | Demo ao vivo | Todo o item A da especificação funcionando em produção: cadastro, login, dashboard, perfil, foto, senha e logout |
| 3 | AWS no console | Todo o item B: os recursos reais, na ordem de uma requisição, cada um com o seu report |
| 4 | Código | Trechos curtos: camadas MVC + Service, autenticação, TDD, storage no S3, frontend e CI |
| 5 | Contribuições e lições | O que cada membro fez (issues e PRs) e o que aprendeu |

A demo vem antes da AWS de propósito: primeiro se vê que funciona, depois onde roda. A foto enviada na demo reaparece no bucket S3 no bloco 3.

## 3. Bloco 1: Abertura

**Fala: José Victor.** Mostrar só três coisas:

| Mostrar | Dizer |
|---|---|
| [ARQUITETURA §1.1](../ARQUITETURA.md#11-requisitos-da-especificação--como-foram-atendidos) (tabela requisito → solução) | O que a especificação pedia (A: login/logout, registro, dashboard, perfil; B: VPC, EC2, SG, rotas, IP público; C: repositório documentado) e que tudo foi entregue, mais RDS, S3, Parameter Store, HTTPS e CI |
| Diagrama do [README](../../README.md#arquitetura) | Caminho de uma requisição: navegador → Elastic IP → EC2 (Nginx + React, FastAPI) na subnet pública → RDS na subnet privada; foto no S3 privado; segredos no Parameter Store |
| Lista de issues/PRs no GitHub (sem abrir nenhum) | Como a equipe trabalhou: uma issue = uma branch = um PR revisado; TDD no backend; CI em todo PR; cada recurso AWS com report + script. A pergunta "o que cada um fez" é respondida no fim |

## 4. Bloco 2: Demo ao vivo

Cobre todo o item A da especificação. Usar a janela anônima. Quem construiu a tela narra; quem opera é a mesma máquina.

### Parte 1: Acesso e cadastro (Thalys)

| # | Ação | O que deve aparecer | Requisito |
|---|---|---|---|
| 1 | Abrir `https://52-15-241-143.sslip.io` e clicar no cadeado | Conexão segura (Let's Encrypt) e redirecionamento para `/login` | A1, segurança |
| 2 | Digitar `/dashboard` na barra de endereço | Volta para `/login`: rota protegida sem sessão | A1 autorização |
| 3 | **Criar conta** com o email de uma conta que já existe em produção (por exemplo, a da validação da #24) | "Email já cadastrado" embaixo do campo email (409 da API) | A1 registro |
| 4 | Digitar uma senha fraca e ir completando | Regras de força marcando ao vivo | A1 |
| 5 | Preencher nome completo, username `demo`, email novo, senha válida e descrição; enviar | Conta criada e entrada direta no dashboard | A1 registro + login |

### Parte 2: Dashboard (Jailson)

| # | Ação | O que deve aparecer | Requisito |
|---|---|---|---|
| 6 | Mostrar a página inicial | Card com iniciais, nome, username, descrição e **"Membro desde"** (data de criação) | A2 dashboard, data de criação |
| 7 | Passar pelo menu lateral | Início, Meu perfil, Alterar senha, Sair | A2 menu |
| 8 | (Opcional) Alternar tema claro/escuro | Tema muda e é lembrado | Extra |

### Parte 3: Perfil e foto (Thalys)

| # | Ação | O que deve aparecer | Requisito |
|---|---|---|---|
| 9 | **Meu perfil** → editar nome e descrição → salvar | Toast de sucesso e dados atualizados | A2 editar informações |
| 10 | Escolher `foto-grande.jpg` | "A imagem deve ter no máximo 2 MB." e envio bloqueado | A2 imagem |
| 11 | Escolher `foto.jpg` → enviar | Pré-visualização, depois a foto no perfil e no avatar do topo (vem do S3) | A2 imagem do perfil |

### Parte 4: Senha, logout e novo login (Jailson)

| # | Ação | O que deve aparecer | Requisito |
|---|---|---|---|
| 12 | **Alterar senha** com a senha atual errada | "Senha atual incorreta" | A2 alterar senha |
| 13 | Senha atual certa + nova senha válida | Sucesso | A2 alterar senha |
| 14 | **Sair** | Volta ao login | A1 logout |
| 15 | Botão **Voltar** do navegador ou `/dashboard` | Continua no login: o token foi revogado no servidor | A1 logout |
| 16 | Login com a **senha antiga** | "Usuário ou senha inválidos" (mensagem genérica) | A1 |
| 17 | Login pelo **email** com a senha nova | Dashboard com a foto: login aceita username ou email | A1 |

Deixar a sessão aberta: o Pedro mostra a foto no S3 no bloco 3.

## 5. Bloco 3: AWS no console

Segue o caminho de uma requisição, de fora para dentro. Cada um mostra o próprio recurso no console e cita o report (não abrir o report, a não ser que perguntem). Todos os recursos têm prefixo `proto1-` e tag `Owner`.

| Ordem | Quem | Onde clicar | O que apontar | Report |
|---|---|---|---|---|
| 1 | José Victor | AWS Settings → **Equipe** → Membros; Billing → **Budgets** | 5 membros, cada um com o próprio login (sem IAM users nem access keys); `proto1-budget` (US$ 10/mês, alertas em 50%, 80% e 100%); região `us-east-2` fixa (ADR-008) | [00](../aws/report_00_conta_equipe_custos.md) |
| 2 | Gabriel | VPC → Your VPCs → `proto1-vpc` → aba **Resource map**; depois Route tables | 2 subnets públicas e 2 privadas em 2 AZs; `proto1-rt-public` com `0.0.0.0/0 → proto1-igw`; `proto1-rt-private` só com `local` + endpoint do S3 (o banco não tem saída para a internet). **Especificação B: VPC e tabela de rotas** | [01](../aws/report_01_vpc_rede.md) |
| 3 | Thalys | EC2 → Security Groups → `proto1-sg-web` e `proto1-sg-db` → Inbound rules | Web: 80 e 443 da internet, **sem porta 22**; DB: 5432 **só a partir do `proto1-sg-web`** (referência a SG, não IP). **Especificação B: grupos de segurança** | [02](../aws/report_02_security_groups.md) |
| 4 | Jailson | EC2 → Instances → `proto1-app` (detalhes); Elastic IPs → `proto1-eip`; **Conectar → Session Manager** | `t3.micro` na subnet pública A, role `proto1-ec2-role`, Elastic IP `52.15.241.143` associado. **Especificação B: EC2 e IP público**. No terminal: `sudo docker ps --format 'table {{.Names}}\t{{.Status}}'` (web, api e certbot). Explicar o `deploy.sh` pelo diagrama da [ARQUITETURA §2.3](../ARQUITETURA.md#23-fluxo-do-deploy): `git pull` → `.env` do Parameter Store → `docker compose up --build` → teste do health. Não rodar o deploy (leva minutos) | [06](../aws/report_06_ec2_elastic_ip.md), [07](../aws/report_07_deploy.md) |
| 5 | José Victor | RDS → Databases → `proto1-db` → Connectivity & security | PostgreSQL 16, **Publicly accessible: No**, subnet group das subnets privadas, SG `proto1-sg-db`. Prova de que a EC2 fala com ele: aba da aplicação em `/api/health` → `"db":"ok"` | [04](../aws/report_04_rds.md) |
| 6 | Pedro | S3 → `proto1-avatars-…` → Permissions e Objects; IAM → Roles → `proto1-ec2-role`; Systems Manager → Parameter Store | Bucket com *Block all public access*; em `avatars/` (ordenar por data) a **foto enviada na demo**; abrir a URL do objeto → *AccessDenied* (a aplicação usa URL pré-assinada de 1 h). Role: policy inline `proto1-ec2-app` com S3 só em `avatars/*` e leitura de `/proto1/*` (privilégio mínimo, sem chaves na EC2). Parameter Store: nomes `/proto1/prod/*` do tipo `SecureString`, **sem mostrar valores** | [03](../aws/report_03_s3_iam_role.md), [05](../aws/report_05_ssm_parameters.md) |

Frase de ligação (Jailson → José Victor): "A API nessa EC2 fala com o banco, que está numa subnet privada."

## 6. Bloco 4: Código

Mostrar arquivos curtos e já abertos no editor, sem rolar muito. Os números de linha valem para a `main` de 2026-11-16.

### Gabriel: camadas e autenticação

1. **MVC + Service pelo cadastro** (seguindo uma requisição):
   - Controller fino: [`auth_controller.py:147-148`](../../backend/app/controllers/auth_controller.py#L147-L148) (duas linhas; o resto do decorator é documentação do Swagger).
   - Regra de negócio: [`auth_service.py:114-144`](../../backend/app/services/auth_service.py#L114-L144) (normaliza, checa unicidade, faz o hash Argon2id), sem importar `fastapi`.
   - View = schema Pydantic: `UserCreate` em [`schemas/user.py`](../../backend/app/schemas/user.py) (regras da senha).
2. **Logout de verdade**: [`auth_service.py:81-104`](../../backend/app/services/auth_service.py#L81-L104) grava o `jti` em `revoked_tokens`; [`dependencies.py:56-70`](../../backend/app/dependencies.py#L56-L70) recusa o token revogado. Opcional: DevTools → Application → Cookies → `__Host-access_token` com **HttpOnly** e **Secure**.
3. **TDD** no terminal, mostrando `test` antes de `feat` e `refactor` no histórico:

   ```bash
   git log --oneline --no-merges --reverse --grep="(#8)"
   ```

### Pedro: foto de perfil e S3

1. Mesmo padrão na foto: controller [`user_controller.py:63-70`](../../backend/app/controllers/user_controller.py#L63-L70) → service [`user_service.py:62-78`](../../backend/app/services/user_service.py#L62-L78) (chave `avatars/{user_id}/{uuid}`, apaga a foto anterior).
2. Abstração de storage: interface em [`storage/base.py`](../../backend/app/services/storage/base.py) e [`storage/s3.py`](../../backend/app/services/storage/s3.py) com `boto3` sem nenhuma chave (credenciais da role) e URL pré-assinada. Em dev e nos testes, o mesmo código usa o disco local.
3. Ligação com a AWS: [`infra/ec2/load-env.sh`](../../infra/ec2/load-env.sh) gera o `.env` a partir do Parameter Store.

### Thalys: frontend

1. Rota protegida em 10 linhas: [`ProtectedRoute.tsx`](../../frontend/src/routes/ProtectedRoute.tsx).
2. Sessão segura no cliente: [`services/api.ts:53-80`](../../frontend/src/services/api.ts#L53-L80): header CSRF em toda escrita, nova tentativa em `403 CSRF_INVALID` e volta ao login em `401`. O JWT fica num cookie `HttpOnly`, que o JavaScript não lê.
3. Chamadas HTTP só em `src/services/`; páginas usam React Hook Form + Zod ([`schemas/`](../../frontend/src/schemas/)).

### Jailson: CI

1. Aba **Actions** do GitHub: execução verde na `main` com os jobs **Backend** (ruff, pytest com cobertura mínima de 70%) e **Frontend** (ESLint, Prettier, Vitest, build), definidos em [`ci.yml`](../../.github/workflows/ci.yml).
2. Números: backend com 400 testes e 96% de cobertura; frontend com 30 testes em 10 arquivos. Nenhum PR entrou com CI vermelho.

## 7. Bloco 5: Contribuições e lições

Na tela: GitHub → **Insights → Contributors** e, depois, a tabela abaixo. Cada membro fala o que fez (coluna "Frentes") e uma lição. José Victor fecha falando do processo.

### Tabela de contribuições

Dados da `main` antes do merge desta issue.

| Membro | Frentes | Issues | PRs |
|---|---|---|---|
| José Victor (@vickminari) | Repositório e governança, esqueleto do backend, banco e migrações, conta AWS e equipe, RDS, README e diagramas, apresentação | #1, #2, #3, #5, #20, #25, #27 | #29, #31, #48, #50, #60 |
| Gabriel Lopes (@G4brielLB) | Hash e JWT, registro, login, logout com revogação, cookie `HttpOnly` e CSRF, VPC e rotas, teardown | #7, #8, #9, #17, #26 | #30, #32, #41, #45 |
| Pedro Emanuel (@PedroEmanuelMoreiraCarvalho) | Perfil, troca de senha, upload de imagem e storage, S3 e role da EC2, Parameter Store, validação em produção | #10, #11, #19, #21, #24 | #33, #39, #40, #55, #56, #59 |
| Thalys Yago (@ThalysYago) | Esqueleto do frontend, camada de API e sessão, login, cadastro e perfil, security groups, modo escuro e transições | #4, #12, #13, #15, #18, #37, #53 | #34, #36, #38, #46, #47, #52, #54 |
| Jailson Zarur (@jailsonzarur) | CI, dashboard e logout, alteração de senha, EC2 e Elastic IP, deploy em produção e HTTPS | #6, #14, #16, #22, #23 | #35, #42, #43, #44, #49, #51, #57 |

Para regenerar:

```bash
gh issue list --state all --assignee <login>
gh pr list --state merged --author <login>
```

## 8. Opcionais e plano B

**Podem ficar de fora se faltar tempo:** passo 8 (tema) e o cookie no DevTools; passo 16 (senha antiga); `load-env.sh` na fala do Pedro; Budgets na fala do José Victor; TDD vira só uma frase em vez do `git log`.

| Problema | Plano B |
|---|---|
| `/api/health` com `503` | RDS ainda ligando; conferir o status no RDS e seguir com o bloco 1 enquanto isso |
| Aplicação fora do ar ou internet ruim | Prints do [checklist de validação](../checklist_validacao.md) e do [report 07 §7](../aws/report_07_deploy.md#7-verificação) |
| Console AWS sem acesso | Prints de cada report em `docs/aws/img/` (resource map, SGs, instância, Elastic IP, RDS) |
| Session Manager não conecta | Print `report_06_session_manager.png` e o diagrama do deploy na ARQUITETURA §2.3 |

## 9. Resumo por membro

Quem conduz cada parte, na ordem da apresentação. Os demais complementam.

| Membro | Bloco 1 | Bloco 2 (demo) | Bloco 3 (AWS) | Bloco 4 (código) | Bloco 5 |
|---|---|---|---|---|---|
| José Victor | Abertura | | Equipe e Budgets, RDS | | Fala + fechamento |
| Gabriel | | | VPC e rotas | Camadas, auth, TDD | Fala |
| Pedro | | | S3, role, Parameter Store | Foto e storage | Fala |
| Thalys | | Cadastro, perfil | Security groups | Frontend | Fala |
| Jailson | | Dashboard, senha e logout | EC2, Elastic IP, deploy | CI | Fala |
