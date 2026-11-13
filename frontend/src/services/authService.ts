import { isAxiosError } from 'axios'
import type { LoginResponse, UserCreate, UserRead } from '../types/user.ts'
import { api, clearCsrfToken } from './api.ts'

/** Cadastra um usuário. Não faz login: o chamador faz em seguida, se quiser. */
export async function register(data: UserCreate): Promise<UserRead> {
  const response = await api.post<UserRead>('/auth/register', data)
  return response.data
}

/**
 * Faz login com username ou email. O backend responde com o cookie de sessão;
 * 401 (credenciais inválidas) é repassado ao chamador, sem o tratamento global.
 */
export async function login(username: string, password: string): Promise<LoginResponse> {
  // URLSearchParams → application/x-www-form-urlencoded (OAuth2PasswordRequestForm).
  const body = new URLSearchParams({ username, password })
  const response = await api.post<LoginResponse>('/auth/login', body, { skipAuthRedirect: true })
  // O backend renova o CSRF ao autenticar; o token da pré-sessão deixa de valer.
  clearCsrfToken()
  return response.data
}

/**
 * Encerra a sessão no servidor (revoga o JWT). 401 conta como sucesso, pois a
 * sessão já não vale; falha de rede é relançada para não fingir um logout que não ocorreu.
 */
export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout', null, { skipAuthRedirect: true })
  } catch (error) {
    if (!isAxiosError(error) || error.response?.status !== 401) throw error
  }
  clearCsrfToken()
}
