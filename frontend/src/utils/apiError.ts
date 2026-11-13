import { isAxiosError } from 'axios'

interface ApiErrorInfo {
  /** Status HTTP; `undefined` em falha de rede. */
  status?: number
  /** Código de domínio do backend, ex.: `EMAIL_ALREADY_EXISTS`. */
  code?: string
  /** Mensagem do backend (`detail`) quando é texto. */
  detail?: string
}

/** Extrai status, `code` e `detail` de um erro da API (formato `ErrorRead`). */
export function getApiError(error: unknown): ApiErrorInfo {
  if (!isAxiosError(error)) return {}
  const data: unknown = error.response?.data
  const body = typeof data === 'object' && data !== null ? (data as Record<string, unknown>) : {}
  return {
    status: error.response?.status,
    code: typeof body.code === 'string' ? body.code : undefined,
    detail: typeof body.detail === 'string' ? body.detail : undefined,
  }
}

/**
 * Erros por campo de uma resposta 422 (`ValidationErrorRead`): `loc` termina no nome do
 * campo, ex.: `["body", "email"]` → `{ field: "email", message: "..." }`.
 */
export function getValidationErrors(error: unknown): { field: string; message: string }[] {
  if (!isAxiosError(error) || error.response?.status !== 422) return []
  const detail: unknown = (error.response.data as { detail?: unknown } | undefined)?.detail
  if (!Array.isArray(detail)) return []
  return detail.flatMap((issue: { loc?: unknown[]; msg?: unknown }) => {
    const field = issue.loc?.at(-1)
    return typeof field === 'string' && typeof issue.msg === 'string'
      ? [{ field, message: issue.msg }]
      : []
  })
}
