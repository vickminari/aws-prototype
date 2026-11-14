import { zodResolver } from '@hookform/resolvers/zod'
import { useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { PasswordRules } from '../components/forms/PasswordRules.tsx'
import { Button } from '../components/ui/Button.tsx'
import { Card } from '../components/ui/Card.tsx'
import { Input } from '../components/ui/Input.tsx'
import { changePasswordSchema, type ChangePasswordFormData } from '../schemas/authSchemas.ts'
import { changePassword } from '../services/userService.ts'
import { getApiError, getValidationErrors } from '../utils/apiError.ts'

const EMPTY_FORM: ChangePasswordFormData = {
  current_password: '',
  new_password: '',
  confirmPassword: '',
}

export function ChangePasswordPage() {
  const {
    register,
    control,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: EMPTY_FORM,
  })
  const newPassword = useWatch({ control, name: 'new_password' })

  async function onSubmit(data: ChangePasswordFormData) {
    try {
      await changePassword({
        current_password: data.current_password,
        new_password: data.new_password,
      })
      toast.success('Senha alterada com sucesso.')
      reset(EMPTY_FORM)
    } catch (error) {
      const { status, code, detail } = getApiError(error)
      if (status === 400) {
        setError('current_password', { message: 'Senha atual incorreta' })
      } else if (code === 'INVALID_PASSWORD') {
        setError('new_password', { message: detail ?? 'A nova senha é inválida' })
      } else if (status === 422) {
        for (const { field, message } of getValidationErrors(error)) {
          if (field === 'current_password' || field === 'new_password') {
            setError(field, { message })
          }
        }
      } else if (status !== 401) {
        // 401 já é tratado pelo api.ts: sessão expirada → /login
        toast.error('Não foi possível alterar a senha. Tente novamente.')
      }
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-900">Alterar senha</h1>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
          <Input
            label="Senha atual"
            type="password"
            autoComplete="current-password"
            error={errors.current_password?.message}
            {...register('current_password')}
          />
          <Input
            label="Nova senha"
            type="password"
            autoComplete="new-password"
            error={errors.new_password?.message}
            {...register('new_password')}
          />
          <PasswordRules password={newPassword} />
          <Input
            label="Confirmar nova senha"
            type="password"
            autoComplete="new-password"
            error={errors.confirmPassword?.message}
            {...register('confirmPassword')}
          />
          <Button type="submit" isLoading={isSubmitting} className="mt-2">
            Salvar nova senha
          </Button>
        </form>
      </Card>
    </div>
  )
}
