import { Link } from 'react-router'
import { Avatar } from '../components/ui/Avatar.tsx'
import { Card } from '../components/ui/Card.tsx'
import { useAuth } from '../hooks/useAuth.ts'
import { formatDate } from '../utils/formatDate.ts'

/** Página inicial do dashboard: resumo do perfil do usuário logado. */
export function DashboardHomePage() {
  const { user } = useAuth()
  // O ProtectedRoute garante o usuário; a checagem só estreita o tipo
  if (!user) return null

  const firstName = user.full_name.trim().split(/\s+/)[0]

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
        Olá, {firstName}!
      </h1>

      <Card className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
        <Avatar name={user.full_name} src={user.profile_image_url} size="lg" />
        <div className="min-w-0 text-center sm:text-left">
          <h2 className="text-xl font-semibold break-words text-slate-900 dark:text-slate-100">
            {user.full_name}
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">@{user.username}</p>

          {user.description ? (
            <p className="mt-3 break-words whitespace-pre-line text-slate-700 dark:text-slate-300">
              {user.description}
            </p>
          ) : (
            <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
              Você ainda não escreveu uma descrição.{' '}
              <Link
                to="/dashboard/profile"
                className="font-medium text-blue-600 dark:text-blue-400 hover:underline"
              >
                Editar perfil
              </Link>
            </p>
          )}

          <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
            Membro desde {formatDate(user.created_at)}
          </p>
        </div>
      </Card>
    </div>
  )
}
