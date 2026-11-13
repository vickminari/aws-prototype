import { RouterProvider } from 'react-router'
import { Toaster } from 'sonner'
import { AuthProvider } from './contexts/AuthContext.tsx'
import { router } from './routes/router.tsx'

/** Raiz da aplicação: sessão (AuthProvider), toasts (sonner) e router. */
export function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
      <Toaster richColors position="top-right" />
    </AuthProvider>
  )
}
