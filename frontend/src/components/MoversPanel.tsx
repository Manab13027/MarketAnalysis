import { useState } from 'react'
import type { IndexMovers, StockMover } from '../types'

const TABS = [
  { key: 'nifty50',   label: 'NIFTY 50' },
  { key: 'banknifty', label: 'BANK NIFTY' },
  { key: 'midcap',    label: 'MIDCAP' },
  { key: 'sensex',    label: 'SENSEX' },
]

function MoverRow({ stock, side }: { stock: StockMover; side: 'gainer' | 'loser' }) {
  const color = side === 'gainer' ? 'text-terminal-green' : 'text-terminal-red'
  const sign  = side === 'gainer' ? '+' : ''
  return (
    <div className="flex items-center justify-between py-1 border-b border-terminal-border/30 last:border-0">
      <div>
        <div className="text-terminal-text text-xs font-mono font-semibold">{stock.symbol}</div>
        <div className="text-terminal-muted text-[10px] font-mono">
          ₹{stock.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
      </div>
      <div className={`text-right ${color}`}>
        <div className="text-xs font-mono font-bold">{sign}{stock.change_pct.toFixed(2)}%</div>
        <div className="text-[10px] font-mono opacity-75">
          {sign}{stock.change.toFixed(2)}
        </div>
      </div>
    </div>
  )
}

export function MoversPanel({
  movers,
}: {
  movers: Record<string, IndexMovers> | null | undefined
}) {
  const [activeTab, setActiveTab] = useState<string>('nifty50')
  const data: IndexMovers | undefined = movers?.[activeTab]

  const updatedAt = data?.updated_at
    ? new Date(data.updated_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null

  return (
    <div className="bg-terminal-panel border border-terminal-border rounded flex flex-col h-full font-mono overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-terminal-border">
        <span className="text-terminal-label text-[10px] tracking-widest uppercase">Gainers / Losers</span>
        {updatedAt && (
          <span className="text-terminal-muted text-[10px]">{updatedAt}</span>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-terminal-border">
        {TABS.map(tab => {
          const active = tab.key === activeTab
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 text-[10px] py-1 tracking-wide transition-colors ${
                active
                  ? 'text-terminal-blue border-b-2 border-terminal-blue bg-terminal-blue/5'
                  : 'text-terminal-muted hover:text-terminal-label'
              }`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto min-h-0">
        {!movers ? (
          <div className="flex items-center justify-center h-full text-terminal-muted text-xs">
            Fetching...
          </div>
        ) : !data || (data.gainers.length === 0 && data.losers.length === 0) ? (
          <div className="flex items-center justify-center h-full text-terminal-muted text-xs">
            No data available
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-0 h-full">
            {/* Gainers */}
            <div className="border-r border-terminal-border/50 px-2 py-1">
              <div className="text-terminal-green text-[10px] font-bold tracking-widest mb-1 uppercase">
                ▲ Gainers
              </div>
              {data.gainers.map(s => (
                <MoverRow key={s.symbol} stock={s} side="gainer" />
              ))}
            </div>

            {/* Losers */}
            <div className="px-2 py-1">
              <div className="text-terminal-red text-[10px] font-bold tracking-widest mb-1 uppercase">
                ▼ Losers
              </div>
              {data.losers.map(s => (
                <MoverRow key={s.symbol} stock={s} side="loser" />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
