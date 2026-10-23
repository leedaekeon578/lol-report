import type { ReactNode } from 'react'

type Props = {
  kind: 'loading' | 'info' | 'empty' | 'error'
  title?: string
  children?: ReactNode
}

function Notice({ kind, title, children }: Props) {
  return (
    <div className={`notice notice-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      {title ? <strong>{title}</strong> : null}
      {children ? <p>{children}</p> : null}
    </div>
  )
}

export default Notice
