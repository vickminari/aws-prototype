import { createContext, useContext } from 'react'
import type { UserProfileRead } from '../types/user.ts'

/** Estado da sessão exposto por `useAuth()`. */
export interface AuthContextValue {
  /** Usuário logado, ou `null` se não houver sessão. */
  user: UserProfileRead | null
  /** `true` enquanto a sessão é verificada ao abrir a aplicação. */
  isLoading: boolean
  /** Faz login e carrega o usuário. Erros (ex.: 401) são repassados ao chamador. */
  login: (username: string, password: string) => Promise<void>
  /** Encerra a sessão no servidor e só então limpa o estado; falha de rede é relançada. */
  logout: () => Promise<void>
  /** Recarrega o usuário (ex.: após editar o perfil). */
  refreshUser: () => Promise<void>
}

/**
 * Contexto da sessão, preenchido pelo `AuthProvider` (contexts/AuthContext.tsx).
 * Fica fora do arquivo do provider para o Fast Refresh do Vite funcionar; os testes
 * o usam para simular a sessão.
 */
export const AuthContext = createContext<AuthContextValue | null>(null)

/** Acessa a sessão: `user`, `isLoading`, `login`, `logout` e `refreshUser`. Exige o `AuthProvider`. */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth precisa estar dentro de <AuthProvider>')
  return context
}
