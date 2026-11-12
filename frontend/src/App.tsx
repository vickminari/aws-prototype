import { RouterProvider } from 'react-router'
import { router } from './routes/router.tsx'

/** Raiz da aplicação: providers globais (AuthContext e toasts entram na #12) + router. */
export function App() {
  return <RouterProvider router={router} />
}
