import { Navigate, createBrowserRouter, type RouteObject } from 'react-router'
import { ChangePasswordPage } from '../pages/ChangePasswordPage.tsx'
import { DashboardHomePage } from '../pages/DashboardHomePage.tsx'
import { LoginPage } from '../pages/LoginPage.tsx'
import { NotFoundPage } from '../pages/NotFoundPage.tsx'
import { ProfilePage } from '../pages/ProfilePage.tsx'
import { RegisterPage } from '../pages/RegisterPage.tsx'

/**
 * Rotas da ARQ §7.3. Exportadas à parte para os testes montarem com `createMemoryRouter`.
 * `ProtectedRoute`/`PublicOnlyRoute` e o redirecionamento de `/` conforme a sessão entram na #12;
 * o `DashboardLayout`, na #14.
 */
export const routes: RouteObject[] = [
  { path: '/', element: <Navigate to="/dashboard" replace /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  { path: '/dashboard', element: <DashboardHomePage /> },
  { path: '/dashboard/profile', element: <ProfilePage /> },
  { path: '/dashboard/password', element: <ChangePasswordPage /> },
  { path: '*', element: <NotFoundPage /> },
]

export const router = createBrowserRouter(routes)
