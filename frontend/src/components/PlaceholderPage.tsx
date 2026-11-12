import type { ReactNode } from 'react'
import { Card } from './ui/Card.tsx'

interface PlaceholderPageProps {
  title: string
  issue: number
  children?: ReactNode
}

/** Página provisória; cada rota é substituída pela issue indicada. */
export function PlaceholderPage({ title, issue, children }: PlaceholderPageProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-md text-center">
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        <p className="mt-2 text-sm text-slate-500">Em construção (issue #{issue}).</p>
        {children}
      </Card>
    </main>
  )
}
