# Decisão — JWT em cookie HttpOnly

Status: decisão aceita; integração HTTP a implementar nas issues abaixo.

Responsável pela decisão: Gabriel Lopes, com autonomia autorizada por José
Victor. Este documento é o registro versionado da mudança e contém os contratos
necessários para implementá-la, sem depender dos documentos de planejamento
mantidos apenas como referência local.

Substitui a orientação anterior de Bearer com armazenamento em `localStorage`
para o navegador e antecipa cookie HttpOnly e HTTPS para esta entrega.
Preserva JWT HS256, identidade UUID, revogação por `jti`, validade configurável
e ausência de refresh token.

## Limite da entrega #7

A #7 entrega `hash_password`, `verify_password`, `create_access_token(user_id: UUID)`
e `decode_access_token`, com testes unitários. O UUID é serializado como texto
em `sub`; o token contém também `jti` UUID4, `iat` e `exp`.

Cookies, CSRF, leitura da sessão e revogação no banco serão implementados na #9.
A conclusão do core não significa que o fluxo HttpOnly já esteja funcionando.

## Contexto e decisão

O navegador recebe o JWT em um cookie `HttpOnly` definido pelo backend.
O frontend não recebe o JWT no JSON, não o armazena em Web Storage e não monta
o header `Authorization`. Frontend e API serão servidos pela mesma origem,
com `/api` encaminhado pelo Nginx. Em desenvolvimento, usar o proxy do Vite.

Esta decisão atualiza os contratos de transporte descritos nas issues #9 e #12.
O módulo `core/security.py` da #7 continua responsável por hash e validação
criptográfica. A validade continua configurável por `JWT_EXPIRE_MINUTES`
(padrão: 60 minutos). Não haverá refresh token nesta primeira versão:
após expirar, o usuário faz login novamente.

O cookie impede a leitura do JWT pelo JavaScript, mas um XSS ainda pode realizar
ações autenticadas. Como o navegador envia cookies automaticamente, é necessário
proteger as operações de escrita contra CSRF.

## Contrato a implementar na #9

- Login mantém entrada `application/x-www-form-urlencoded` (`username` ou email
  no campo `username`, mais `password`). Sucesso: HTTP 200 com
  `{"detail": "Login realizado"}` e `Set-Cookie`; não retornar o schema `Token`.
- Cookie de produção: `__Host-access_token`, `HttpOnly`, `Secure`, `SameSite=Lax`,
  `Path=/`, sem `Domain`. `Max-Age` acompanha a validade do JWT; `exp` continua
  sendo verificado pelo servidor independentemente da validade do cookie.
- Em desenvolvimento HTTP local, usar `access_token`, sem `Secure`, mantendo
  `HttpOnly`, `SameSite=Lax`, `Path=/` e sem `Domain`. A exceção deve depender
  explicitamente do ambiente; produção sempre exige `Secure`.
- `get_current_user` lê o cookie, valida o JWT e consulta usuário ativo e
  revogação do `jti`. Ausência, expiração ou invalidade retorna 401 no formato
  de erro existente. Não implementar fallback Bearer para o navegador.
- Ajustar a documentação OpenAPI para autenticação por cookie. A indicação
  `WWW-Authenticate: Bearer` da issue e dos handlers atuais deve ser revista
  junto dessa mudança; não anunciar um mecanismo que a rota não aceita.
- Logout revoga o `jti` até a expiração e remove o cookie com o mesmo nome,
  path e domínio usados na criação; retorna 204. Repetição não gera 500.
  Não basta remover o cookie: uma cópia do JWT revogado também deve ser rejeitada.
- Substituir a fixture `auth_headers` por cliente autenticado/cookies reais.
  Os testes com `auth_user` que substituem a dependência continuam úteis para
  testar regras de perfil isoladamente.

### Proteção contra CSRF

Incluir a proteção na #9, antes da integração com o frontend:

- Exigir `X-CSRF-Token` e validar a origem em operações de escrita
  (`POST`, `PUT`, `PATCH`, `DELETE`), incluindo login e cadastro. Validar
  `Origin` contra uma lista explícita; quando ausente, verificar a origem do
  `Referer`; rejeitar se não houver origem confiável. Considerar a origem
  pública HTTPS, não o endereço interno do container.
- Disponibilizar `GET /api/auth/csrf` para inicialização antes do login e após
  recarregar. Resposta `{"csrf_token": "..."}`, com `Cache-Control: no-store`.
- Usar double-submit **assinado e vinculado à sessão**, não apenas comparar
  um valor arbitrário do header com um cookie. Antes do login, vincular a um
  identificador aleatório de pré-sessão; após login, renovar e vincular ao
  `jti`. O material de assinatura CSRF deve ser separado do segredo JWT.
- O frontend mantém o token CSRF em memória e o envia no header. Esse token
  é distinto do JWT; sua leitura pelo frontend é intencional.
- Renovar o estado CSRF após login e limpar no logout. O frontend deve poder
  obter novo estado de pré-sessão antes de um novo login. Falha CSRF retorna
  403 (`CSRF_INVALID`), sem executar a operação.
- `SameSite` é uma camada adicional; não substitui a validação CSRF.
  GET/HEAD não devem modificar dados da aplicação.

Detalhes internos do formato e armazenamento auxiliar serão implementados e
testados na #9. Documentar as novas variáveis de ambiente nessa entrega.

## Issues impactadas

| Issue | Ajuste necessário |
|---|---|
| #4 — Base frontend | Atualizar o tipo de resposta de login, que deixa de ser `Token`, caso já tenha sido criado. Preservar proxy `/api` no Vite e Nginx. |
| #9 — Login/logout | Implementar contrato de cookies, CSRF, revogação e testes descritos acima. |
| #12 — API e AuthContext | Remover interceptor Bearer e armazenamento do JWT. Usar cookies e header CSRF nas escritas. Inicializar consultando `/api/users/me`, com estado de carregamento, sem tentar ler o cookie HttpOnly. Obter/renovar CSRF antes de enviar operações. |
| #13 — Login/cadastro | Consumir o novo contrato: obter CSRF, enviar formulário, renovar CSRF após login e buscar `/me`. Login automático após cadastro usa o mesmo fluxo. |
| #14 — Logout | Aguardar o logout no servidor e só então limpar o estado local. Falha de rede não deve ser apresentada como revogação concluída. |
| #18 e #22 — SGs e EC2 | Compatibilizar entrada HTTPS com a terminação TLS escolhida na #23; se terminar na EC2, permitir 443 no SG web. |
| #21 — Parameter Store | Provisionar o segredo CSRF separado do JWT e incluí-lo no carregamento de configuração, conforme o nome e formato definidos na #9. |
| #23 — Deploy | Disponibilizar HTTPS com certificado confiável para frontend e API na mesma origem; preservar `Set-Cookie` e headers de proxy. HTTP no Elastic IP pode servir ao healthcheck inicial, mas não atende ao aceite final da autenticação. |
| #24 — Validação | Testar sessão real no navegador, atributos do cookie, CSRF, recarregamento, expiração e revogação. |

As operações de perfil, senha e avatar (#10, #11, #15 e #16) usam a mesma
dependência de autenticação e o cliente HTTP central da #12; não precisam de
um mecanismo próprio de token. A proteção CSRF deve abranger suas escritas,
inclusive upload multipart.

Na mesma origem, cookies são enviados normalmente pelo navegador. Se houver
acesso direto à API em outra origem durante desenvolvimento, configurar
`credentials: "include"`/`withCredentials: true` e CORS com origens explícitas
e credenciais habilitadas, nunca origem `*`. CORS não substitui proteção CSRF.

## Verificação de aceite da integração

- Login não expõe JWT no corpo; cookie de produção tem os atributos definidos.
- Recarregar a página recupera o usuário por `/me`; JWT não aparece em
  `localStorage`, `sessionStorage` ou `document.cookie`.
- Escrita com cookie válido e CSRF ausente/incorreto ou origem não autorizada
  é rejeitada; requisição legítima funciona, inclusive cadastro e upload.
- JWT expirado, adulterado, revogado ou de usuário inativo retorna 401.
- Após logout, reutilizar uma cópia do cookie anterior falha; repetir logout
  conforme o protocolo CSRF não gera 500.
- HTTPS funciona no endereço público. Não desabilitar `Secure` em produção
  para contornar a falta de certificado.

## Pendência de infraestrutura

A #23 precisa definir endereço público, certificado confiável e ponto de
terminação TLS. A decisão de cookie está aceita; essa configuração ainda
precisa ser resolvida antes do teste de autenticação em produção.

### Opção preferencial: HTTPS com Let's Encrypt

Usar certificado gratuito do Let's Encrypt, com emissão e renovação automática
por cliente ACME compatível (por exemplo, Certbot), e recarregar o Nginx após
renovar. São possíveis dois caminhos:

- Domínio/subdomínio apontando para o Elastic IP, com certificado para esse nome.
- Certificado diretamente para o IP público estável. O Let's Encrypt oferece
  certificados de IP em disponibilidade geral desde janeiro de 2026; eles
  duram aproximadamente seis dias. Usar cliente com suporte a certificados
  de IP e ao perfil de curta duração, com renovação automática monitorada.

A #23 deve validar controle do nome/IP pelo desafio ACME escolhido, configurar
as portas necessárias e testar renovação e carregamento do certificado pelo
Nginx. O certificado precisa corresponder ao endereço usado no navegador:
certificado de domínio não valida acesso pelo IP. Manter cookie `Secure` e
redirecionar o acesso HTTP da aplicação para HTTPS.

### Contingência temporária: demonstração por HTTP

Tecnicamente é possível omitir `Secure` e usar `access_token` (sem prefixo
`__Host-`), preservando `HttpOnly`, `SameSite=Lax`, `Path=/`, sem `Domain` e
proteção CSRF. Isso permite transmitir o cookie por HTTP, mas **não oferece
proteção de transporte**: senha, JWT e dados podem ser interceptados ou
alterados na rede. `HttpOnly` e assinatura do JWT não substituem TLS.

Esta opção fica registrada apenas como contingência de demonstração temporária
com contas e dados fictícios, em ambiente controlado; não satisfaz o aceite de
segurança de produção. Antes de usá-la, registrar a limitação no report da #23.
Não implementar fallback automático quando HTTPS falhar.

Se essa contingência for necessária, criar configuração explícita e documentada
na #9/#23, desabilitada por padrão e vedada em produção. Não trocar todo o
ambiente para `dev` para contornar validações nem reutilizar segredos de
desenvolvimento. A configuração ainda não existe no código.

Ao migrar a demonstração para HTTPS, remover o cookie antigo e invalidar as
sessões usadas por HTTP, exigindo novo login. Preferir resolver o certificado
antes da demonstração; a ausência de domínio não impede tentar o certificado
para o Elastic IP.

## Referências

- [OWASP — Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP — CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Let's Encrypt — Certificados de IP e de seis dias](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability)
- [Let's Encrypt — Suporte no Certbot](https://letsencrypt.org/2026/03/11/shorter-certs-certbot)
- [MDN — Atributos Secure e prefixos de cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie)
