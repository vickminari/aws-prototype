import { AvatarUploader } from '../components/profile/AvatarUploader.tsx'
import { ProfileForm } from '../components/profile/ProfileForm.tsx'
import { useAuth } from '../hooks/useAuth.ts'

/** Meu perfil (ARQ §7.3): foto de perfil e edição dos dados. */
export function ProfilePage() {
  const { user } = useAuth()
  // O ProtectedRoute garante o usuário; a checagem só estreita o tipo
  if (!user) return null

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-900">Meu perfil</h1>
      <AvatarUploader user={user} />
      <ProfileForm user={user} />
    </div>
  )
}
