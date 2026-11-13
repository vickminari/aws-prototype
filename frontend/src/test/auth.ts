import { vi } from 'vitest'
import type { AuthContextValue } from '../hooks/useAuth.ts'
import type { UserProfileRead } from '../types/user.ts'

/** Usuário fictício para testes. */
export const fakeUser: UserProfileRead = {
  id: '12345678-1234-4234-8234-123456789abc',
  full_name: 'Maria Silva',
  username: 'maria.silva',
  email: 'maria@example.com',
  description: null,
  profile_image_url: null,
  created_at: '2026-11-07T12:00:00Z',
  is_active: true,
  updated_at: '2026-11-07T12:00:00Z',
}

/** Valor do AuthContext para testes: visitante sem sessão, com funções simuladas. */
export function makeAuthValue(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    user: null,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
    ...overrides,
  }
}
