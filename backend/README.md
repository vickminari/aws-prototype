# Backend — API FastAPI

API do protótipo: cadastro, login com JWT e perfil de usuário. Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2.
Decisões completas em `docs/ARQUITETURA.md` (§5 backend, §6 testes).

## Como rodar

### Com Docker (API + PostgreSQL)

Na raiz do repositório:

```bash
docker compose up --build
```

- API: <http://localhost:8000/api/health>
- Swagger: <http://localhost:8000/api/docs>

O código em `backend/app` é montado no container com `--reload`: salvar um arquivo reinicia a API.
Variáveis opcionais vão em `backend/.env` (copie de `.env.example`); o `DATABASE_URL` do compose já aponta para o serviço `db`.

### Sem Docker (venv)

```bash
cd backend
python -m venv .venv            # ou: uv venv --python 3.12 .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"         # ou: uv pip install -e ".[dev]"
cp .env.example .env            # ajuste se precisar
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

## Estrutura de camadas (MVC + Service)

```
app/
├── main.py              # create_app(): routers, CORS, handlers de erro, docs em /api/docs
├── dependencies.py      # Depends: get_current_user, get_storage (stubs até #9 e #11), get_db (#5)
├── core/                # config.py (variáveis de ambiente), exceptions.py (erros de domínio)
├── schemas/   (VIEW)    # Pydantic: o que entra e o que sai da API
├── controllers/ (CONTROLLER) # routers finos: recebem dependências e chamam UM método de service
├── services/  (SERVICE) # regras de negócio; NÃO importam fastapi
└── models/    (MODEL)   # entidades SQLAlchemy
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
| outra subclasse de `DomainError` | 400 |
| qualquer outra exceção | 500 `INTERNAL_ERROR` (mensagem real só no log) |

Nunca use `HTTPException` em services.

### Usuário autenticado nos testes (antes do login existir)

`get_current_user` é um stub que sempre responde 401. Para testar rotas protegidas:

```python
app.dependency_overrides[get_current_user] = lambda: usuario_de_teste
```

O mesmo vale para `get_storage`.

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
       responses={401: {"model": ErrorRead}},
   )
   def read_me(current_user: User = Depends(get_current_user)):
       return user_service.to_read(current_user)
   ```

5. **Registre o router** em `create_app()` (`app/main.py`):
   `app.include_router(user_controller.router, prefix=API_PREFIX)`.
6. Exceção nova? Crie em `core/exceptions.py` (`code` + `message`) e, se o status não for 400,
   adicione em `DOMAIN_ERROR_STATUS` no `main.py`.
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
