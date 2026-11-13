import type { ReactNode } from 'react'
import { Card } from '../components/ui/Card.tsx'

interface AuthLayoutProps {
  title: string
  subtitle?: string
  children: ReactNode
}

/** Moldura das telas de login e cadastro: card centralizado com título. */
export function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-8">
      <Card className="w-full max-w-md">
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
        <div className="mt-6">{children}</div>
      </Card>
    </main>
  )
}
