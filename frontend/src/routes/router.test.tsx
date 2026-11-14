import { render, screen } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AuthContext } from '../hooks/useAuth.ts'
import { fakeUser, makeAuthValue } from '../test/auth.ts'
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

  it('renderiza a página 404 em rota inexistente', () => {
    const router = createMemoryRouter(routes, { initialEntries: ['/rota-que-nao-existe'] })

    render(
      <AuthContext value={makeAuthValue()}>
        <RouterProvider router={router} />
      </AuthContext>,
    )

    expect(screen.getByRole('heading', { name: 'Página não encontrada' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Voltar ao início' })).toHaveAttribute('href', '/')
  })

  it('mostra as páginas do dashboard dentro do layout', () => {
    const router = createMemoryRouter(routes, { initialEntries: ['/dashboard'] })

    render(
      <AuthContext value={makeAuthValue({ user: fakeUser })}>
        <RouterProvider router={router} />
      </AuthContext>,
    )

    expect(screen.getByRole('navigation', { name: 'Menu principal' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Olá, Maria!' })).toBeInTheDocument()
  })
})
