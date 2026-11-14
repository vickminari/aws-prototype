import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RouterProvider, createMemoryRouter } from 'react-router'
import { toast } from 'sonner'
import { describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../hooks/useAuth.ts'
import { fakeUser, makeAuthValue } from '../test/auth.ts'
import { DashboardLayout } from './DashboardLayout.tsx'

vi.mock('sonner', () => ({ toast: { error: vi.fn() } }))

function renderLayout({ path = '/dashboard', logout = vi.fn().mockResolvedValue(undefined) } = {}) {
  const router = createMemoryRouter(
    [
      {
        element: <DashboardLayout />,
        children: [
          { path: '/dashboard', element: <h1>Conteúdo início</h1> },
          { path: '/dashboard/profile', element: <h1>Conteúdo perfil</h1> },
        ],
      },
      { path: '/login', element: <h1>Página de login</h1> },
    ],
    { initialEntries: [path] },
  )
  render(
    <AuthContext value={makeAuthValue({ user: fakeUser, logout })}>
      <RouterProvider router={router} />
    </AuthContext>,
  )
  return { logout, user: userEvent.setup() }
}

describe('DashboardLayout', () => {
  it('mostra o menu, o usuário na topbar e o conteúdo da rota', () => {
    renderLayout()

    const nav = screen.getByRole('navigation', { name: 'Menu principal' })
    expect(within(nav).getByRole('link', { name: 'Início' })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'Meu perfil' })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'Alterar senha' })).toBeInTheDocument()
    expect(within(nav).getByRole('button', { name: 'Sair' })).toBeInTheDocument()
    expect(screen.getByText('Maria Silva')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Conteúdo início' })).toBeInTheDocument()
  })

  it('destaca só o item da rota atual', () => {
    renderLayout({ path: '/dashboard/profile' })

    expect(screen.getByRole('link', { name: 'Meu perfil' })).toHaveAttribute('aria-current', 'page')
    // "Início" (/dashboard) não fica ativo nas subpáginas
    expect(screen.getByRole('link', { name: 'Início' })).not.toHaveAttribute('aria-current')
  })

  it('sai e volta para /login', async () => {
    const { logout, user } = renderLayout()

    await user.click(screen.getByRole('button', { name: 'Sair' }))

    expect(logout).toHaveBeenCalledOnce()
    expect(await screen.findByRole('heading', { name: 'Página de login' })).toBeInTheDocument()
  })

  it('continua no dashboard e avisa quando o logout falha', async () => {
    const { user } = renderLayout({ logout: vi.fn().mockRejectedValue(new Error('Network Error')) })

    await user.click(screen.getByRole('button', { name: 'Sair' }))

    expect(toast.error).toHaveBeenCalledWith(
      'Não foi possível sair. Verifique sua conexão e tente novamente.',
    )
    expect(screen.getByRole('heading', { name: 'Conteúdo início' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sair' })).toBeEnabled()
  })

  it('abre e fecha o menu do celular', async () => {
    const { user } = renderLayout()
    const toggle = screen.getByRole('button', { name: 'Abrir menu' })

    await user.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getAllByRole('navigation', { name: 'Menu principal' })).toHaveLength(2)

    // Navegar pelo menu do celular o fecha
    const mobileMenu = screen.getAllByRole('navigation', { name: 'Menu principal' })[1]
    await user.click(within(mobileMenu).getByRole('link', { name: 'Meu perfil' }))
    expect(await screen.findByRole('heading', { name: 'Conteúdo perfil' })).toBeInTheDocument()
    expect(screen.getAllByRole('navigation', { name: 'Menu principal' })).toHaveLength(1)
  })
})
