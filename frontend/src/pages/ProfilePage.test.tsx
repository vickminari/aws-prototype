import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../hooks/useAuth.ts'
import * as userService from '../services/userService.ts'
import { makeApiError } from '../test/apiError.ts'
import { fakeUser, makeAuthValue } from '../test/auth.ts'
import { ProfilePage } from './ProfilePage.tsx'

vi.mock('../services/userService.ts')

function renderProfile() {
  const refreshUser = vi.fn().mockResolvedValue(undefined)
  render(
    <AuthContext value={makeAuthValue({ user: fakeUser, refreshUser })}>
      <ProfilePage />
    </AuthContext>,
  )
  return { refreshUser, user: userEvent.setup() }
}

describe('ProfilePage', () => {
  beforeEach(() => {
    vi.mocked(userService.updateMe).mockReset()
    vi.mocked(userService.uploadAvatar).mockReset()
  })

  it('envia só os campos alterados e recarrega o usuário', async () => {
    vi.mocked(userService.updateMe).mockResolvedValue({ ...fakeUser, full_name: 'Maria Souza' })
    const { refreshUser, user } = renderProfile()

    const name = screen.getByLabelText('Nome completo')
    await user.clear(name)
    await user.type(name, 'Maria Souza')
    await user.click(screen.getByRole('button', { name: 'Salvar alterações' }))

    expect(userService.updateMe).toHaveBeenCalledWith({ full_name: 'Maria Souza' })
    expect(refreshUser).toHaveBeenCalled()
  })

  it('mostra o erro 409 no campo username', async () => {
    vi.mocked(userService.updateMe).mockRejectedValue(
      makeApiError(409, {
        detail: 'Nome de usuário já cadastrado',
        code: 'USERNAME_ALREADY_EXISTS',
      }),
    )
    const { refreshUser, user } = renderProfile()

    const username = screen.getByLabelText('Nome de usuário')
    await user.clear(username)
    await user.type(username, 'joao.silva')
    await user.click(screen.getByRole('button', { name: 'Salvar alterações' }))

    expect(await screen.findByText('Nome de usuário já cadastrado')).toBeInTheDocument()
    expect(username).toHaveAccessibleDescription('Nome de usuário já cadastrado')
    expect(refreshUser).not.toHaveBeenCalled()
  })

  it('recusa imagem acima de 2 MB sem enviar', async () => {
    const { user } = renderProfile()
    const bigImage = new File([new Uint8Array(2 * 1024 * 1024 + 1)], 'foto.png', {
      type: 'image/png',
    })

    await user.upload(screen.getByLabelText('Arquivo da foto de perfil'), bigImage)

    expect(await screen.findByRole('alert')).toHaveTextContent('A imagem deve ter no máximo 2 MB.')
    expect(userService.uploadAvatar).not.toHaveBeenCalled()
  })
})
