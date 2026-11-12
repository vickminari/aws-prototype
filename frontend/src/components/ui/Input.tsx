import { useId, type ComponentProps } from 'react'

interface InputProps extends ComponentProps<'input'> {
  label: string
  /** Mensagem de erro do campo; marca o input como inválido. */
  error?: string
}

/** Campo com label associado; aceita `ref` (React 19) para react-hook-form. */
export function Input({ label, error, id, className = '', ...props }: InputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const errorId = `${inputId}-error`

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={inputId} className="text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className={`rounded-md border px-3 py-2 text-sm focus:outline-2 focus:outline-blue-600 ${error ? 'border-red-500' : 'border-slate-300'} ${className}`}
        {...props}
      />
      {error && (
        <p id={errorId} className="text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  )
}
