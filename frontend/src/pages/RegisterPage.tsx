import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { FormField } from '../components/forms/FormField.tsx'
import { Button } from '../components/ui/Button.tsx'
import { Input } from '../components/ui/Input.tsx'
import { useAuth } from '../hooks/useAuth.ts'
import { AuthLayout } from '../layouts/AuthLayout.tsx'
import { registerSchema, type RegisterFormData } from '../schemas/authSchemas.ts'
import * as authService from '../services/authService.ts'
import { getApiError, getValidationErrors } from '../utils/apiError.ts'

/** Campos do formulário que podem receber erro vindo da API. */
const API_FIELDS = ['full_name', 'username', 'email', 'password', 'description'] as const
type ApiField = (typeof API_FIELDS)[number]

const isApiField = (field: string): field is ApiField =>
  (API_FIELDS as readonly string[]).includes(field)

export function RegisterPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: '',
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      description: '',
    },
  })

  async function onSubmit(data: RegisterFormData) {
    try {
      await authService.register({
        full_name: data.full_name,
        username: data.username,
        email: data.email,
        password: data.password,
        description: data.description.trim() || null,
      })
    } catch (error) {
      const { code, detail } = getApiError(error)
      const fieldErrors = getValidationErrors(error).filter((issue) => isApiField(issue.field))
      // 409 aparece no campo duplicado (ARQ §7.5); 422 em cada campo apontado pela API.
      if (code === 'EMAIL_ALREADY_EXISTS') setError('email', { message: detail })
      else if (code === 'USERNAME_ALREADY_EXISTS') setError('username', { message: detail })
      else if (fieldErrors.length > 0)
        fieldErrors.forEach((issue) =>
          setError(issue.field as ApiField, { message: issue.message }),
        )
      else toast.error('Não foi possível criar a conta. Tente novamente.')
      return
    }

    // Login automático após o cadastro.
    try {
      await login(data.username, data.password)
      toast.success('Conta criada com sucesso!')
      navigate('/dashboard', { replace: true })
    } catch {
      toast.info('Conta criada. Entre com seus dados.')
      navigate('/login', { replace: true })
    }
  }

  return (
    <AuthLayout title="Criar conta" subtitle="Preencha seus dados para se cadastrar.">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
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
        <Input
          label="Senha"
          type="password"
          autoComplete="new-password"
          error={errors.password?.message}
          {...register('password')}
        />
        <Input
          label="Confirmar senha"
          type="password"
          autoComplete="new-password"
          error={errors.confirmPassword?.message}
          {...register('confirmPassword')}
        />
        <FormField
          label="Descrição (opcional)"
          error={errors.description?.message}
          hint="Até 500 caracteres."
        >
          {(control) => (
            <textarea
              rows={3}
              className={`rounded-md border px-3 py-2 text-sm focus:outline-2 focus:outline-blue-600 ${errors.description ? 'border-red-500' : 'border-slate-300'}`}
              {...control}
              {...register('description')}
            />
          )}
        </FormField>
        <Button type="submit" isLoading={isSubmitting} className="mt-2">
          Criar conta
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        Já tem conta?{' '}
        <Link to="/login" className="font-medium text-blue-600 hover:underline">
          Entrar
        </Link>
      </p>
    </AuthLayout>
  )
}
