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

Ver [`.env.example`](.env.example) e ARQ §5.8. Em `ENVIRONMENT=prod` a API não sobe se
`JWT_SECRET` tiver menos de 32 caracteres ou for o padrão de desenvolvimento, nem com
`STORAGE_BACKEND=s3` sem `S3_BUCKET`.
