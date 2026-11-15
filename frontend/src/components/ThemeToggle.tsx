import type { MouseEvent } from 'react'
import { useTheme } from '../hooks/useTheme.ts'

/**
 * Interruptor (switch) de tema claro/escuro (#37): a bolinha desliza para a direita no
 * modo escuro. O novo tema se espalha a partir do centro do switch.
 *
 * O botão usa `relative` (para a bolinha); para fixá-lo num canto, envolva-o num elemento
 * com `fixed`, em vez de passar `fixed` no `className` (as duas classes conflitam).
 */
export function ThemeToggle({ className = '' }: { className?: string }) {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  function handleClick(event: MouseEvent<HTMLButtonElement>) {
    const rect = event.currentTarget.getBoundingClientRect()
    toggleTheme({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })
  }

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label="Modo escuro"
      title={isDark ? 'Mudar para o modo claro' : 'Mudar para o modo escuro'}
      onClick={handleClick}
      className={`relative inline-flex h-8 w-14 shrink-0 items-center rounded-full border transition-colors duration-500 ease-in-out focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${
        isDark ? 'border-slate-600 bg-slate-700' : 'border-slate-300 bg-slate-200'
      } ${className}`}
    >
      <span
        aria-hidden="true"
        className={`absolute left-1 inline-flex size-6 items-center justify-center rounded-full shadow-md transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${
          isDark
            ? 'translate-x-6 bg-slate-900 text-blue-300'
            : 'translate-x-0 bg-white text-amber-500'
        }`}
      >
        <svg viewBox="0 0 24 24" className="size-4" fill="none">
          {isDark ? (
            // Lua: modo escuro ligado
            <path
              d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79Z"
              fill="currentColor"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          ) : (
            // Sol: modo claro
            <g stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="4" fill="currentColor" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
            </g>
          )}
        </svg>
      </span>
    </button>
  )
}
