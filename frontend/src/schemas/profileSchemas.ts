import { z } from 'zod'
import { userFieldRules } from './authSchemas.ts'

/** Edição do perfil: espelha `UserUpdate` (backend/app/schemas/user.py), com as regras do cadastro. */
export const profileSchema = z.object(userFieldRules)

export type ProfileFormData = z.infer<typeof profileSchema>

/** Mesmas regras do backend (#11, ARQ §5.7): JPEG, PNG ou WebP de até 2 MB. */
export const AVATAR_ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const AVATAR_MAX_BYTES = 2 * 1024 * 1024

/**
 * Valida a imagem no navegador antes do envio. Retorna a mensagem de erro, ou `null`
 * se a imagem for aceita. O backend confere de novo pela assinatura real do arquivo.
 */
export function validateAvatarFile(file: File): string | null {
  if (!AVATAR_ACCEPTED_TYPES.includes(file.type)) return 'Use uma imagem JPEG, PNG ou WebP.'
  if (file.size > AVATAR_MAX_BYTES) return 'A imagem deve ter no máximo 2 MB.'
  return null
}
