import { z } from 'zod'

/** Login: aceita username ou email no mesmo campo (ARQ §5.5). */
export const loginSchema = z.object({
  username: z.string().trim().min(1, 'Informe o usuário ou email'),
  password: z.string().min(1, 'Informe a senha'),
})

export type LoginFormData = z.infer<typeof loginSchema>

/** Mesmas regras de força do backend: mín. 8 caracteres, ao menos 1 letra e 1 número. */
const passwordRule = z
  .string()
  .min(8, 'A senha deve ter no mínimo 8 caracteres')
  .regex(/\p{L}/u, 'A senha deve conter ao menos uma letra')
  .regex(/\d/, 'A senha deve conter ao menos um número')

/** Cadastro: espelha `UserCreate` (backend/app/schemas/user.py) + confirmação de senha. */
export const registerSchema = z
  .object({
    full_name: z
      .string()
      .trim()
      .min(1, 'Informe o nome completo')
      .max(120, 'Use no máximo 120 caracteres'),
    username: z
      .string()
      .trim()
      .min(3, 'Use no mínimo 3 caracteres')
      .max(30, 'Use no máximo 30 caracteres')
      .regex(/^[a-zA-Z0-9_.]+$/, 'Use apenas letras, números, ponto ou sublinhado'),
    email: z
      .string()
      .trim()
      .min(1, 'Informe o email')
      .max(254, 'Use no máximo 254 caracteres')
      .pipe(z.email('Email inválido')),
    password: passwordRule,
    confirmPassword: z.string().min(1, 'Confirme a senha'),
    description: z.string().max(500, 'Use no máximo 500 caracteres'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'As senhas não conferem',
    path: ['confirmPassword'],
  })

export type RegisterFormData = z.infer<typeof registerSchema>
