// A API envia datas em UTC; a exibição segue o fuso de Fortaleza (ARQ §7.6).
const dateFormatter = new Intl.DateTimeFormat('pt-BR', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'America/Fortaleza',
})

/** Formata uma data ISO 8601 da API, ex.: `"2026-11-07T12:00:00Z"` → `"7 de novembro de 2026"`. */
export function formatDate(iso: string): string {
  return dateFormatter.format(new Date(iso))
}
