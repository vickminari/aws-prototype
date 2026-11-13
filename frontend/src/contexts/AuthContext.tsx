import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { toast } from 'sonner'
import { clearCsrfToken, setUnauthorizedHandler } from '../services/api.ts'
import * as authService from '../services/authService.ts'
import { getMe } from '../services/userService.ts'
import type { UserProfileRead } from '../types/user.ts'
import { AuthContext, type AuthContextValue } from '../hooks/useAuth.ts'

/**
 * Mantém a sessão (ARQ §7.4, adaptada ao cookie HttpOnly): ao abrir, consulta
 * `/api/users/me` para saber se há sessão; em 401 de qualquer chamada, limpa o usuário
 * e as rotas protegidas redirecionam para `/login`.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfileRead | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const userRef = useRef<UserProfileRead | null>(null)

  useEffect(() => {
    userRef.current = user
  }, [user])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      // Só avisa quem estava logado; visitante em página pública não recebe toast.
      if (userRef.current) toast.error('Sessão expirada. Entre novamente.')
      clearCsrfToken()
      setUser(null)
    })
    return () => setUnauthorizedHandler(null)
  }, [])

  useEffect(() => {
    let active = true
    getMe({ skipAuthRedirect: true })
      .then((me) => {
        if (active) setUser(me)
      })
      .catch(() => {
        if (active) setUser(null)
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    await authService.login(username, password)
    setUser(await getMe())
  }, [])

  const logout = useCallback(async () => {
    await authService.logout()
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    setUser(await getMe())
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, login, logout, refreshUser }),
    [user, isLoading, login, logout, refreshUser],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
