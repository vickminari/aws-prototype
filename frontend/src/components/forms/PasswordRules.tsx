import { PASSWORD_RULES } from '../../schemas/authSchemas.ts'

interface PasswordRulesProps {
  /** Senha digitada; cada regra atendida fica marcada. */
  password: string
}

/** Lista das regras de força da senha, atualizada enquanto o usuário digita. */
export function PasswordRules({ password }: PasswordRulesProps) {
  return (
    <ul aria-label="Regras da senha" className="flex flex-col gap-1 text-sm">
      {PASSWORD_RULES.map((rule) => {
        const isMet = rule.test(password)
        return (
          <li
            key={rule.label}
            className={`flex items-center gap-2 ${isMet ? 'text-green-700 dark:text-green-400' : 'text-slate-500 dark:text-slate-400'}`}
          >
            <span aria-hidden="true" className="w-4 text-center font-semibold">
              {isMet ? '✓' : '•'}
            </span>
            {rule.label}
            <span className="sr-only">{isMet ? '(atendida)' : '(pendente)'}</span>
          </li>
        )
      })}
    </ul>
  )
}
