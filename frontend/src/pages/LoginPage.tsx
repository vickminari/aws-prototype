import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Button } from '../components/ui/Button.tsx'
import { Input } from '../components/ui/Input.tsx'
import { useAuth } from '../hooks/useAuth.ts'
import { AuthLayout } from '../layouts/AuthLayout.tsx'
import { loginSchema, type LoginFormData } from '../schemas/authSchemas.ts'
import { getApiError } from '../utils/apiError.ts'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  })

  async function onSubmit(data: LoginFormData) {
    setFormError(null)
    try {
      await login(data.username, data.password)
      navigate('/dashboard', { replace: true })
    } catch (error) {
      // Mensagem genérica: não revela se o usuário existe (ARQ §5.6).
      if (getApiError(error).status === 401) setFormError('Usuário ou senha inválidos')
      else toast.error('Não foi possível entrar. Tente novamente.')
    }
  }

  return (
    <AuthLayout title="Entrar" subtitle="Acesse sua conta para continuar.">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        {formError && (
          <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {formError}
          </p>
        )}
        <Input
          label="Usuário ou email"
          autoComplete="username"
          error={errors.username?.message}
          {...register('username')}
        />
        <Input
          label="Senha"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register('password')}
        />
        <Button type="submit" isLoading={isSubmitting} className="mt-2">
          Entrar
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        Não tem conta?{' '}
        <Link to="/register" className="font-medium text-blue-600 hover:underline">
          Cadastre-se
        </Link>
      </p>
    </AuthLayout>
  )
}
