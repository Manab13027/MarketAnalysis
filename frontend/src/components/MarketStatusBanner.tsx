import type { MarketStatus } from '../types'
export function MarketStatusBanner({ status }: { status: MarketStatus }) {
  if (status.status === 'open') return null
  const cls = {
    futures_mode: 'border-amber-400/40 bg-amber-500/10 text-amber-200',
    pre_open:     'border-cyan-400/40 bg-cyan-500/10 text-cyan-200',
    closed:       'border-slate-500/40 bg-slate-500/10 text-slate-200',
    holiday:      'border-violet-400/40 bg-violet-500/10 text-violet-200',
  }[status.status] ?? 'border-slate-500/40 bg-slate-500/10 text-slate-200'
  return (
    <div className={`flex items-center justify-between gap-3 border-b border-terminal-border/70 px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.32em] ${cls}`}>
      <span className="inline-flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-current" />
        {status.status.replace('_', ' ')}
      </span>
      <span className="truncate text-right tracking-normal opacity-90">
        {status.message ?? 'Market state updated'}
      </span>
    </div>
  )
}
