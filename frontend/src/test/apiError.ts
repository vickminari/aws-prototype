import { AxiosError, AxiosHeaders, type AxiosResponse } from 'axios'

/** Cria um erro do axios como o que a API devolveria, ex.: 401 ou 409 com `{ detail, code }`. */
export function makeApiError(status: number, data: unknown): AxiosError {
  const config = { headers: new AxiosHeaders() }
  const response: AxiosResponse = { status, statusText: '', data, headers: {}, config }
  return new AxiosError(
    `Request failed with status code ${status}`,
    'ERR_BAD_REQUEST',
    config,
    null,
    response,
  )
}
