import { useWebSocket } from './hooks/useWebSocket'
import { MarketStatusBanner } from './components/MarketStatusBanner'
import { TickerBar }           from './components/TickerBar'
import { MLPredictionPanel }   from './components/MLPredictionPanel'
import { LLMAnalysisPanel }    from './components/LLMAnalysisPanel'
import { NewsFeed }            from './components/NewsFeed'
import { MarketMoversStrip }   from './components/MarketMoversStrip'

const WS_URL = 'ws://localhost:8000/ws'

export default function App() {
  const { message, status } = useWebSocket(WS_URL)

  const handleRefreshLLM = async () => {
    try { await fetch('/api/llm/refresh', { method: 'POST' }) }
    catch { /* ignore */ }
  }

  return (
    <div className="flex flex-col h-screen bg-terminal-bg overflow-hidden">
      {status !== 'connected' && (
        <div className="text-center text-xs py-0.5 bg-red-900/40 text-terminal-red">
          {status === 'connecting' ? '⟳ Connecting to server...' : '⟳ Reconnecting...'}
        </div>
      )}
      {message && <MarketStatusBanner status={message.market_status} />}
      {message && <TickerBar indices={message.indices} />}
      <div className="flex-1 grid grid-cols-3 gap-2 p-2 min-h-0">
        <MLPredictionPanel pred={message?.ml_prediction ?? null} />
        <LLMAnalysisPanel analysis={message?.llm_analysis ?? null} onRefresh={handleRefreshLLM} />
        <NewsFeed news={message?.news ?? []} />
      </div>
      <MarketMoversStrip movers={message?.market_movers ?? null} />
    </div>
  )
}
