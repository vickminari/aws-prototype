import { render, screen } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AuthContext } from '../hooks/useAuth.ts'
import { makeAuthValue } from '../test/auth.ts'
import { routes } from './router.tsx'

describe('router', () => {
  it('renderiza a página de login em /login', () => {
    const router = createMemoryRouter(routes, { initialEntries: ['/login'] })

    render(
      <AuthContext value={makeAuthValue()}>
        <RouterProvider router={router} />
      </AuthContext>,
    )

    expect(screen.getByRole('heading', { name: 'Entrar' })).toBeInTheDocument()
  })
})
