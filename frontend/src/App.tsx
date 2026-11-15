import { RouterProvider } from 'react-router'
import { Toaster } from 'sonner'
import { AuthProvider } from './contexts/AuthContext.tsx'
import { useTheme } from './hooks/useTheme.ts'
import { router } from './routes/router.tsx'

/** Toasts no mesmo tema da página (#37). */
function ThemedToaster() {
  const { theme } = useTheme()
  return <Toaster richColors position="top-right" theme={theme} />
}

/** Raiz da aplicação: sessão (AuthProvider), toasts (sonner) e router. */
export function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
      <ThemedToaster />
    </AuthProvider>
  )
}
