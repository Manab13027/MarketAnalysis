import type { MarketStatus } from '../types'
export function MarketStatusBanner({ status }: { status: MarketStatus }) {
  if (status.status === 'open') return null
  const cls = {
    futures_mode: 'bg-amber-900/60 text-amber-300 border-amber-600',
    pre_open:     'bg-blue-900/60 text-blue-300 border-blue-600',
    closed:       'bg-terminal-panel text-terminal-muted border-terminal-border',
    holiday:      'bg-purple-900/60 text-purple-300 border-purple-600',
  }[status.status] ?? 'bg-terminal-panel text-terminal-muted border-terminal-border'
  return (
    <div className={`w-full text-center text-xs py-1 border-b font-semibold tracking-widest uppercase ${cls}`}>
      {status.message ?? status.status.replace('_', ' ')}
    </div>
  )
}
