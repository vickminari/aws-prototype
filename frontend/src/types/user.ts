/**
 * Contratos da API (ARQ §5.5), espelhando `backend/app/schemas/user.py`.
 * UUIDs e datas chegam como string no JSON.
 */

/** Dados públicos do usuário (`UserRead`). */
export interface UserRead {
  id: string
  full_name: string
  username: string
  email: string
  description: string | null
  profile_image_url: string | null
  /** Data ISO 8601 em UTC. */
  created_at: string
}

/**
 * Resposta de `POST /api/auth/login`. Substitui o antigo `Token`: o JWT vai em
 * cookie HttpOnly e não aparece no corpo (docs/DECISAO_AUTENTICACAO.md).
 */
export interface LoginResponse {
  detail: string
}
