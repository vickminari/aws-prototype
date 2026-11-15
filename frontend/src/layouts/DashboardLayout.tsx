import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { ThemeToggle } from '../components/ThemeToggle.tsx'
import { Avatar } from '../components/ui/Avatar.tsx'
import { Spinner } from '../components/ui/Spinner.tsx'
import { useAuth } from '../hooks/useAuth.ts'

const NAV_ITEMS = [
  // end: "Início" só fica ativo em /dashboard, não nas subpáginas
  { to: '/dashboard', label: 'Início', end: true },
  { to: '/dashboard/profile', label: 'Meu perfil', end: false },
  { to: '/dashboard/password', label: 'Alterar senha', end: false },
]

const itemClasses =
  'flex w-full items-center rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'

interface SidebarNavProps {
  onNavigate: () => void
  onLogout: () => void
  isLoggingOut: boolean
}

/** Itens do menu; usado na sidebar (desktop) e no menu aberto pelo botão (celular). */
function SidebarNav({ onNavigate, onLogout, isLoggingOut }: SidebarNavProps) {
  return (
    <nav aria-label="Menu principal" className="flex flex-col gap-1 p-3">
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            `${itemClasses} ${
              isActive
                ? 'bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300'
                : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`
          }
        >
          {item.label}
        </NavLink>
      ))}
      <button
        type="button"
        onClick={onLogout}
        disabled={isLoggingOut}
        aria-busy={isLoggingOut || undefined}
        className={`${itemClasses} gap-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 disabled:cursor-not-allowed disabled:opacity-60`}
      >
        {isLoggingOut && <Spinner label="Saindo" />}
        Sair
      </button>
    </nav>
  )
}

/** Moldura das páginas logadas (ARQ §7.3): sidebar, topbar com o usuário e o conteúdo da rota. */
export function DashboardLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  async function handleLogout() {
    setIsLoggingOut(true)
    try {
      await logout()
      navigate('/login', { replace: true })
    } catch {
      // O logout só limpa a sessão se o servidor confirmar (docs/DECISAO_AUTENTICACAO.md, #14)
      toast.error('Não foi possível sair. Verifique sua conexão e tente novamente.')
      setIsLoggingOut(false)
    }
  }

  // O ProtectedRoute garante o usuário; a checagem só estreita o tipo
  if (!user) return null

  const navProps = {
    onNavigate: () => setIsMenuOpen(false),
    onLogout: handleLogout,
    isLoggingOut,
  }

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 md:flex">
        <p className="flex h-16 items-center px-6 text-lg font-semibold text-slate-900 dark:text-slate-100">
          Protótipo 1
        </p>
        <SidebarNav {...navProps} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center gap-3 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 md:px-8">
          <button
            type="button"
            onClick={() => setIsMenuOpen((open) => !open)}
            aria-expanded={isMenuOpen}
            aria-controls="menu-celular"
            aria-label={isMenuOpen ? 'Fechar menu' : 'Abrir menu'}
            className="rounded-md p-2 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-blue-600 md:hidden"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" className="size-5" fill="none">
              <path
                d={isMenuOpen ? 'M6 6l12 12M18 6L6 18' : 'M4 6h16M4 12h16M4 18h16'}
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
          <span className="font-semibold text-slate-900 dark:text-slate-100 md:hidden">
            Protótipo 1
          </span>

          <div className="ml-auto flex min-w-0 items-center gap-3">
            <ThemeToggle />
            <span className="hidden truncate text-sm font-medium text-slate-700 dark:text-slate-300 sm:block">
              {user.full_name}
            </span>
            <Avatar name={user.full_name} src={user.profile_image_url} size="sm" />
          </div>
        </header>

        {isMenuOpen && (
          <div
            id="menu-celular"
            className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 md:hidden"
          >
            <SidebarNav {...navProps} />
          </div>
        )}

        <main className="flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
