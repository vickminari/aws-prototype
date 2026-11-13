import axios, { type AxiosError } from 'axios'
import type { ApiError, CsrfResponse } from '../types/user.ts'

declare module 'axios' {
  interface AxiosRequestConfig {
    /** Não dispara o tratamento global de 401 (ex.: login com senha errada, checagem inicial do `/me`). */
    skipAuthRedirect?: boolean
    /** Uso interno: a requisição já foi repetida após renovar o CSRF. */
    csrfRetried?: boolean
  }
}

/**
 * Instância única do axios (ARQ §7.5). A sessão é um cookie HttpOnly enviado pelo
 * navegador; o frontend nunca lê nem envia o JWT (docs/DECISAO_AUTENTICACAO.md).
 */
export const api = axios.create({ baseURL: '/api' })

/** Métodos que alteram dados e por isso exigem o header `X-CSRF-Token`. */
const WRITE_METHODS = new Set(['post', 'put', 'patch', 'delete'])

let csrfToken: string | null = null
let csrfRequest: Promise<string> | null = null

/** Retorna o token CSRF em memória, buscando um novo em `/api/auth/csrf` se não houver. */
export async function getCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken
  // Reaproveita a busca em andamento quando várias escritas saem ao mesmo tempo.
  csrfRequest ??= api
    .get<CsrfResponse>('/auth/csrf')
    .then(({ data }) => {
      csrfToken = data.csrf_token
      return csrfToken
    })
    .finally(() => {
      csrfRequest = null
    })
  return csrfRequest
}

/** Descarta o token CSRF; o próximo envio busca outro (após login, logout ou 401). */
export function clearCsrfToken(): void {
  csrfToken = null
}

let unauthorizedHandler: (() => void) | null = null

/** Registra quem trata a sessão expirada (o `AuthProvider`). */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}

api.interceptors.request.use(async (config) => {
  if (config.method && WRITE_METHODS.has(config.method.toLowerCase())) {
    config.headers.set('X-CSRF-Token', await getCsrfToken())
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const config = error.config
    const status = error.response?.status

    // CSRF expirado ou de outra sessão: renova e repete uma única vez.
    if (status === 403 && error.response?.data?.code === 'CSRF_INVALID' && config) {
      if (!config.csrfRetried) {
        clearCsrfToken()
        config.csrfRetried = true
        return api(config)
      }
    }

    if (status === 401 && !config?.skipAuthRedirect) {
      unauthorizedHandler?.()
    }

    return Promise.reject(error)
  },
)
