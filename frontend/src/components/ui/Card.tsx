import type { ComponentProps } from 'react'

export function Card({ className = '', ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={`rounded-lg border border-slate-200 bg-white p-6 shadow-sm ${className}`}
      {...props}
    />
  )
}
