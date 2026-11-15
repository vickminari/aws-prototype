import { useSyncExternalStore } from 'react'
import { flushSync } from 'react-dom'

export type Theme = 'light' | 'dark'

/** Ponto da tela de onde a transição do tema se espalha (centro do switch). */
export interface ThemeOrigin {
  x: number
  y: number
}

/** Mesma chave lida pelo script do index.html. Preferência visual, não é dado sensível. */
export const THEME_STORAGE_KEY = 'proto1.theme'

/** Duração do fade das cores quando o navegador não tem View Transitions (igual ao index.css). */
const FADE_MS = 500

const listeners = new Set<() => void>()

/** O tema atual é a classe `.dark` no `<html>`, aplicada pelo index.html antes do React. */
function getTheme(): Theme {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function prefersReducedMotion(): boolean {
  return (
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/** Aplica o tema no `<html>`, lembra a escolha e atualiza na hora quem usa `useTheme()`. */
function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // Navegador sem localStorage (ex.: modo privado): o tema vale até recarregar.
  }
  // Síncrono para a View Transition capturar a tela já com o switch na nova posição.
  flushSync(() => listeners.forEach((listener) => listener()))
}

/**
 * Troca o tema com transição:
 * - com View Transitions (Chrome, Edge, Safari): o novo tema se espalha em círculo a partir de `origin`;
 * - sem suporte: as cores mudam com fade de 0,5 s;
 * - com "reduzir movimento" ativado no sistema: troca instantânea (acessibilidade).
 */
export function setTheme(theme: Theme, origin?: ThemeOrigin): void {
  const root = document.documentElement

  if (prefersReducedMotion()) {
    applyTheme(theme)
    return
  }

  if (typeof document.startViewTransition === 'function') {
    const x = origin?.x ?? window.innerWidth / 2
    const y = origin?.y ?? window.innerHeight / 2
    // Raio até o canto mais distante, para o círculo cobrir a tela inteira.
    const radius = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y),
    )
    root.style.setProperty('--theme-x', `${x}px`)
    root.style.setProperty('--theme-y', `${y}px`)
    root.style.setProperty('--theme-r', `${radius}px`)
    document.startViewTransition(() => applyTheme(theme))
    return
  }

  root.classList.add('theme-fade')
  applyTheme(theme)
  window.setTimeout(() => root.classList.remove('theme-fade'), FADE_MS)
}

/**
 * Tema claro/escuro (#37). Não precisa de Provider: o estado vive no `<html>`, então
 * qualquer componente (e os testes) pode usar o hook sem montar nada a mais.
 */
export function useTheme(): { theme: Theme; toggleTheme: (origin?: ThemeOrigin) => void } {
  const theme = useSyncExternalStore(subscribe, getTheme, () => 'light' as Theme)
  return {
    theme,
    toggleTheme: (origin) => setTheme(theme === 'dark' ? 'light' : 'dark', origin),
  }
}
