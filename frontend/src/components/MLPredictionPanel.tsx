import type { MLPrediction } from '../types'
const fmt    = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 2 })
const fmtPct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
const LABELS: Record<string, string> = { usdinr:'USDINR', usoil:'USOIL', msci:'MSCI', breadth:'BREADTH' }
const LETTERS = ['B','C','D','E']

export function MLPredictionPanel({ pred }: { pred: MLPrediction | null }) {
  if (!pred) return (
    <div className="glass-panel panel-accent rounded-3xl p-5 flex items-center justify-center min-h-0">
      <span className="text-terminal-muted text-xs uppercase tracking-[0.24em] animate-pulse">Training model...</span>
    </div>
  )
  const up = pred.direction === 'UP'
  const dc = up ? 'text-terminal-green' : 'text-terminal-red'
  const keys = Object.keys(pred.adjustments)
  return (
    <div className="glass-panel panel-accent rounded-3xl p-5 font-mono text-xs h-full overflow-y-auto">
      <div className="mb-4 flex items-end justify-between gap-3 border-b border-terminal-border/70 pb-3">
        <div>
          <div className="font-display text-sm font-semibold uppercase tracking-[0.32em] text-slate-100">
            NIFTY 50
          </div>
          <div className="text-[10px] uppercase tracking-[0.24em] text-terminal-label">Next-day prediction</div>
        </div>
        <div className={`rounded-full border px-2.5 py-1 text-[10px] font-bold tracking-[0.24em] ${up ? 'border-emerald-400/40 bg-emerald-500/10 text-emerald-300' : 'border-rose-400/40 bg-rose-500/10 text-rose-300'}`}>
          {up ? 'UPWARD BIAS' : 'DOWNWARD BIAS'}
        </div>
      </div>
      <div className="grid gap-3">
        <div className="rounded-2xl border border-terminal-border/70 bg-white/[0.03] px-4 py-3">
          <div className="text-[10px] uppercase tracking-[0.24em] text-terminal-label">Today close</div>
          <div className="mt-1 text-lg font-semibold text-slate-50">{fmt(pred.today_close)}</div>
        </div>
        <div className="rounded-2xl border border-terminal-border/70 bg-white/[0.03] px-4 py-3 space-y-1.5 text-terminal-muted">
          <div>[A] ML preliminary : <span className="text-terminal-text">{fmt(pred.ml_preliminary)}</span></div>
          {keys.map((k, i) => {
            const v = pred.adjustments[k]
            return (
              <div key={k} className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span>[{LETTERS[i]}] {LABELS[k]} adj :</span>
                <span className={v.value >= 0 ? 'text-terminal-green' : 'text-terminal-red'}>
                  {v.value >= 0 ? '+' : ''}{fmt(v.value)}
                </span>
                <span className="text-terminal-muted">(β={v.beta} w={v.window})</span>
              </div>
            )
          })}
        </div>
      </div>
      <div className="mt-4 grid gap-3 border-t border-terminal-border/70 pt-4">
        <div className={`rounded-2xl border px-4 py-3 ${up ? 'border-emerald-400/25 bg-emerald-500/10' : 'border-rose-400/25 bg-rose-500/10'}`}>
          <div className={`text-base font-bold ${dc}`}>
            FINAL : {fmt(pred.final_prediction)} {up ? '▲ UP' : '▼ DOWN'}
          </div>
          <div>Expected move : <span className={dc}>{fmtPct(pred.expected_move_pct)} ({pred.expected_move >= 0 ? '+' : ''}{fmt(pred.expected_move)} pts)</span></div>
        </div>
        <div className="grid gap-1 text-terminal-muted sm:grid-cols-2">
          <div>P(UP) : <span className="text-terminal-text">{pred.p_up.toFixed(3)}</span></div>
          <div>Classifier : <span className={pred.classifier === 'AGREE' ? 'text-terminal-green' : 'text-terminal-amber'}>{pred.classifier} — {pred.classifier_detail}</span></div>
          <div>Confidence : <span className="text-terminal-text">{pred.confidence.toFixed(3)}</span></div>
          <div>VIX today : <span className="text-terminal-text">{pred.vix_today.toFixed(2)}%</span></div>
        </div>
      </div>
      <div className="mt-4 grid gap-3 border-t border-terminal-border/70 pt-4 text-terminal-muted">
        <div className="rounded-2xl border border-terminal-border/70 bg-white/[0.03] px-4 py-3 space-y-1">
          <div>VIX range : <span className="text-terminal-text">{fmt(pred.vix_range_low)} – {fmt(pred.vix_range_high)}</span></div>
          <div>Within VIX range? : <span className={pred.within_vix_range ? 'text-terminal-green' : 'text-terminal-red'}>{pred.within_vix_range ? 'YES' : 'NO'}</span></div>
        </div>
        <div className="rounded-2xl border border-terminal-border/70 bg-white/[0.03] px-4 py-3 space-y-1">
          {Object.entries(pred.factors_today_pred).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between gap-3">
              <span>{LABELS[k]} today/pred</span>
              <span className="text-terminal-text">{v.today} / {v.pred} <span className={v.direction === 'UP' ? 'text-terminal-green ml-1' : 'text-terminal-red ml-1'}>({v.direction})</span></span>
            </div>
          ))}
        </div>
        <div className="grid gap-1 rounded-2xl border border-terminal-border/70 bg-white/[0.03] px-4 py-3 sm:grid-cols-2">
          <div>CV MAPE : <span className="text-terminal-text">{pred.cv_mape.toFixed(2)}%</span></div>
          <div>CV Dir Accuracy : <span className="text-terminal-text">{pred.cv_dir_accuracy.toFixed(1)}%</span></div>
        </div>
      </div>
    </div>
  )
}
