import type { ReactNode } from 'react'
import { ThemeToggle } from '../components/ThemeToggle.tsx'
import { Card } from '../components/ui/Card.tsx'

interface AuthLayoutProps {
  title: string
  subtitle?: string
  children: ReactNode
}

/** Moldura das telas de login e cadastro: card centralizado com título. */
export function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950 px-4 py-8">
      <div className="fixed top-4 right-4 z-10">
        <ThemeToggle />
      </div>
      <Card className="w-full max-w-md">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        <div className="mt-6">{children}</div>
      </Card>
    </main>
  )
}
