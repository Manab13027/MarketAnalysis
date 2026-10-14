import { useState } from 'react'
import type { IndexMovers, StockMover } from '../types'

const TABS = [
  { key: 'nifty50',   label: 'N50' },
  { key: 'banknifty', label: 'BANK' },
  { key: 'midcap',    label: 'MID' },
  { key: 'sensex',    label: 'SENSEX' },
]

function StockRow({ stock, maxPct, side }: { stock: StockMover; maxPct: number; side: 'gain' | 'loss' }) {
  const barPct = maxPct > 0 ? Math.min(Math.abs(stock.change_pct) / maxPct * 100, 100) : 0
  const isGain = side === 'gain'
  return (
    <div className="flex items-center gap-2 py-0.5 px-1 rounded hover:bg-white/[0.03]">
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-baseline">
          <span className="text-[10px] font-bold text-terminal-text truncate">{stock.symbol}</span>
          <span className={`text-[10px] font-bold shrink-0 ml-1 ${isGain ? 'text-terminal-green' : 'text-terminal-red'}`}>
            {isGain ? '+' : ''}{stock.change_pct.toFixed(2)}%
          </span>
        </div>
        <div className="w-full bg-terminal-border/60 rounded-full h-0.5 mt-0.5 overflow-hidden">
          <div
            className={`h-0.5 rounded-full ${isGain ? 'bg-terminal-green' : 'bg-terminal-red'}`}
            style={{ width: `${barPct}%` }}
          />
        </div>
      </div>
    </div>
  )
}

export function MoversPanel({ movers }: { movers: Record<string, IndexMovers> | null | undefined }) {
  const [active, setActive] = useState('nifty50')
  const data    = movers?.[active]
  const gainers = data?.gainers ?? []
  const losers  = data?.losers  ?? []
  const maxGain = Math.max(...gainers.map(s => Math.abs(s.change_pct)), 0.01)
  const maxLoss = Math.max(...losers.map(s => Math.abs(s.change_pct)), 0.01)
  const total   = gainers.length + losers.length
  const advPct  = total > 0 ? (gainers.length / total) * 100 : 50

  return (
    <div className="h-full flex flex-col bg-terminal-panel border border-terminal-border rounded overflow-hidden">

      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-terminal-border shrink-0">
        <span className="text-[10px] font-mono uppercase tracking-widest text-terminal-muted">Movers</span>
        <div className="flex gap-1">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setActive(t.key)}
              className={`px-2 py-0.5 rounded text-[9px] font-mono uppercase tracking-wide transition-colors ${
                active === t.key
                  ? 'bg-terminal-green/20 text-terminal-green border border-terminal-green/40'
                  : 'text-terminal-muted hover:text-terminal-text border border-transparent'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* A/D bar */}
      <div className="px-3 py-1.5 border-b border-terminal-border/40 shrink-0">
        <div className="flex justify-between text-[9px] font-mono mb-1">
          <span className="text-terminal-green">▲ {gainers.length} ADV</span>
          <span className="text-terminal-muted">A/D</span>
          <span className="text-terminal-red">{losers.length} DEC ▼</span>
        </div>
        <div className="w-full bg-terminal-border rounded-full h-1 flex overflow-hidden">
          <div className="h-1 bg-terminal-green/70 transition-all duration-500" style={{ width: `${advPct}%` }} />
          <div className="h-1 bg-terminal-red/70 flex-1" />
        </div>
      </div>

      {/* Gainers / Losers */}
      {!data ? (
        <div className="flex-1 flex items-center justify-center text-[10px] text-terminal-muted font-mono">
          Fetching…
        </div>
      ) : (
        <div className="flex flex-1 min-h-0 overflow-hidden gap-0">
          {/* Gainers */}
          <div className="flex-1 flex flex-col min-h-0 border-r border-terminal-border/40">
            <div className="text-[9px] text-terminal-green font-mono tracking-widest px-2 py-1 shrink-0 border-b border-terminal-border/30">
              ▲ GAINERS
            </div>
            <div className="flex-1 overflow-y-auto min-h-0 px-1 py-1 scrollbar-hide">
              {gainers.length === 0
                ? <p className="text-[9px] text-terminal-muted px-2">No data</p>
                : gainers.map(s => <StockRow key={s.symbol} stock={s} maxPct={maxGain} side="gain" />)
              }
            </div>
          </div>

          {/* Losers */}
          <div className="flex-1 flex flex-col min-h-0">
            <div className="text-[9px] text-terminal-red font-mono tracking-widest px-2 py-1 shrink-0 border-b border-terminal-border/30">
              ▼ LOSERS
            </div>
            <div className="flex-1 overflow-y-auto min-h-0 px-1 py-1 scrollbar-hide">
              {losers.length === 0
                ? <p className="text-[9px] text-terminal-muted px-2">No data</p>
                : losers.map(s => <StockRow key={s.symbol} stock={s} maxPct={maxLoss} side="loss" />)
              }
            </div>
          </div>
        </div>
      )}

      {/* Footer timestamp */}
      {data && (
        <div className="px-3 py-1 border-t border-terminal-border/40 text-[8px] text-terminal-muted/60 font-mono shrink-0">
          {new Date(data.updated_at).toLocaleTimeString('en-IN')}
        </div>
      )}
    </div>
  )
}
