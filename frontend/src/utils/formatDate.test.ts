import { describe, expect, it } from 'vitest'
import { formatDate } from './formatDate.ts'

describe('formatDate', () => {
  it('formata a data por extenso em português', () => {
    expect(formatDate('2026-11-07T12:00:00Z')).toBe('7 de novembro de 2026')
  })

  it('usa o fuso de Fortaleza (UTC-3), não o UTC', () => {
    // 02:00 UTC do dia 8 ainda é 23:00 do dia 7 em Fortaleza
    expect(formatDate('2026-11-08T02:00:00Z')).toBe('7 de novembro de 2026')
  })
})
