import { useState } from 'react'
import type { IndexMovers, StockMover } from '../types'

const TABS = [
  { key: 'nifty50',   label: 'NIFTY 50' },
  { key: 'banknifty', label: 'BANK NIFTY' },
  { key: 'midcap',    label: 'MIDCAP' },
  { key: 'sensex',    label: 'SENSEX' },
]

function BarRow({ stock, maxPct, side }: { stock: StockMover; maxPct: number; side: 'gain' | 'loss' }) {
  const barPct = maxPct > 0 ? Math.min(Math.abs(stock.change_pct) / maxPct * 100, 100) : 0
  const isGain = side === 'gain'
  return (
    <div className="mb-2">
      <div className="flex justify-between items-baseline mb-0.5">
        <span className="text-terminal-text font-bold text-xs">{stock.symbol}</span>
        <span className={`text-xs font-bold ${isGain ? 'text-terminal-green' : 'text-terminal-red'}`}>
          {isGain ? '+' : ''}{stock.change_pct.toFixed(2)}%
        </span>
      </div>
      <div className="w-full bg-terminal-border rounded-full h-1.5 mb-0.5">
        <div
          className={`h-1.5 rounded-full ${isGain ? 'bg-terminal-green' : 'bg-terminal-red'} opacity-80`}
          style={{ width: `${barPct}%` }}
        />
      </div>
      <span className="text-terminal-muted text-xs">₹{stock.price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
    </div>
  )
}

export function MoversPanel({ movers }: { movers: Record<string, IndexMovers> | null | undefined }) {
  const [active, setActive] = useState('nifty50')
  const data = movers?.[active]

  const gainers = data?.gainers ?? []
  const losers  = data?.losers  ?? []
  const maxGain = Math.max(...gainers.map(s => Math.abs(s.change_pct)), 0.01)
  const maxLoss = Math.max(...losers.map(s => Math.abs(s.change_pct)), 0.01)
  const total   = gainers.length + losers.length
  const advPct  = total > 0 ? (gainers.length / total) * 100 : 50

  return (
    <div className="bg-terminal-panel border border-terminal-border rounded p-3 font-mono text-xs h-full flex flex-col overflow-hidden">
      {/* Header + Tabs */}
      <div className="flex items-center justify-between mb-2 border-b border-terminal-border pb-2">
        <span className="text-terminal-label tracking-widest uppercase text-xs">Movers</span>
        <div className="flex gap-1">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setActive(t.key)}
              className={`px-2 py-0.5 text-xs rounded transition-colors ${
                active === t.key
                  ? 'text-terminal-blue border-b border-terminal-blue'
                  : 'text-terminal-muted hover:text-terminal-label'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* A/D bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-terminal-green">{gainers.length} ↑ ADV</span>
          <span className="text-terminal-label">A/D Ratio</span>
          <span className="text-terminal-red">{losers.length} ↓ DEC</span>
        </div>
        <div className="w-full bg-terminal-border rounded-full h-2 flex overflow-hidden">
          <div className="h-2 bg-terminal-green opacity-70 transition-all duration-500" style={{ width: `${advPct}%` }} />
          <div className="h-2 bg-terminal-red opacity-70 flex-1" />
        </div>
      </div>

      {!data ? (
        <p className="text-terminal-muted flex-1 flex items-center justify-center">Fetching market data...</p>
      ) : (
        <div className="flex gap-3 flex-1 overflow-hidden">
          {/* Gainers */}
          <div className="flex-1 overflow-y-auto">
            <div className="text-terminal-green text-xs tracking-widest mb-2 uppercase">▲ Gainers</div>
            {gainers.length === 0
              ? <p className="text-terminal-muted text-xs">No data</p>
              : gainers.map(s => <BarRow key={s.symbol} stock={s} maxPct={maxGain} side="gain" />)
            }
          </div>
          {/* Divider */}
          <div className="w-px bg-terminal-border" />
          {/* Losers */}
          <div className="flex-1 overflow-y-auto">
            <div className="text-terminal-red text-xs tracking-widest mb-2 uppercase">▼ Losers</div>
            {losers.length === 0
              ? <p className="text-terminal-muted text-xs">No data</p>
              : losers.map(s => <BarRow key={s.symbol} stock={s} maxPct={maxLoss} side="loss" />)
            }
          </div>
        </div>
      )}

      {data && (
        <div className="text-terminal-muted text-xs mt-2 pt-1 border-t border-terminal-border">
          Updated: {new Date(data.updated_at).toLocaleTimeString('en-IN')}
        </div>
      )}
    </div>
  )
}
