import { useId, type ReactNode } from 'react'

/** Atributos de acessibilidade que o `FormField` passa para o controle. */
export interface FormFieldControlProps {
  id: string
  'aria-invalid'?: true
  'aria-describedby'?: string
}

interface FormFieldProps {
  label: string
  /** Mensagem de erro; marca o controle como inválido. */
  error?: string
  /** Texto de ajuda exibido abaixo do controle quando não há erro. */
  hint?: string
  /** Recebe os atributos e renderiza o controle (ex.: `<textarea>`). */
  children: (control: FormFieldControlProps) => ReactNode
}

/**
 * Label, ajuda e erro acessíveis para controles que não são o `Input` (ex.: textarea).
 * Para campos de texto simples, use `components/ui/Input`.
 */
export function FormField({ label, error, hint, children }: FormFieldProps) {
  const id = useId()
  const messageId = `${id}-message`
  const message = error ?? hint

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-slate-700">
        {label}
      </label>
      {children({
        id,
        'aria-invalid': error ? true : undefined,
        'aria-describedby': message ? messageId : undefined,
      })}
      {message && (
        <p id={messageId} className={`text-sm ${error ? 'text-red-600' : 'text-slate-500'}`}>
          {message}
        </p>
      )}
    </div>
  )
}
