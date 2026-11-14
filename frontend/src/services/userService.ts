import type { PasswordChange, UserProfileRead, UserUpdate } from '../types/user.ts'
import { api } from './api.ts'

interface GetMeOptions {
  /** `true` na checagem inicial da sessão: 401 só significa "não logado". */
  skipAuthRedirect?: boolean
}

/** Busca o usuário da sessão atual. */
export async function getMe({
  skipAuthRedirect = false,
}: GetMeOptions = {}): Promise<UserProfileRead> {
  const response = await api.get<UserProfileRead>('/users/me', { skipAuthRedirect })
  return response.data
}

/** Atualiza o perfil; envie só os campos alterados. */
export async function updateMe(data: UserUpdate): Promise<UserProfileRead> {
  const response = await api.patch<UserProfileRead>('/users/me', data)
  return response.data
}

/** Troca a senha (204 sem corpo). */
export async function changePassword(data: PasswordChange): Promise<void> {
  await api.put('/users/me/password', data)
}

/** Envia a foto de perfil como multipart (campo `file`). */
export async function uploadAvatar(file: File): Promise<UserProfileRead> {
  const form = new FormData()
  form.append('file', file)
  const response = await api.post<UserProfileRead>('/users/me/avatar', form)
  return response.data
}

/** Remove a foto de perfil. */
export async function deleteAvatar(): Promise<UserProfileRead> {
  const response = await api.delete<UserProfileRead>('/users/me/avatar')
  return response.data
}
