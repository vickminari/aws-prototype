# Protótipo 1 — Aplicação Web na AWS

Protótipo da disciplina **Tópicos em Engenharia de Software (Engenharia de Software aplicada à AWS)** — UFPI.

Aplicação web com cadastro de usuários, login/logout com JWT, dashboard e edição de perfil (com foto armazenada no S3), hospedada na AWS em uma VPC própria com EC2, RDS PostgreSQL e S3.

> 🚧 Em desenvolvimento. Este README é completado na issue #25 (como rodar, deploy, URL de produção).

## Documentação

| Documento | Conteúdo |
|---|---|
| [Como contribuir](CONTRIBUTING.md) | Fluxo de git, commits, TDD, checklist do PR |
| [Issues](https://github.com/vickminari/aws-prototype/issues) | Tarefas, responsáveis e cronograma |
| [Reports da AWS](docs/aws/) | Como cada recurso da AWS foi criado e configurado |

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, JWT (PyJWT), Argon2 (pwdlib) |
| Frontend | React, TypeScript, Vite, React Router, Tailwind CSS |
| Banco | PostgreSQL (Amazon RDS); SQLite em memória nos testes |
| Infraestrutura | AWS: VPC, EC2, Elastic IP, RDS, S3, IAM, Systems Manager — região `us-east-2` |
| Deploy | Docker Compose na EC2 (Nginx + API) |
| Qualidade | pytest, ruff, Vitest, ESLint, GitHub Actions |

## Equipe

| Membro | Responsabilidades | GitHub |
|---|---|---|
| José Victor | Setup do repositório, tech lead backend (esqueleto, banco), conta AWS e equipe, RDS | [@vickminari](https://github.com/vickminari) |
| Gabriel Lopes | Autenticação (segurança, registro, login, logout), VPC e rede | [@G4brielLB](https://github.com/G4brielLB) |
| Pedro Emanuel | Perfil do usuário e imagens, S3, role da EC2, Parameter Store | [@PedroEmanuelMoreiraCarvalho](https://github.com/PedroEmanuelMoreiraCarvalho) |
| Thalys Yago | Frontend base e telas de autenticação, security groups, apresentação | [@ThalysYago](https://github.com/ThalysYago) |
| Jailson Zarur | Frontend do dashboard, CI, EC2 e deploy | [@jailsonzarur](https://github.com/jailsonzarur) |
