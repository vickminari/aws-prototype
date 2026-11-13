import { Navigate, Outlet } from 'react-router'
import { PageLoader } from '../components/PageLoader.tsx'
import { useAuth } from '../hooks/useAuth.ts'

/** Rotas só para usuário logado; sem sessão, redireciona para `/login`. */
export function ProtectedRoute() {
  const { user, isLoading } = useAuth()

  if (isLoading) return <PageLoader />
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}
