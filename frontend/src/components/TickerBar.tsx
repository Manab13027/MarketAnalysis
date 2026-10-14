import type { IndexQuote } from '../types'
function Item({ q }: { q: IndexQuote }) {
  const up = q.change_pct >= 0
  return (
    <span className="inline-flex items-center gap-1.5 border-r border-terminal-border/60 px-3 py-1 whitespace-nowrap transition-colors hover:bg-white/[0.03]">
      <span className="text-[9px] uppercase tracking-[0.2em] text-terminal-label">{q.name}{q.is_futures ? ' ◆' : ''}</span>
      <span className={`font-semibold text-xs ${up ? 'text-terminal-green' : 'text-terminal-red'}`}>
        {q.price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
      </span>
      <span className={`text-[10px] font-semibold ${up ? 'text-terminal-green' : 'text-terminal-red'}`}>
        {up ? '▲' : '▼'} {Math.abs(q.change_pct).toFixed(2)}%
      </span>
    </span>
  )
}
export function TickerBar({ indices }: { indices: IndexQuote[] }) {
  return (
    <div className="w-full overflow-x-auto border-b border-terminal-border/70 bg-terminal-bg/45 backdrop-blur-xl">
      <div className="flex h-8 min-w-max items-center">
        {indices.map(q => <Item key={q.symbol} q={q} />)}
      </div>
    </div>
  )
}
