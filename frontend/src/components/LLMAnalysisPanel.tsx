import { useState } from 'react'
import type { LLMAnalysis } from '../types'
export function LLMAnalysisPanel({ analysis, onRefresh }: { analysis: LLMAnalysis | null; onRefresh: () => void }) {
  const [loading, setLoading] = useState(false)
  const handleRefresh = async () => {
    setLoading(true)
    await onRefresh()
    setTimeout(() => setLoading(false), 3000)
  }
  const bc = !analysis ? '' :
    analysis.bias === 'BULLISH' ? 'text-terminal-green' :
    analysis.bias === 'BEARISH' ? 'text-terminal-red' : 'text-terminal-amber'
  return (
    <div className="glass-panel panel-accent rounded-3xl p-5 font-mono text-xs h-full overflow-y-auto flex flex-col">
      <div className="mb-4 flex items-end justify-between gap-3 border-b border-terminal-border/70 pb-3">
        <div>
          <div className="font-display text-sm font-semibold uppercase tracking-[0.32em] text-slate-100">LLM Analysis</div>
          <div className="text-[10px] uppercase tracking-[0.24em] text-terminal-label">Qualitative market read</div>
        </div>
        {analysis && (
          <div className={`rounded-full border px-2.5 py-1 text-[10px] font-bold tracking-[0.24em] ${analysis.bias === 'BULLISH' ? 'border-emerald-400/40 bg-emerald-500/10 text-emerald-300' : analysis.bias === 'BEARISH' ? 'border-rose-400/40 bg-rose-500/10 text-rose-300' : 'border-amber-400/40 bg-amber-500/10 text-amber-300'}`}>
            {analysis.bias}
          </div>
        )}
      </div>
      {!analysis ? (
        <p className="text-terminal-muted flex-1 rounded-2xl border border-terminal-border/70 bg-white/[0.03] p-4">Waiting for analysis (updates every 5 min)...</p>
      ) : (
        <div className="space-y-3 flex-1">
          <div className="rounded-2xl border border-terminal-border/70 bg-white/[0.03] px-4 py-3">
            <div className="text-[10px] uppercase tracking-[0.24em] text-terminal-label">Bias / confidence</div>
            <div className={`mt-1 text-lg font-bold ${bc}`}>{analysis.bias} <span className="text-sm text-terminal-muted">({analysis.confidence})</span></div>
          </div>
          <p className="rounded-2xl border border-terminal-border/70 bg-white/[0.03] px-4 py-3 leading-relaxed text-terminal-text">{analysis.summary}</p>
          <div className="rounded-2xl border border-terminal-border/70 bg-white/[0.03] px-4 py-3">
            <div className="mb-2 text-[10px] uppercase tracking-[0.24em] text-terminal-label">Key risks</div>
            {analysis.key_risks.map((r, i) => <div key={i} className="text-terminal-muted">• {r}</div>)}
          </div>
          <div className="rounded-2xl border border-terminal-border/70 bg-white/[0.03] px-4 py-3">
            <div className="text-[10px] uppercase tracking-[0.24em] text-terminal-label">News impact</div>
            <div className="mt-1 text-terminal-text">{analysis.news_impact}</div>
          </div>
          <div className="grid gap-2 rounded-2xl border border-terminal-border/70 bg-white/[0.03] px-4 py-3 sm:grid-cols-2">
            <div><span className="text-terminal-label">Support</span><div className="text-terminal-green">{analysis.watch_levels.support?.toLocaleString('en-IN')}</div></div>
            <div><span className="text-terminal-label">Resistance</span><div className="text-terminal-red">{analysis.watch_levels.resistance?.toLocaleString('en-IN')}</div></div>
          </div>
          <div className="text-terminal-muted">Updated : {new Date(analysis.updated_at).toLocaleTimeString('en-IN')}</div>
        </div>
      )}
      <button
        onClick={handleRefresh}
        disabled={loading}
        className="mt-4 w-full rounded-2xl border border-terminal-border/70 bg-white/[0.03] py-2 text-xs uppercase tracking-[0.24em] text-terminal-label transition-all hover:border-terminal-blue/70 hover:text-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? '⟳ Refreshing...' : '[ Refresh Now ]'}
      </button>
    </div>
  )
}
