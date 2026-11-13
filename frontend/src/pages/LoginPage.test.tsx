import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RouterProvider, createMemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../hooks/useAuth.ts'
import { makeApiError } from '../test/apiError.ts'
import { makeAuthValue } from '../test/auth.ts'
import { LoginPage } from './LoginPage.tsx'

function renderLogin(login = vi.fn().mockResolvedValue(undefined)) {
  const router = createMemoryRouter(
    [
      { path: '/login', element: <LoginPage /> },
      { path: '/dashboard', element: <h1>Dashboard</h1> },
    ],
    { initialEntries: ['/login'] },
  )
  render(
    <AuthContext value={makeAuthValue({ login })}>
      <RouterProvider router={router} />
    </AuthContext>,
  )
  return { login, user: userEvent.setup() }
}

describe('LoginPage', () => {
  it('mostra erros de validação e não envia com campos vazios', async () => {
    const { login, user } = renderLogin()

    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('Informe o usuário ou email')).toBeInTheDocument()
    expect(screen.getByText('Informe a senha')).toBeInTheDocument()
    expect(login).not.toHaveBeenCalled()
  })

  it('chama o login com os dados digitados e vai para o dashboard', async () => {
    const { login, user } = renderLogin()

    await user.type(screen.getByLabelText('Usuário ou email'), 'maria.silva')
    await user.type(screen.getByLabelText('Senha'), 'Senha123')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(login).toHaveBeenCalledWith('maria.silva', 'Senha123')
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('mostra erro genérico em 401', async () => {
    const login = vi
      .fn()
      .mockRejectedValue(
        makeApiError(401, { detail: 'Usuário ou senha inválidos', code: 'INVALID_CREDENTIALS' }),
      )
    const { user } = renderLogin(login)

    await user.type(screen.getByLabelText('Usuário ou email'), 'maria.silva')
    await user.type(screen.getByLabelText('Senha'), 'SenhaErrada1')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Usuário ou senha inválidos')
    expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument()
  })
})
