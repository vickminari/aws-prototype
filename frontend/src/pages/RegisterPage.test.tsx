import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RouterProvider, createMemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../hooks/useAuth.ts'
import * as authService from '../services/authService.ts'
import { makeApiError } from '../test/apiError.ts'
import { makeAuthValue } from '../test/auth.ts'
import { RegisterPage } from './RegisterPage.tsx'

vi.mock('../services/authService.ts')

function renderRegister() {
  const login = vi.fn().mockResolvedValue(undefined)
  const router = createMemoryRouter(
    [
      { path: '/register', element: <RegisterPage /> },
      { path: '/dashboard', element: <h1>Dashboard</h1> },
    ],
    { initialEntries: ['/register'] },
  )
  render(
    <AuthContext value={makeAuthValue({ login })}>
      <RouterProvider router={router} />
    </AuthContext>,
  )
  return { login, user: userEvent.setup() }
}

async function fillForm(user: ReturnType<typeof userEvent.setup>, confirmPassword: string) {
  await user.type(screen.getByLabelText('Nome completo'), 'Maria Silva')
  await user.type(screen.getByLabelText('Nome de usuário'), 'maria.silva')
  await user.type(screen.getByLabelText('Email'), 'maria@example.com')
  await user.type(screen.getByLabelText('Senha'), 'Senha123')
  await user.type(screen.getByLabelText('Confirmar senha'), confirmPassword)
}

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.mocked(authService.register).mockReset()
  })

  it('bloqueia o envio quando as senhas são diferentes', async () => {
    const { login, user } = renderRegister()

    await fillForm(user, 'Outra123')
    await user.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(await screen.findByText('As senhas não conferem')).toBeInTheDocument()
    expect(authService.register).not.toHaveBeenCalled()
    expect(login).not.toHaveBeenCalled()
  })

  it('mostra o erro 409 no campo email', async () => {
    vi.mocked(authService.register).mockRejectedValue(
      makeApiError(409, { detail: 'Email já cadastrado', code: 'EMAIL_ALREADY_EXISTS' }),
    )
    const { login, user } = renderRegister()

    await fillForm(user, 'Senha123')
    await user.click(screen.getByRole('button', { name: 'Criar conta' }))

    const email = screen.getByLabelText('Email')
    expect(await screen.findByText('Email já cadastrado')).toBeInTheDocument()
    expect(email).toHaveAttribute('aria-invalid', 'true')
    expect(email).toHaveAccessibleDescription('Email já cadastrado')
    expect(login).not.toHaveBeenCalled()
  })
})
