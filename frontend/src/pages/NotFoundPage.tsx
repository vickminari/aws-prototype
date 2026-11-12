import { Link } from 'react-router'
import { PlaceholderPage } from '../components/PlaceholderPage.tsx'

export function NotFoundPage() {
  return (
    <PlaceholderPage title="Página não encontrada" issue={14}>
      <Link to="/" className="mt-4 inline-block text-sm text-blue-600 hover:underline">
        Voltar ao início
      </Link>
    </PlaceholderPage>
  )
}
