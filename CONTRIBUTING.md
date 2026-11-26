# Como contribuir

## 1. Configuração inicial (uma vez)

```bash
git config --global user.name "Seu Nome"
git config --global user.email "o-mesmo-email-da-sua-conta-github@exemplo.com"
git clone https://github.com/vickminari/aws-prototype.git
```

> ⚠️ Se o `user.email` for diferente do email da sua conta GitHub, seus commits **não contam** como seus. Confira em GitHub → Settings → Emails.

## 2. Fluxo: uma issue = uma branch = um PR

```bash
git switch dev && git pull                  # parte da dev atualizada
git switch -c feat/8-registro               # branch da issue
git commit -m "feat(auth): implementa registro de usuário"
git push -u origin feat/8-registro
gh pr create --fill                         # ou pelo site do GitHub
```

1. Mova a issue para **Em andamento** no Project ao começar.
2. No PR, escreva `Closes #<n>` e preencha o template.
3. Peça revisão a outro membro e mova a issue para **Em revisão**.
4. Com a aprovação, faça o merge com **Create a merge commit** (único método habilitado).

Nunca faça push direto na `dev` ou na `main`, `push --force` ou squash.

### Branches `dev` e `main` (sprint 2, ADR-031)

- **`dev`** é a branch padrão: todo PR de issue vai para ela, com 1 aprovação.
- **`main`** é o que está em produção. Só recebe PR `dev → main`, quando a equipe decide publicar (fim de marco, feature freeze). Esse PR precisa de **2 aprovações** (com o autor, maioria da equipe: 3 de 5).
- Correção urgente também passa pela `dev`, e depois vai para a `main` num PR `dev → main`.

## 3. Nomes de branch e commits

- Branch: `<tipo>/<n-da-issue>-<descricao>`, ex.: `feat/8-registro`, `infra/17-vpc`, `docs/25-readme`.
- Commit (em português, no imperativo): `tipo(escopo): descrição`, ex.: `fix(perfil): impede email duplicado`.
- Tipos: `feat`, `fix`, `test`, `refactor`, `docs`, `infra`, `ci`, `deploy`, `chore`.
- Trabalhou em dupla? Adicione no final da mensagem: `Co-authored-by: Nome <email-da-conta-github>`.

## 4. TDD (issues com a label `tdd`)

A sequência de commits é avaliada:

1. `test(...)`: escreva os testes e veja falhar.
2. `feat(...)`: implemente o mínimo para passar.
3. `refactor(...)`: melhore o código com os testes verdes.

## 5. Antes de pedir revisão

- [ ] Critérios de aceite da issue cumpridos.
- [ ] Testes passando (código) ou verificação colada no report (AWS).
- [ ] CI verde no PR: jobs **Backend** e **Frontend** (`.github/workflows/ci.yml`).
- [ ] README do módulo atualizado, se mudou como rodar.
- [ ] Nenhum segredo (senha, chave, `JWT_SECRET`, `DATABASE_URL`) em código, docs ou prints.

## 6. Issues da AWS

- Entregue **report + script + prints**, seguindo [`docs/aws/TEMPLATE_report.md`](docs/aws/TEMPLATE_report.md).
- Use o seu próprio login (convite da página Equipe da AWS) e rode os comandos no **CloudShell** (ícone `>_`). Não crie IAM users nem access keys.
- Região **`us-east-2`**. Todo recurso leva as tags `Project` e `Owner=<seu nome>`.
- **Mexa só nos recursos da sua frente.**

### Tags na sprint 2 (ADR-019)

O nome e a tag `Project` dizem em que sprint o recurso foi criado ou mudou ([ARQUITETURA §8.1](docs/ARQUITETURA.md#81-convenções)):

| Situação do recurso | Nome | Tags |
|---|---|---|
| Novo na sprint 2 | prefixo `proto2-` | `Project=proto2`, `Owner=<seu nome>` |
| Modificado na sprint 2 | mantém o nome original | `Project=proto2`, `PreviousProject=proto1`, `Owner=<seu nome>` |
| Intocado | não muda | continua `Project=proto1` |

- "Modificado" é mudar a configuração do próprio recurso (ex.: regra nova no `proto1-sg-db`). Só usar um recurso existente, como as subnets públicas, não conta.
- Os scripts novos fazem `export PROJECT=proto2` antes de `source 00_env.sh`. Para um recurso modificado, use `retag_as_proto2` do `lib.sh` (#63).
- A seção 6 do report lista as tags de cada recurso criado ou modificado.

## 7. Registro do trabalho

Não há diário de bordo separado (ADR-017 em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md)). O histórico de quem fez o quê fica no próprio GitHub, então capriche nele:

- **Commits** pequenos, citando a issue (`(#n)` no título ou `Refs #n` no corpo) e explicando o porquê no corpo quando não for óbvio.
- **PR** com o template preenchido: o que foi feito, como testar e evidências.
- **Report** da AWS com o seu nome e a data no cabeçalho.

O roteiro da apresentação e a tabela de contribuições de cada membro ficam em [`docs/apresentacao/roteiro.md`](docs/apresentacao/roteiro.md) (#27).

## 8. Sprint 2: milestones, labels e reports

O backlog da sprint 2 são as issues #62 a #91, mais a #26 (teardown de proto1 + proto2). Cada issue diz de quais outras depende; comece pelas que não têm dependência aberta. Requisitos em [`docs/REQUISITOS.md`](docs/REQUISITOS.md).

| Milestone | Período | Issues |
|---|---|---|
| M4 — Fundação da sprint 2 | 26–27/11 | #62–#66 |
| M5 — Mídia, processamento e infraestrutura | 27/11–03/12 | #67–#84 |
| M6 — Escala e deploy | 01–05/12 (feature freeze no fim de 05/12) | #85–#87 |
| M7 — Entrega da sprint 2 | 06–09/12 | #88–#91 e #26 |

Labels novas: `worker` (worker e processamento de mídia: fila, ffmpeg) e `performance` (teste de carga e escala).

| Report | Tema | Issue |
|---|---|---|
| 09 | Plano gratuito, créditos e orçamento da sprint 2 | #63 |
| 10 | Bucket de mídia proto2 (CORS e lifecycle) | #79 |
| 11 | Fila SQS de processamento e DLQ | #80 |
| 12 | Roles da aplicação e do worker e parâmetros `/proto2` | #81 |
| 13 | Security groups da sprint 2 e acesso ao RDS | #82 |
| 14 | Application Load Balancer e target group | #83 |
| 15 | CloudFront com HTTPS | #84 |
| 16 | Launch template e Auto Scaling da aplicação | #85 |
| 17 | Auto Scaling dos workers pela fila | #86 |
| 18 | Deploy por instance refresh e cutover da proto1 | #87 |

O report 08 (teardown) continua na #26 e só é executado depois da nota.
