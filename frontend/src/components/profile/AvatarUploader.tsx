import { useEffect, useId, useRef, useState, type ChangeEvent } from 'react'
import { toast } from 'sonner'
import { useAuth } from '../../hooks/useAuth.ts'
import { AVATAR_ACCEPTED_TYPES, validateAvatarFile } from '../../schemas/profileSchemas.ts'
import { deleteAvatar, uploadAvatar } from '../../services/userService.ts'
import type { UserProfileRead } from '../../types/user.ts'
import { getApiError } from '../../utils/apiError.ts'
import { Avatar } from '../ui/Avatar.tsx'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'

/**
 * Foto de perfil: escolha com preview, validação de tipo e tamanho no navegador,
 * envio e remoção (ARQ §7.6). Após salvar, recarrega o usuário com `refreshUser()`.
 */
export function AvatarUploader({ user }: { user: UserProfileRead }) {
  const { refreshUser } = useAuth()
  const inputRef = useRef<HTMLInputElement>(null)
  const errorId = useId()
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<'upload' | 'delete' | null>(null)

  // Libera a memória do preview quando ele é trocado ou a página fecha.
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  function clearSelection() {
    setFile(null)
    setPreviewUrl(null)
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0]
    // Limpa o input para permitir escolher o mesmo arquivo de novo.
    event.target.value = ''
    if (!selected) return

    const validationError = validateAvatarFile(selected)
    setError(validationError)
    if (validationError) {
      clearSelection()
      return
    }
    setFile(selected)
    setPreviewUrl(URL.createObjectURL(selected))
  }

  async function run(action: 'upload' | 'delete') {
    if (action === 'upload' && !file) return
    setPending(action)
    setError(null)
    try {
      if (action === 'upload') await uploadAvatar(file!)
      else await deleteAvatar()
      await refreshUser()
      clearSelection()
      toast.success(action === 'upload' ? 'Foto atualizada.' : 'Foto removida.')
    } catch (err) {
      const { status, code, detail } = getApiError(err)
      if (code === 'INVALID_IMAGE') setError(detail ?? 'Imagem inválida.')
      else if (status !== 401) {
        // 401 já é tratado pelo api.ts: sessão expirada → /login
        toast.error(
          action === 'upload'
            ? 'Não foi possível enviar a foto. Tente novamente.'
            : 'Não foi possível remover a foto. Tente novamente.',
        )
      }
    } finally {
      setPending(null)
    }
  }

  return (
    <Card>
      <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Foto de perfil</h2>
      <div className="mt-4 flex flex-col items-center gap-4 sm:flex-row sm:items-start">
        <Avatar name={user.full_name} src={previewUrl ?? user.profile_image_url} size="lg" />

        <div className="flex flex-col items-center gap-3 sm:items-start">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {file ? `Pré-visualização: ${file.name}` : 'JPEG, PNG ou WebP, até 2 MB.'}
          </p>

          <input
            ref={inputRef}
            type="file"
            accept={AVATAR_ACCEPTED_TYPES.join(',')}
            aria-label="Arquivo da foto de perfil"
            aria-describedby={error ? errorId : undefined}
            className="sr-only"
            tabIndex={-1}
            onChange={handleFileChange}
          />

          <div className="flex flex-wrap justify-center gap-2">
            {file ? (
              <>
                <Button isLoading={pending === 'upload'} onClick={() => run('upload')}>
                  Enviar foto
                </Button>
                <Button variant="secondary" disabled={pending !== null} onClick={clearSelection}>
                  Cancelar
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="secondary"
                  disabled={pending !== null}
                  onClick={() => inputRef.current?.click()}
                >
                  Escolher foto
                </Button>
                {user.profile_image_url && (
                  <Button
                    variant="danger"
                    isLoading={pending === 'delete'}
                    disabled={pending !== null}
                    onClick={() => run('delete')}
                  >
                    Remover foto
                  </Button>
                )}
              </>
            )}
          </div>

          {error && (
            <p id={errorId} role="alert" className="text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          )}
        </div>
      </div>
    </Card>
  )
}
