import { Navigate, createBrowserRouter, type RouteObject } from 'react-router'
import { ChangePasswordPage } from '../pages/ChangePasswordPage.tsx'
import { DashboardHomePage } from '../pages/DashboardHomePage.tsx'
import { LoginPage } from '../pages/LoginPage.tsx'
import { NotFoundPage } from '../pages/NotFoundPage.tsx'
import { ProfilePage } from '../pages/ProfilePage.tsx'
import { RegisterPage } from '../pages/RegisterPage.tsx'
import { ProtectedRoute } from './ProtectedRoute.tsx'
import { PublicOnlyRoute } from './PublicOnlyRoute.tsx'

/**
 * Rotas da ARQ §7.3. Exportadas à parte para os testes montarem com `createMemoryRouter`.
 * O `DashboardLayout` entra na #14.
 */
export const routes: RouteObject[] = [
  {
    element: <PublicOnlyRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      // Sem sessão, o ProtectedRoute leva para /login; com sessão, vai para o dashboard.
      { path: '/', element: <Navigate to="/dashboard" replace /> },
      { path: '/dashboard', element: <DashboardHomePage /> },
      { path: '/dashboard/profile', element: <ProfilePage /> },
      { path: '/dashboard/password', element: <ChangePasswordPage /> },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]

export const router = createBrowserRouter(routes)
