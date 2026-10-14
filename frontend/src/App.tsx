import { useWebSocket } from './hooks/useWebSocket'
import { MarketStatusBanner }  from './components/MarketStatusBanner'
import { TickerBar }           from './components/TickerBar'
import { MLPredictionPanel }   from './components/MLPredictionPanel'
import { LLMAnalysisPanel }    from './components/LLMAnalysisPanel'
import { NewsFeed }            from './components/NewsFeed'
import { MarketMoversStrip }   from './components/MarketMoversStrip'
import { MoversPanel }         from './components/MoversPanel'
import { NiftyFuturesBar }     from './components/NiftyFuturesBar'
import { FIIDIIBar }           from './components/FIIDIIBar'
import { GlobalMarketsPanel }  from './components/GlobalMarketsPanel'

const WS_URL = 'ws://localhost:8000/ws'

export default function App() {
  const { message, status } = useWebSocket(WS_URL)

  const handleRefreshLLM = async () => {
    try { await fetch('/api/llm/refresh', { method: 'POST' }) } catch { /* ignore */ }
  }

  const isConnected = status === 'connected'
  const feedTime = message?.timestamp
    ? new Date(message.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '—'

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-terminal-bg text-terminal-text">

      {/* ── Compact top header bar ───────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-1.5 border-b border-terminal-border/60 bg-terminal-panel flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-bold tracking-widest text-terminal-green uppercase">Market Pulse</span>
          <span className={`text-[9px] font-bold tracking-widest px-2 py-0.5 rounded-full border ${
            isConnected
              ? 'border-terminal-green/40 text-terminal-green bg-terminal-green/10'
              : 'border-terminal-amber/40 text-terminal-amber bg-terminal-amber/10'
          }`}>
            {isConnected ? '● LIVE' : '○ ' + status.toUpperCase()}
          </span>
        </div>
        <div className="flex items-center gap-4 text-[9px] font-mono text-terminal-muted">
          <span>MARKET: <span className="text-terminal-text">{(message?.market_status.status ?? '—').replace('_',' ').toUpperCase()}</span></span>
          <span>FEED: <span className="text-terminal-text">{feedTime}</span></span>
          <button
            onClick={handleRefreshLLM}
            className="text-terminal-muted hover:text-terminal-green transition-colors border border-terminal-border/60 rounded px-2 py-0.5"
          >
            ↻ LLM
          </button>
        </div>
      </div>

      {/* ── Status + Ticker + Futures + FII/DII bars ────────────────────── */}
      <MarketStatusBanner status={message?.market_status ?? { status: 'pre_open', message: 'Waiting for data…' }} />
      {message && <TickerBar indices={message.indices} />}
      <NiftyFuturesBar futures={message?.nifty_futures} />
      <FIIDIIBar data={message?.fii_dii} />

      {/* ── Main 4-column grid ───────────────────────────────────────────── */}
      <div className="flex-1 grid grid-cols-4 gap-2 p-2 min-h-0 overflow-hidden">
        <MLPredictionPanel pred={message?.ml_prediction ?? null} />
        <LLMAnalysisPanel  analysis={message?.llm_analysis ?? null} onRefresh={handleRefreshLLM} />
        <GlobalMarketsPanel indices={message?.indices ?? []} movers={message?.market_movers ?? null} crypto={message?.crypto} niftyFutures={message?.nifty_futures} />
        <div className="flex flex-col gap-2 min-h-0 overflow-hidden">
          <div className="flex-1 min-h-0 overflow-hidden">
            <MoversPanel movers={message?.index_movers} />
          </div>
          <div className="flex-1 min-h-0 overflow-hidden">
            <NewsFeed news={message?.news ?? []} />
          </div>
        </div>
      </div>

      {/* ── Bottom macro strip ───────────────────────────────────────────── */}
      <MarketMoversStrip movers={message?.market_movers ?? null} />
    </div>
  )
}
