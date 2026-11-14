import { zodResolver } from '@hookform/resolvers/zod'
import { useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { useAuth } from '../../hooks/useAuth.ts'
import { DESCRIPTION_MAX_LENGTH } from '../../schemas/authSchemas.ts'
import { profileSchema, type ProfileFormData } from '../../schemas/profileSchemas.ts'
import { updateMe } from '../../services/userService.ts'
import type { UserProfileRead, UserUpdate } from '../../types/user.ts'
import { getApiError, getValidationErrors } from '../../utils/apiError.ts'
import { FormField } from '../forms/FormField.tsx'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { Input } from '../ui/Input.tsx'

const FIELDS = ['full_name', 'username', 'email', 'description'] as const

function toFormValues(user: UserProfileRead): ProfileFormData {
  return {
    full_name: user.full_name,
    username: user.username,
    email: user.email,
    description: user.description ?? '',
  }
}

/** Monta o `PATCH` só com o que mudou; descrição vazia vira `null` (apaga no backend). */
function getChanges(data: ProfileFormData, user: UserProfileRead): UserUpdate {
  const changes: UserUpdate = {}
  if (data.full_name !== user.full_name) changes.full_name = data.full_name
  if (data.username !== user.username) changes.username = data.username
  if (data.email !== user.email) changes.email = data.email
  const description = data.description.trim() || null
  if (description !== (user.description ?? null)) changes.description = description
  return changes
}

/**
 * Dados do perfil pré-preenchidos; envia só os campos alterados (`PATCH /api/users/me`).
 * 409 e 422 aparecem no campo; após salvar, recarrega o usuário com `refreshUser()`.
 */
export function ProfileForm({ user }: { user: UserProfileRead }) {
  const { refreshUser } = useAuth()
  const {
    register,
    control,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: toFormValues(user),
  })
  const description = useWatch({ control, name: 'description' })

  async function onSubmit(data: ProfileFormData) {
    const changes = getChanges(data, user)
    if (Object.keys(changes).length === 0) {
      reset(toFormValues(user))
      return
    }

    try {
      const updated = await updateMe(changes)
      await refreshUser()
      reset(toFormValues(updated))
      toast.success('Perfil atualizado.')
    } catch (error) {
      const { status, code, detail } = getApiError(error)
      if (code === 'EMAIL_ALREADY_EXISTS') setError('email', { message: detail })
      else if (code === 'USERNAME_ALREADY_EXISTS') setError('username', { message: detail })
      else if (status === 422) {
        for (const { field, message } of getValidationErrors(error)) {
          const formField = FIELDS.find((name) => name === field)
          if (formField) setError(formField, { message })
        }
      } else if (status !== 401) {
        // 401 já é tratado pelo api.ts: sessão expirada → /login
        toast.error('Não foi possível salvar o perfil. Tente novamente.')
      }
    }
  }

  return (
    <Card>
      <h2 className="text-lg font-semibold text-slate-900">Dados do perfil</h2>
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-4 flex flex-col gap-4">
        <Input
          label="Nome completo"
          autoComplete="name"
          error={errors.full_name?.message}
          {...register('full_name')}
        />
        <Input
          label="Nome de usuário"
          autoComplete="username"
          error={errors.username?.message}
          {...register('username')}
        />
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register('email')}
        />
        <FormField
          label="Descrição"
          error={errors.description?.message}
          hint={`${description.length}/${DESCRIPTION_MAX_LENGTH} caracteres`}
        >
          {(controlProps) => (
            <textarea
              rows={4}
              className={`rounded-md border px-3 py-2 text-sm focus:outline-2 focus:outline-blue-600 ${errors.description ? 'border-red-500' : 'border-slate-300'}`}
              {...controlProps}
              {...register('description')}
            />
          )}
        </FormField>
        <Button type="submit" isLoading={isSubmitting} disabled={!isDirty} className="mt-2">
          Salvar alterações
        </Button>
      </form>
    </Card>
  )
}
