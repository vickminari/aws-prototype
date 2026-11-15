import { Spinner } from './ui/Spinner.tsx'

/** Tela de carregamento enquanto a sessão é verificada. */
export function PageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center text-blue-600 dark:text-blue-400">
      <Spinner label="Verificando sessão" className="scale-150" />
    </div>
  )
}
