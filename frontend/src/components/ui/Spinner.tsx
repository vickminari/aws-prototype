interface SpinnerProps {
  className?: string
  /** Texto lido por leitores de tela. */
  label?: string
}

export function Spinner({ className = '', label = 'Carregando' }: SpinnerProps) {
  return (
    <span role="status" className={`inline-flex items-center ${className}`}>
      <span
        aria-hidden="true"
        className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
      />
      <span className="sr-only">{label}</span>
    </span>
  )
}
