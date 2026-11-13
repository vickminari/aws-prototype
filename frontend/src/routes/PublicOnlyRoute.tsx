import { Navigate, Outlet } from 'react-router'
import { PageLoader } from '../components/PageLoader.tsx'
import { useAuth } from '../hooks/useAuth.ts'

/** Rotas só para visitante (login e cadastro); com sessão, redireciona para `/dashboard`. */
export function PublicOnlyRoute() {
  const { user, isLoading } = useAuth()

  if (isLoading) return <PageLoader />
  if (user) return <Navigate to="/dashboard" replace />
  return <Outlet />
}
