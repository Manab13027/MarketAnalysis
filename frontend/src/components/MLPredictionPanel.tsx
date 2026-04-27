import type { MLPrediction } from '../types'
const fmt    = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 2 })
const fmtPct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
const LABELS: Record<string, string> = { usdinr:'USDINR', usoil:'USOIL', msci:'MSCI', breadth:'BREADTH' }
const LETTERS = ['B','C','D','E']

export function MLPredictionPanel({ pred }: { pred: MLPrediction | null }) {
  if (!pred) return (
    <div className="bg-terminal-panel border border-terminal-border rounded p-4 flex items-center justify-center">
      <span className="text-terminal-muted text-xs animate-pulse">Training model...</span>
    </div>
  )
  const up = pred.direction === 'UP'
  const dc = up ? 'text-terminal-green' : 'text-terminal-red'
  const keys = Object.keys(pred.adjustments)
  return (
    <div className="bg-terminal-panel border border-terminal-border rounded p-4 font-mono text-xs h-full overflow-y-auto">
      <div className="text-terminal-label tracking-widest mb-3 border-b border-terminal-border pb-2 text-xs uppercase">
        NIFTY 50 — Next-Day Prediction
      </div>
      <div className="text-terminal-label mb-3">
        Today close : <span className="text-terminal-text font-semibold">{fmt(pred.today_close)}</span>
      </div>
      <div className="space-y-1 text-terminal-muted">
        <div>[A] ML preliminary&nbsp;&nbsp;: <span className="text-terminal-text">{fmt(pred.ml_preliminary)}</span></div>
        {keys.map((k, i) => {
          const v = pred.adjustments[k]
          return (
            <div key={k}>
              [{LETTERS[i]}] {LABELS[k]} adj&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;:{' '}
              <span className={v.value >= 0 ? 'text-terminal-green' : 'text-terminal-red'}>
                {v.value >= 0 ? '+' : ''}{fmt(v.value)}
              </span>
              <span className="text-terminal-muted ml-2">(β={v.beta} w={v.window})</span>
            </div>
          )
        })}
      </div>
      <div className="border-t border-terminal-border mt-3 pt-3 space-y-1">
        <div className={`text-base font-bold ${dc}`}>
          FINAL : {fmt(pred.final_prediction)} {up ? '▲ UP' : '▼ DOWN'}
        </div>
        <div>Expected move : <span className={dc}>{fmtPct(pred.expected_move_pct)} ({pred.expected_move >= 0 ? '+' : ''}{fmt(pred.expected_move)} pts)</span></div>
        <div className="text-terminal-muted">P(UP) : <span className="text-terminal-text">{pred.p_up.toFixed(3)}</span></div>
        <div className="text-terminal-muted">Classifier : <span className={pred.classifier === 'AGREE' ? 'text-terminal-green' : 'text-terminal-amber'}>{pred.classifier} — {pred.classifier_detail}</span></div>
        <div className="text-terminal-muted">Confidence : <span className="text-terminal-text">{pred.confidence.toFixed(3)}</span></div>
      </div>
      <div className="border-t border-terminal-border mt-3 pt-3 space-y-1 text-terminal-muted">
        <div>VIX today : <span className="text-terminal-text">{pred.vix_today.toFixed(2)}%</span></div>
        <div>VIX range : <span className="text-terminal-text">{fmt(pred.vix_range_low)} – {fmt(pred.vix_range_high)}</span></div>
        <div>Within VIX range? : <span className={pred.within_vix_range ? 'text-terminal-green' : 'text-terminal-red'}>{pred.within_vix_range ? 'YES' : 'NO'}</span></div>
      </div>
      <div className="border-t border-terminal-border mt-3 pt-3 space-y-1 text-terminal-muted">
        {Object.entries(pred.factors_today_pred).map(([k, v]) => (
          <div key={k}>
            {LABELS[k]} today/pred :{' '}
            <span className="text-terminal-text">{v.today} / {v.pred}</span>
            <span className={v.direction === 'UP' ? 'text-terminal-green ml-1' : 'text-terminal-red ml-1'}>({v.direction})</span>
          </div>
        ))}
      </div>
      <div className="border-t border-terminal-border mt-3 pt-3 space-y-1 text-terminal-muted">
        <div>CV MAPE : <span className="text-terminal-text">{pred.cv_mape.toFixed(2)}%</span></div>
        <div>CV Dir Accuracy : <span className="text-terminal-text">{pred.cv_dir_accuracy.toFixed(1)}%</span></div>
      </div>
    </div>
  )
}
