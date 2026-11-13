import { render, screen } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AuthContext, type AuthContextValue } from '../hooks/useAuth.ts'
import { fakeUser, makeAuthValue } from '../test/auth.ts'
import { ProtectedRoute } from './ProtectedRoute.tsx'

function renderProtected(auth: AuthContextValue) {
  const router = createMemoryRouter(
    [
      {
        element: <ProtectedRoute />,
        children: [{ path: '/dashboard', element: <h1>Área protegida</h1> }],
      },
      { path: '/login', element: <h1>Página de login</h1> },
    ],
    { initialEntries: ['/dashboard'] },
  )
  render(
    <AuthContext value={auth}>
      <RouterProvider router={router} />
    </AuthContext>,
  )
}

describe('ProtectedRoute', () => {
  it('redireciona para /login sem usuário', () => {
    renderProtected(makeAuthValue({ user: null }))

    expect(screen.getByRole('heading', { name: 'Página de login' })).toBeInTheDocument()
    expect(screen.queryByText('Área protegida')).not.toBeInTheDocument()
  })

  it('renderiza a rota com usuário', () => {
    renderProtected(makeAuthValue({ user: fakeUser }))

    expect(screen.getByRole('heading', { name: 'Área protegida' })).toBeInTheDocument()
  })
})
