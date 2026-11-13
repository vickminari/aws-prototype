/**
 * Contratos da API (ARQ §5.5), espelhando `backend/app/schemas/user.py` e `error.py`.
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

/** Perfil do usuário autenticado, retornado por `/api/users/me` (`UserProfileRead`). */
export interface UserProfileRead extends UserRead {
  is_active: boolean
  /** Data ISO 8601 em UTC. */
  updated_at: string
}

/** Cadastro (`UserCreate`). */
export interface UserCreate {
  full_name: string
  username: string
  email: string
  password: string
  description?: string | null
}

/** Atualização parcial do perfil (`UserUpdate`): envie só os campos alterados. */
export interface UserUpdate {
  full_name?: string
  username?: string
  email?: string
  description?: string | null
}

/** Troca de senha (`PasswordChange`). */
export interface PasswordChange {
  current_password: string
  new_password: string
}

/**
 * Resposta de `POST /api/auth/login`. Substitui o antigo `Token`: o JWT vai em
 * cookie HttpOnly e não aparece no corpo (docs/DECISAO_AUTENTICACAO.md).
 */
export interface LoginResponse {
  detail: string
}

/** Resposta de `GET /api/auth/csrf`. O token é guardado só em memória. */
export interface CsrfResponse {
  csrf_token: string
}

/** Formato padrão de erro da API (`ErrorRead`), ex.: `{ detail, code: "CSRF_INVALID" }`. */
export interface ApiError {
  detail: string
  code: string
}
