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
git switch main && git pull                 # parte da main atualizada
git switch -c feat/8-registro               # branch da issue
git commit -m "feat(auth): implementa registro de usuário"
git push -u origin feat/8-registro
gh pr create --fill                         # ou pelo site do GitHub
```

1. Mova a issue para **Em andamento** no Project ao começar.
2. No PR, escreva `Closes #<n>` e preencha o template.
3. Peça revisão a outro membro e mova a issue para **Em revisão**.
4. Com a aprovação, faça o merge com **Create a merge commit** (único método habilitado).

Nunca faça push direto na `main`, `push --force` ou squash.

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
- [ ] README do módulo atualizado, se mudou como rodar.
- [ ] Nenhum segredo (senha, chave, `JWT_SECRET`, `DATABASE_URL`) em código, docs ou prints.

## 6. Issues da AWS

- Entregue **report + script + prints**, seguindo [`docs/aws/TEMPLATE_report.md`](docs/aws/TEMPLATE_report.md).
- Use o seu próprio login (convite da página Equipe da AWS) e rode os comandos no **CloudShell** (ícone `>_`). Não crie IAM users nem access keys.
- Região **`us-east-2`**. Prefixo `proto1-` e tags `Project=proto1` e `Owner=<seu nome>` em todo recurso.
- **Mexa só nos recursos da sua frente.**

## 7. Diário de bordo

Todo dia, comente na issue **Diário de bordo da equipe** (fixada):

```markdown
**D3 — Seu Nome**
- Fiz: <o que concluiu, com links de PR/issue>
- Próximo: <o que faz amanhã>
- Bloqueios / aprendizados: <opcional>
```
