import type { IndexQuote } from '../types'
function Item({ q }: { q: IndexQuote }) {
  const up = q.change_pct >= 0
  return (
    <span className="inline-flex items-center gap-2 px-4 border-r border-terminal-border whitespace-nowrap">
      <span className="text-terminal-label text-xs">{q.name}{q.is_futures ? ' ◆' : ''}</span>
      <span className={`font-semibold text-sm ${up ? 'text-terminal-green' : 'text-terminal-red'}`}>
        {q.price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
      </span>
      <span className={`text-xs ${up ? 'text-terminal-green' : 'text-terminal-red'}`}>
        {up ? '▲' : '▼'} {Math.abs(q.change_pct).toFixed(2)}%
      </span>
    </span>
  )
}
export function TickerBar({ indices }: { indices: IndexQuote[] }) {
  return (
    <div className="w-full bg-terminal-panel border-b border-terminal-border overflow-x-auto">
      <div className="flex items-center h-10 min-w-max">
        {indices.map(q => <Item key={q.symbol} q={q} />)}
      </div>
    </div>
  )
}
