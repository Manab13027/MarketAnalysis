import type { FuturesContract } from '../types'

function FutCard({ c }: { c: FuturesContract }) {
  const up  = c.change_pct >= 0
  const clr = up ? 'text-terminal-green' : 'text-terminal-red'
  return (
    <div className={`flex min-w-[140px] flex-col justify-center gap-0.5 border-r border-terminal-border/60 px-3 py-1 whitespace-nowrap ${c.is_gift ? 'bg-sky-500/8' : 'bg-white/[0.02]'}`}>
      <div className="flex items-center gap-1.5">
        {c.is_gift && <span className="text-sky-400 text-[9px] font-bold tracking-widest">GIFT</span>}
        <span className="text-[9px] text-terminal-muted uppercase tracking-[0.2em]">{c.label}</span>
        {c.is_prev_close && (
          <span className="text-[8px] text-terminal-amber border border-terminal-amber/40 rounded px-0.5 leading-tight">PREV</span>
        )}
      </div>
      <div className="flex items-baseline gap-2">
        <span className={`text-[11px] font-mono font-bold ${clr}`}>
          {c.price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
        </span>
        <span className={`text-[9px] font-semibold ${clr}`}>
          {up ? '▲' : '▼'}{Math.abs(c.change_pct).toFixed(2)}%
          <span className="text-terminal-muted font-normal ml-1">({up ? '+' : ''}{c.change.toFixed(0)})</span>
        </span>
      </div>
    </div>
  )
}

export function NiftyFuturesBar({ futures }: { futures: FuturesContract[] | null | undefined }) {
  const hasFutures = futures && futures.length > 0
  const allPrev = hasFutures && futures.every(c => c.is_prev_close)
  return (
    <div className="w-full overflow-x-auto border-b border-terminal-border/70 bg-terminal-bg/45 backdrop-blur-xl flex-shrink-0">
      <div className="flex items-stretch min-w-max">
        <div className="flex flex-col justify-center px-4 border-r border-terminal-border/60 bg-white/[0.02] min-w-[72px]">
          <span className="text-[10px] text-terminal-muted font-mono tracking-[0.24em] uppercase">Futures</span>
          {allPrev && (
            <span className="text-[8px] text-terminal-amber mt-0.5">prev close</span>
          )}
        </div>
        {hasFutures
          ? futures.map(c => <FutCard key={c.label} c={c} />)
          : (
            <div className="flex items-center px-4 text-[10px] text-terminal-muted font-mono">
              <span className="text-terminal-amber">⏸ Loading...</span>
            </div>
          )
        }
        {allPrev && (
          <div className="flex items-center px-3 text-[9px] text-terminal-muted/60 font-mono italic">
            NSE live futures require a broker API (Dhan/Zerodha)
          </div>
        )}
      </div>
    </div>
  )
}
