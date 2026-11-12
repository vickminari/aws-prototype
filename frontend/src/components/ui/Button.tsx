import type { ComponentProps } from 'react'
import { Spinner } from './Spinner.tsx'

type ButtonVariant = 'primary' | 'secondary' | 'danger'

interface ButtonProps extends ComponentProps<'button'> {
  variant?: ButtonVariant
  /** Mostra o spinner e desabilita o botão (ex.: envio de formulário). */
  isLoading?: boolean
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50',
  danger: 'bg-red-600 text-white hover:bg-red-700',
}

export function Button({
  variant = 'primary',
  isLoading = false,
  disabled,
  type = 'button',
  className = '',
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-60 ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {isLoading && <Spinner label="Enviando" />}
      {children}
    </button>
  )
}
