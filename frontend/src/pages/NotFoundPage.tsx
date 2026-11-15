import { Link } from 'react-router'
import { ThemeToggle } from '../components/ThemeToggle.tsx'

/** Rota inexistente (`*`). O link para `/` leva ao dashboard ou ao login, conforme a sessão. */
export function NotFoundPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-50 dark:bg-slate-950 p-4 text-center">
      <div className="fixed top-4 right-4 z-10">
        <ThemeToggle />
      </div>
      <div className="page-enter flex flex-col items-center">
        <p className="text-6xl font-bold text-blue-600 dark:text-blue-400">404</p>
        <h1 className="mt-4 text-2xl font-semibold text-slate-900 dark:text-slate-100">
          Página não encontrada
        </h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          O endereço acessado não existe.
        </p>
        <Link
          to="/"
          className="mt-6 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          Voltar ao início
        </Link>
      </div>
    </main>
  )
}
