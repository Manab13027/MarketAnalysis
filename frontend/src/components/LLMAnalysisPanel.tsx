import type { LLMAnalysis } from '../types'
export function LLMAnalysisPanel({ analysis, onRefresh }: { analysis: LLMAnalysis | null; onRefresh: () => void }) {
  const bc = !analysis ? '' :
    analysis.bias === 'BULLISH' ? 'text-terminal-green' :
    analysis.bias === 'BEARISH' ? 'text-terminal-red' : 'text-terminal-amber'
  return (
    <div className="bg-terminal-panel border border-terminal-border rounded p-4 font-mono text-xs h-full overflow-y-auto flex flex-col">
      <div className="text-terminal-label tracking-widest mb-3 border-b border-terminal-border pb-2 uppercase">LLM Analysis</div>
      {!analysis ? (
        <p className="text-terminal-muted flex-1">Waiting for analysis (updates every 5 min)...</p>
      ) : (
        <div className="space-y-3 flex-1">
          <div>
            <span className="text-terminal-label">Bias : </span>
            <span className={`font-bold ${bc}`}>{analysis.bias}</span>
            <span className="text-terminal-muted ml-2">({analysis.confidence})</span>
          </div>
          <p className="text-terminal-text leading-relaxed">{analysis.summary}</p>
          <div>
            <div className="text-terminal-label mb-1">Key Risks :</div>
            {analysis.key_risks.map((r, i) => <div key={i} className="text-terminal-muted">• {r}</div>)}
          </div>
          <div><span className="text-terminal-label">News Impact : </span><span className="text-terminal-muted">{analysis.news_impact}</span></div>
          <div>
            <span className="text-terminal-label">Support : </span><span className="text-terminal-green">{analysis.watch_levels.support?.toLocaleString('en-IN')}</span>
            <span className="text-terminal-label ml-4">Resistance : </span><span className="text-terminal-red">{analysis.watch_levels.resistance?.toLocaleString('en-IN')}</span>
          </div>
          <div className="text-terminal-muted">Updated : {new Date(analysis.updated_at).toLocaleTimeString('en-IN')}</div>
        </div>
      )}
      <button onClick={onRefresh} className="mt-4 w-full border border-terminal-border text-terminal-label hover:text-terminal-text hover:border-terminal-blue text-xs py-1 rounded transition-colors">
        [ Refresh Now ]
      </button>
    </div>
  )
}
