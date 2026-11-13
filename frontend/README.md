# Frontend

SPA em React 19 + TypeScript + Vite, com React Router v7, Tailwind CSS v4, ESLint + Prettier e Vitest + React Testing Library. Decisões completas em `docs/ARQUITETURA.md` (§7 frontend).

## Pré-requisitos

- **Node 22** (`node -v`). É a mesma versão usada no CI.
- Para usar a API localmente: Docker, para subir o backend (ver [backend/README.md](../backend/README.md)).

## Como rodar

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Requisições para `/api` são encaminhadas pelo Vite para `http://localhost:8000`, sem CORS nem URL diferente por ambiente (ARQ §7.5). Para ter a API respondendo, suba o backend na raiz do repositório:

```bash
docker compose up --build   # API em http://localhost:8000/api/docs
```

Nenhuma variável de ambiente é necessária; veja [`.env.example`](.env.example).

## Como rodar os testes

```bash
npm run test -- --run   # roda os testes uma vez (é o que o CI usa)
npm run test            # modo watch: roda de novo ao salvar
```

Os testes ficam ao lado do arquivo testado (`Componente.test.tsx`) e rodam em jsdom. O [`src/test/setup.ts`](src/test/setup.ts) carrega os matchers do `jest-dom` (`toBeInTheDocument` etc.). O escopo mínimo de testes está na ARQ §7.7.

## Comandos úteis

| Comando                | O que faz                                                |
| ---------------------- | -------------------------------------------------------- |
| `npm run dev`          | Servidor de desenvolvimento com proxy `/api`             |
| `npm run lint`         | ESLint (o CI bloqueia erros)                             |
| `npm run format`       | Formata o código com Prettier                            |
| `npm run format:check` | Só verifica a formatação                                 |
| `npm run build`        | Checagem de tipos (`tsc`) + build de produção em `dist/` |
| `npm run preview`      | Serve o `dist/` localmente                               |

### Imagem de produção

```bash
docker build -t proto1-web ./frontend
```

O [`Dockerfile`](Dockerfile) é multi-stage: `node` gera o `dist/` e `nginx:alpine` serve os arquivos. O [`nginx.conf`](nginx.conf) devolve o `index.html` para qualquer rota da SPA, encaminha `/api/` para `http://api:8000` (serviço `api` do Docker Compose), limita o upload a 3 MB, comprime JS/CSS/JSON com gzip e envia os headers de segurança. Fora do Compose o nome `api` não existe, então o container sozinho não sobe; ele roda com o `docker-compose.prod.yml` (#23).

## Estrutura de pastas

```
src/
├── main.tsx              Ponto de entrada: monta o <App/>
├── App.tsx               Providers globais + router
├── index.css             Entrada do Tailwind
├── routes/               router.tsx (rotas), ProtectedRoute e PublicOnlyRoute
├── pages/                Uma página por rota (hoje placeholders)
├── layouts/              DashboardLayout: sidebar + topbar + <Outlet/> (#14)
├── components/ui/        Componentes visuais base: Button, Input, Card, Spinner, Avatar
├── components/forms/     Componentes de formulário, ex.: FormField (#13)
├── contexts/             AuthContext.tsx (AuthProvider: mantém a sessão)
├── hooks/                useAuth (hook, tipo e contexto da sessão)
├── services/             Chamadas HTTP: api.ts (axios + CSRF + 401), authService, userService
├── schemas/              Schemas Zod dos formulários (#13)
├── types/                Tipos espelhando os schemas da API (user.ts)
├── utils/                Funções puras, ex.: formatDate (#14)
└── test/                 Configuração e utilitários dos testes (setup.ts, auth.ts)
```

### Rotas (ARQ §7.3)

| Rota                  | Acesso       | Página                   | Issue que implementa |
| --------------------- | ------------ | ------------------------ | -------------------- |
| `/login`              | só deslogado | `LoginPage`              | #13                  |
| `/register`           | só deslogado | `RegisterPage`           | #13                  |
| `/dashboard`          | protegida    | `DashboardHomePage`      | #14                  |
| `/dashboard/profile`  | protegida    | `ProfilePage`            | #15                  |
| `/dashboard/password` | protegida    | `ChangePasswordPage`     | #16                  |
| `/`                   | —            | `/dashboard` ou `/login` | #12                  |
| `*`                   | —            | `NotFoundPage`           | #14                  |

Rotas "só deslogado" ficam dentro de `PublicOnlyRoute` (com sessão → `/dashboard`); rotas protegidas, dentro de `ProtectedRoute` (sem sessão → `/login`). Nova página protegida? Adicione-a nos `children` do `ProtectedRoute` em [`router.tsx`](src/routes/router.tsx).

## Autenticação

O JWT fica em um **cookie HttpOnly** definido pelo backend. O frontend não lê, não guarda e não envia o token: o navegador cuida disso. O login responde `{"detail": "..."}` (tipo `LoginResponse`) em vez de `Token`. Essa decisão substitui o `localStorage` e o header Bearer da ARQ §7.4; ver [docs/DECISAO_AUTENTICACAO.md](../docs/DECISAO_AUTENTICACAO.md).

### Como a sessão funciona

1. Ao abrir a aplicação, o `AuthProvider` chama `GET /api/users/me`. Enquanto isso, `isLoading` é `true` e as rotas mostram um spinner. 200 → usuário logado; 401 → visitante.
2. Toda escrita (`POST`, `PUT`, `PATCH`, `DELETE`) leva o header `X-CSRF-Token`. O [`api.ts`](src/services/api.ts) busca o token em `GET /api/auth/csrf` e o guarda **só em memória**. Em 403 `CSRF_INVALID`, ele renova o token e repete a requisição uma vez.
3. Após o login e o logout, o token CSRF é descartado e o próximo é buscado automaticamente.
4. Um 401 em qualquer chamada limpa o usuário. As rotas protegidas levam para `/login` com o toast "Sessão expirada". Exceções: o próprio login (senha errada) e a checagem inicial.

### Como usar nas páginas

Use os services e o `useAuth`. Nunca chame `axios`/`fetch` direto nos componentes.

```tsx
import { useAuth } from '../hooks/useAuth.ts'
import * as userService from '../services/userService.ts'

const { user, isLoading, login, logout, refreshUser } = useAuth()

await login('maria', 'Senha123') // erro 401 → mostrar "usuário ou senha inválidos"
await userService.updateMe({ description: 'Nova descrição' })
await refreshUser() // recarrega o user após salvar
await logout() // só limpa a sessão se o servidor confirmar; erro de rede é relançado
```

| Service                   | Funções                                                               |
| ------------------------- | --------------------------------------------------------------------- |
| `services/authService.ts` | `register`, `login`, `logout`                                         |
| `services/userService.ts` | `getMe`, `updateMe`, `changePassword`, `uploadAvatar`, `deleteAvatar` |

Toasts: `import { toast } from 'sonner'` e `toast.success('...')` / `toast.error('...')`. O `<Toaster />` já está no `App.tsx`.

Em testes, simule a sessão com o `AuthContext` e o `makeAuthValue` de [`src/test/auth.ts`](src/test/auth.ts) (exemplo em [`ProtectedRoute.test.tsx`](src/routes/ProtectedRoute.test.tsx)).

## Boas práticas (ARQ §7.6), checklist antes do PR

- [ ] Componentes pequenos e de função única; páginas compõem componentes.
- [ ] Nenhuma chamada HTTP dentro de componentes de UI: sempre via `services/`.
- [ ] Estados de **carregando**, **erro** e **vazio** tratados em toda tela que busca dados.
- [ ] Botões de submit desabilitados durante o envio (evita duplo clique). Use `<Button isLoading>`.
- [ ] Acessibilidade básica: `label` associado a cada input (o `Input` já faz isso), `alt` na imagem, foco visível, navegação por teclado.
- [ ] Layout responsivo (sidebar vira menu no celular).
- [ ] Preview da imagem antes do upload; validação de tipo e tamanho (2 MB) também no cliente.
- [ ] Sem segredos no frontend; variáveis `VITE_*` são públicas.
- [ ] `npm run lint`, `npm run test -- --run` e `npm run build` passando.
