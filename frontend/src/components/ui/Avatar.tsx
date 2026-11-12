type AvatarSize = 'sm' | 'md' | 'lg'

interface AvatarProps {
  /** Nome do usuário: texto alternativo e origem das iniciais. */
  name: string
  /** URL da foto; sem ela, mostra as iniciais. */
  src?: string | null
  size?: AvatarSize
  className?: string
}

const sizeClasses: Record<AvatarSize, string> = {
  sm: 'size-8 text-xs',
  md: 'size-12 text-base',
  lg: 'size-24 text-2xl',
}

/** Até duas iniciais: primeira e última palavra do nome. */
function getInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  if (words.length === 0) return '?'
  const first = words[0][0]
  const last = words.length > 1 ? words[words.length - 1][0] : ''
  return (first + last).toUpperCase()
}

export function Avatar({ name, src, size = 'md', className = '' }: AvatarProps) {
  const base = `inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full ${sizeClasses[size]} ${className}`

  if (src) {
    return <img src={src} alt={name} className={`${base} object-cover`} />
  }

  return (
    <span
      role="img"
      aria-label={name}
      className={`${base} bg-blue-100 font-semibold text-blue-700`}
    >
      {getInitials(name)}
    </span>
  )
}
