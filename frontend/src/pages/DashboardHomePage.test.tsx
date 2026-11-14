import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AuthContext } from '../hooks/useAuth.ts'
import { fakeUser, makeAuthValue } from '../test/auth.ts'
import type { UserProfileRead } from '../types/user.ts'
import { DashboardHomePage } from './DashboardHomePage.tsx'

function renderHome(user: UserProfileRead) {
  render(
    <AuthContext value={makeAuthValue({ user })}>
      <MemoryRouter>
        <DashboardHomePage />
      </MemoryRouter>
    </AuthContext>,
  )
}

describe('DashboardHomePage', () => {
  it('mostra nome, username, iniciais e data de cadastro', () => {
    renderHome(fakeUser)

    expect(screen.getByRole('heading', { name: 'Olá, Maria!' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Maria Silva' })).toBeInTheDocument()
    expect(screen.getByText('@maria.silva')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Maria Silva' })).toHaveTextContent('MS')
    expect(screen.getByText('Membro desde 7 de novembro de 2026')).toBeInTheDocument()
  })

  it('sem descrição, sugere editar o perfil', () => {
    renderHome(fakeUser)

    expect(screen.getByText(/ainda não escreveu uma descrição/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Editar perfil' })).toHaveAttribute(
      'href',
      '/dashboard/profile',
    )
  })

  it('mostra a descrição e a foto quando existem', () => {
    renderHome({
      ...fakeUser,
      description: 'Estudante de Engenharia de Software',
      profile_image_url: 'https://example.com/avatar.png',
    })

    expect(screen.getByText('Estudante de Engenharia de Software')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Editar perfil' })).not.toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Maria Silva' })).toHaveAttribute(
      'src',
      'https://example.com/avatar.png',
    )
  })
})
