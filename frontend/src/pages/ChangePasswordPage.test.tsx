import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'sonner'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as userService from '../services/userService.ts'
import { makeApiError } from '../test/apiError.ts'
import { ChangePasswordPage } from './ChangePasswordPage.tsx'

vi.mock('../services/userService.ts')
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

function renderPage() {
  render(<ChangePasswordPage />)
  return userEvent.setup()
}

async function fillForm(
  user: ReturnType<typeof userEvent.setup>,
  {
    current = 'SenhaAtual1',
    next = 'NovaSenha2',
    confirm = next,
  }: { current?: string; next?: string; confirm?: string } = {},
) {
  await user.type(screen.getByLabelText('Senha atual'), current)
  await user.type(screen.getByLabelText('Nova senha'), next)
  await user.type(screen.getByLabelText('Confirmar nova senha'), confirm)
}

const submit = () => screen.getByRole('button', { name: 'Salvar nova senha' })

describe('ChangePasswordPage', () => {
  beforeEach(() => {
    vi.mocked(userService.changePassword).mockReset()
    vi.mocked(toast.success).mockReset()
    vi.mocked(toast.error).mockReset()
  })

  it('mostra erros de validação e não envia com campos vazios', async () => {
    const user = renderPage()

    await user.click(submit())

    expect(await screen.findByText('Informe a senha atual')).toBeInTheDocument()
    expect(screen.getByText('Confirme a nova senha')).toBeInTheDocument()
    expect(userService.changePassword).not.toHaveBeenCalled()
  })

  it('marca as regras de força conforme a nova senha é digitada', async () => {
    const user = renderPage()
    const rules = screen.getByRole('list', { name: 'Regras da senha' })

    expect(within(rules).getAllByText('(pendente)')).toHaveLength(3)

    await user.type(screen.getByLabelText('Nova senha'), 'abc1')
    expect(within(rules).getByText('Ao menos uma letra')).toHaveTextContent('(atendida)')
    expect(within(rules).getByText('Ao menos um número')).toHaveTextContent('(atendida)')
    expect(within(rules).getByText('Mínimo de 8 caracteres')).toHaveTextContent('(pendente)')
  })

  it('exige confirmação igual e nova senha diferente da atual', async () => {
    const user = renderPage()

    await fillForm(user, { confirm: 'OutraSenha3' })
    await user.click(submit())
    expect(await screen.findByText('As senhas não conferem')).toBeInTheDocument()

    await user.clear(screen.getByLabelText('Nova senha'))
    await user.type(screen.getByLabelText('Nova senha'), 'SenhaAtual1')
    await user.clear(screen.getByLabelText('Confirmar nova senha'))
    await user.type(screen.getByLabelText('Confirmar nova senha'), 'SenhaAtual1')
    await user.click(submit())
    expect(await screen.findByText('A nova senha deve ser diferente da atual')).toBeInTheDocument()

    expect(userService.changePassword).not.toHaveBeenCalled()
  })

  it('troca a senha, avisa e limpa o formulário', async () => {
    vi.mocked(userService.changePassword).mockResolvedValue(undefined)
    const user = renderPage()

    await fillForm(user)
    await user.click(submit())

    expect(userService.changePassword).toHaveBeenCalledWith({
      current_password: 'SenhaAtual1',
      new_password: 'NovaSenha2',
    })
    expect(toast.success).toHaveBeenCalledWith('Senha alterada com sucesso.')
    expect(screen.getByLabelText('Senha atual')).toHaveValue('')
    expect(screen.getByLabelText('Nova senha')).toHaveValue('')
    expect(screen.getByLabelText('Confirmar nova senha')).toHaveValue('')
  })

  it('mostra o erro no campo "Senha atual" quando a API responde 400', async () => {
    vi.mocked(userService.changePassword).mockRejectedValue(
      makeApiError(400, { detail: 'Senha atual incorreta', code: 'WRONG_PASSWORD' }),
    )
    const user = renderPage()

    await fillForm(user)
    await user.click(submit())

    expect(await screen.findByText('Senha atual incorreta')).toBeInTheDocument()
    expect(screen.getByLabelText('Senha atual')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Nova senha')).toHaveValue('NovaSenha2')
    expect(toast.success).not.toHaveBeenCalled()
  })

  it('avisa com toast em erro inesperado', async () => {
    vi.mocked(userService.changePassword).mockRejectedValue(
      makeApiError(500, { detail: 'Erro interno do servidor', code: 'INTERNAL_ERROR' }),
    )
    const user = renderPage()

    await fillForm(user)
    await user.click(submit())

    expect(toast.error).toHaveBeenCalledWith('Não foi possível alterar a senha. Tente novamente.')
  })
})
