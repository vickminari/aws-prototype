# Backend — API FastAPI

API do protótipo: cadastro, login com JWT e perfil de usuário. Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2.
Decisões completas em `docs/ARQUITETURA.md` (§5 backend, §6 testes).

## Como rodar

### Com Docker (API + PostgreSQL)

Na raiz do repositório:

```bash
docker compose up --build
```

- API: <http://localhost:8000/api/health> (`{"status": "ok", "db": "ok"}`; 503 se o banco não responder)
- Swagger: <http://localhost:8000/api/docs>

O código em `backend/app` é montado no container com `--reload`: salvar um arquivo reinicia a API.
Ao subir, o container roda `alembic upgrade head` (ver [Migrações](#migrações-alembic)).
Variáveis opcionais vão em `backend/.env` (copie de `.env.example`); o `DATABASE_URL` do compose já aponta para o serviço `db`.

### Sem Docker (venv)

```bash
cd backend
python -m venv .venv            # ou: uv venv --python 3.12 .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"         # ou: uv pip install -e ".[dev]"
cp .env.example .env            # ajuste se precisar
docker compose up -d db         # só o PostgreSQL (na raiz do repositório)
alembic upgrade head            # cria/atualiza as tabelas
uvicorn app.main:app --reload
```

## Como testar

```bash
cd backend
pytest                          # todos os testes
pytest --cov                    # com cobertura (meta: 70%, ARQ §6.3)
ruff check .                    # lint
ruff format .                   # formatação (o CI usa ruff format --check)
```

Testes ficam em `tests/unit/` (funções e services) e `tests/integration/` (rotas com `TestClient`).
Nome: `test_<acao>_<cenario>_<resultado>`, ex.: `test_register_with_existing_email_returns_409`.
Os testes não precisam de PostgreSQL: usam SQLite em memória, recriado a cada teste.

### Fixtures (`tests/conftest.py`)

| Fixture | O que entrega |
|---|---|
| `engine` | SQLite em memória (`StaticPool`, chaves estrangeiras ligadas) com as tabelas criadas |
| `db_session` | `Session` do SQLAlchemy; use para criar dados e conferir o que foi gravado |
| `app` | app FastAPI com `get_db` apontando para a `db_session` do teste |
| `client` | `TestClient(app)` |
| `user_factory` | `user_factory(username="maria", password="Outra-123")` cria e salva um usuário; campos omitidos recebem valores válidos e únicos. Senha padrão: `DEFAULT_PASSWORD` |
| `auth_user` | usuário criado e devolvido por `get_current_user` em todas as rotas (sem login) |

```python
def test_read_me_returns_logged_user(client, auth_user):
    response = client.get("/api/users/me")

    assert response.json()["username"] == auth_user.username
```

## Estrutura de camadas (MVC + Service)

```
app/
├── main.py              # create_app(): routers, CORS, handlers de erro, docs em /api/docs
├── dependencies.py      # Depends: get_db, get_current_user e get_storage (stubs até #9 e #11)
├── core/                # config.py (env), database.py (engine, SessionLocal, Base), security.py, exceptions.py
├── schemas/   (VIEW)    # Pydantic: o que entra e o que sai da API
├── controllers/ (CONTROLLER) # routers finos: recebem dependências e chamam UM método de service
├── services/  (SERVICE) # regras de negócio; NÃO importam fastapi
└── models/    (MODEL)   # entidades SQLAlchemy: User, RevokedToken
alembic/                 # env.py e versions/ (migrações); configuração em alembic.ini
```

Sentido das dependências: `controllers → services → models`, `services → core`. Nunca o contrário.

### Erros

Services lançam exceções de `app/core/exceptions.py`; o handler global em `main.py` responde
`{"detail": "mensagem", "code": "CODIGO"}` com o status da tabela `DOMAIN_ERROR_STATUS`:

| Exceção | HTTP |
|---|---|
| `EmailAlreadyExistsError`, `UsernameAlreadyExistsError` | 409 |
| `InvalidCredentialsError`, `InvalidTokenError` | 401 (com `WWW-Authenticate: Bearer`) |
| `WrongPasswordError` | 400 |
| `InvalidImageError` | 422 |
| `NotFoundError` | 404 |
| `DatabaseUnavailableError` (health check) | 503 |
| outra subclasse de `DomainError` | 400 |
| qualquer outra exceção | 500 `INTERNAL_ERROR` (mensagem real só no log) |

Nunca use `HTTPException` em services.

### Usuário autenticado nos testes (antes do login existir)

`get_current_user` é um stub que sempre responde 401. Para testar rotas protegidas, use a
fixture `auth_user` (ver [Fixtures](#fixtures-testsconftestpy)), que faz:

```python
app.dependency_overrides[get_current_user] = lambda: usuario_de_teste
```

Para `get_storage`, faça o override do mesmo jeito.

## Cadastro (issue #8)

`POST /api/auth/register` recebe JSON com `full_name`, `username`, `email`,
`password` e `description` opcional. Retorna **201** com `UserRead`: UUID,
nome, username, email, descrição, `profile_image_url` (inicialmente `null`)
e data de criação. A senha é armazenada somente como hash Argon2id.

Email e username são normalizados em minúsculas antes de verificar unicidade.
Conflitos retornam **409** com `EMAIL_ALREADY_EXISTS` ou
`USERNAME_ALREADY_EXISTS`. Entradas inválidas retornam **422** com erros em
`detail` (`loc`, `msg`, `type`), sem os valores enviados ou contexto interno.
O handler de validação aplica essa remoção às requisições da API.

Exemplos de entrada, saída e conflitos estão em `/api/docs`.
O cadastro não emite JWT nem cookie; login, HttpOnly e CSRF pertencem à #9.

Validações: nome não vazio (até 120 caracteres); username de 3 a 30 caracteres
com letras ASCII, números, ponto ou sublinhado; email válido (até 254 caracteres);
senha com ao menos 8 caracteres, uma letra e um número; descrição opcional
de até 500 caracteres. A senha não é normalizada nem tem espaços removidos.

Exemplo local com dados fictícios:

```bash
curl -i http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"full_name":"Maria Silva","username":"maria.silva","email":"maria@example.com","password":"Senha123"}'
```

Repetir o cadastro retorna 409. A resposta 422 é descrita por
`ValidationErrorRead` no Swagger; seu `detail` é uma lista de erros por campo,
enquanto erros de domínio 409 usam `detail` textual e `code`.

Testes específicos do cadastro:

```bash
pytest tests/unit/test_user_schemas.py tests/unit/test_auth_service.py tests/integration/test_register.py
```

## Banco de dados

- Modelos em `app/models/`, herdando de `Base` (`app/core/database.py`). Use só tipos genéricos
  do SQLAlchemy (os testes rodam em SQLite) e `UTCDateTime` para datas: devolve sempre data com
  fuso UTC, também no SQLite.
- Services recebem a `Session` por parâmetro (`db: Session = Depends(get_db)` no controller) e
  fazem `db.commit()`. Unicidade de email/username é garantida por índice único no banco
  (`IntegrityError`); o service deve checar antes e lançar a exceção de domínio.
- Modelo novo: importe-o em `app/models/__init__.py`, senão o Alembic não o enxerga.

### Migrações (Alembic)

Toda mudança de modelo gera uma migração (ARQ §5.9). Com o PostgreSQL do compose rodando:

```bash
cd backend
alembic revision --autogenerate -m "adiciona coluna x em users"   # gera alembic/versions/<data>_<rev>_*.py
alembic upgrade head            # aplica as pendentes
alembic downgrade -1            # desfaz a última
alembic current                 # mostra a versão do banco
```

Revise o arquivo gerado antes do commit: o autogenerate não detecta tudo (ex.: renomear coluna
vira apagar + criar). O teste `tests/unit/test_migrations.py` aplica todas as migrações num
SQLite e falha se o resultado divergir dos modelos, ou seja, se faltar uma migração.

## Como adicionar um endpoint (passo a passo)

Exemplo: `GET /api/users/me`.

1. **Teste primeiro** em `tests/integration/test_users.py` (commit `test(...)`):
   status esperado, corpo da resposta e erros previstos na issue.
2. **Schema** (View) em `app/schemas/user.py`: `UserRead(BaseModel)` com os campos de saída
   e `json_schema_extra` com um exemplo.
3. **Service** em `app/services/user_service.py`: função com a regra de negócio e docstring
   (estilo Google, com `Raises:`). Erros = exceções de `core/exceptions.py`.
4. **Controller** em `app/controllers/user_controller.py`, com no máximo ~10 linhas:

   ```python
   router = APIRouter(prefix="/users", tags=["users"])


   @router.get(
       "/me",
       response_model=UserRead,
       summary="Retorna o usuário logado",
       responses={401: error_response("Não autenticado", InvalidTokenError)},
   )
   def read_me(current_user: User = Depends(get_current_user)):
       return user_service.to_read(current_user)
   ```

5. **Registre o router** em `create_app()` (`app/main.py`):
   `app.include_router(user_controller.router, prefix=API_PREFIX)`.
6. Exceção nova? Crie em `core/exceptions.py` (`code` + `message`) e, se o status não for 400,
   adicione em `DOMAIN_ERROR_STATUS` no `main.py`. Documente-a na rota com
   `error_response(...)`: assim o Swagger mostra o exemplo certo para cada status.
7. Rode `pytest` e `ruff check .`, commit `feat(...)`; depois `refactor(...)` se houver melhoria.
8. Variável de ambiente nova? Adicione em `core/config.py`, `.env.example` e na ARQ §5.8.

## Variáveis de ambiente

### Segurança (issue #7)

`app/core/security.py` fornece `hash_password`, `verify_password`,
`create_access_token(user_id)` e `decode_access_token(token)`, sem importar FastAPI.
As senhas usam Argon2id com salt aleatório. Os JWTs usam HS256 e exigem `sub`,
`jti`, `iat` e `exp`; assinatura, algoritmo e validade são verificados antes de
retornar os dados. Token inválido gera a exceção de domínio `InvalidTokenError`.

`JWT_EXPIRE_MINUTES` deve ser positivo (padrão atual: 60 minutos).
Em produção, `JWT_SECRET` deve ser gerado aleatoriamente, ter ao menos 32 bytes
de entropia e ser exclusivo desta aplicação. Não reutilize o segredo de desenvolvimento.
O JWT é assinado, não criptografado: não inclua senhas ou outros segredos no payload.

Essas funções independem do transporte: cookie e header são definidos na camada
HTTP. A checagem de usuário ativo e de revogação por `jti` pertence à issue #9;
decodificar um token não basta para autorizar uma requisição.

O transporte escolhido para o navegador é **JWT em cookie HttpOnly**.
O [registro da decisão](../docs/DECISAO_AUTENTICACAO.md) define o contrato futuro
de login/logout, proteção CSRF e os ajustes nas issues de frontend e deploy.
A integração HTTP será implementada na #9; os handlers descritos acima ainda
refletem o esqueleto atual.

### Configuração de cookies e CSRF (issue #9, etapas 2 e 3)

`controllers/auth_cookies.py` centraliza criação e remoção do cookie de acesso:
`access_token` em dev/test e `__Host-access_token` em produção. Ambos usam
`HttpOnly`, `SameSite=Lax`, `Path=/`, sem `Domain`; produção sempre usa `Secure`.
A duração configurada é `JWT_EXPIRE_MINUTES * 60` segundos. Os helpers não
validam o JWT e ainda não estão ligados a endpoints de login/logout nesta etapa.

| Variável | Desenvolvimento/testes | Produção |
|---|---|---|
| `CSRF_SECRET` | Padrão local se omitida | Segredo aleatório exclusivo, mínimo 32 caracteres; não aceita o padrão local |
| `CSRF_TRUSTED_ORIGINS` | Lista explícita HTTP(S), por exemplo `http://localhost:5173` | Lista explícita HTTPS obrigatória, por exemplo `https://app.example.com` |
| `CSRF_EXPIRE_MINUTES` | `60`, configurável e positivo | `60`, configurável e positivo |

`CSRF_SECRET` deve ser diferente de `JWT_SECRET`; gere os dois independentemente
e provisione o novo segredo via Parameter Store na #21. Comprimento mínimo não
substitui geração aleatória. Nunca use os valores fictícios dos testes no deploy.

Origens são separadas por vírgula e incluem esquema, host e porta opcional,
sem credenciais, caminhos, query, fragmento ou curingas. A barra final é removida.
O padrão vazio não autoriza origens. Essa lista é separada de `CORS_ORIGINS`:
mesmo servindo frontend/API na mesma origem, configure a origem pública em CSRF.

`GET /api/auth/csrf` inicia/reutiliza uma pré-sessão assinada e retorna
`{"csrf_token":"..."}` com `Cache-Control: no-store`. Define cookies HttpOnly
`csrf_session` e `csrf_token` (prefixados com `__Host-` e `Secure` em produção).
Envie o token retornado em `X-CSRF-Token`; ele é público e distinto do JWT.

`core/csrf.py` usa HMAC-SHA256, nonce aleatório, vínculo com a sessão e expiração.
O prazo padrão de 60 minutos afeta CSRF/pré-sessão, não renova nem revoga JWTs.
A pré-sessão tem expiração assinada própria: recarregar o endpoint não prolonga
indefinidamente a mesma pré-sessão. Se expirar, obtenha novo token pelo endpoint.

`require_csrf` valida primeiro `Origin` ou, apenas quando ausente, a origem do
`Referer`. Depois exige cookie/header iguais e assinatura válida vinculada à
pré-sessão. Falhas retornam 403 com `CSRF_INVALID`, antes de executar a escrita.

A dependência está pronta e testada em rota isolada. O vínculo HTTP ao `jti`
e a rotação após login entram na etapa 4; a aplicação às rotas existentes
(cadastro e perfil inclusive) e a adaptação de suas fixtures entram na etapa 7.
Portanto, as escritas existentes ainda não estão protegidas por CSRF nesta etapa.
Não há fallback automático para cookie sem `Secure` em produção.

Ver [`.env.example`](.env.example) e ARQ §5.8. Em `ENVIRONMENT=prod` a API não sobe se
`JWT_SECRET` tiver menos de 32 caracteres ou for o padrão de desenvolvimento, nem com
`STORAGE_BACKEND=s3` sem `S3_BUCKET`.
