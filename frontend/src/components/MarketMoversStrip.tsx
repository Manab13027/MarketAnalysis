import type { MarketMovers } from '../types'
export function MarketMoversStrip({ movers }: { movers: MarketMovers | null }) {
  if (!movers) return null
  const items = [
    { label:'USD/INR',  val: movers.usdinr.toFixed(4) },
    { label:'WTI',      val: '$' + movers.wti_crude.toFixed(2) },
    { label:'BRENT',    val: '$' + movers.brent_crude.toFixed(2) },
    { label:'GOLD',     val: '$' + movers.gold.toFixed(0) },
    { label:'VIX',      val: movers.vix.toFixed(2) },
    { label:'US 10Y',   val: movers.us10y.toFixed(2) + '%' },
    { label:'MSCI',     val: movers.msci.toFixed(2) },
    { label:'S&P 500',  val: movers.sp500.toLocaleString('en-US',{maximumFractionDigits:0}) },
    ...(movers.sp500_futures ? [{ label:'S&P FUT', val: movers.sp500_futures.toLocaleString('en-US',{maximumFractionDigits:0}) }] : []),
  ]
  return (
    <div className="w-full bg-terminal-panel border-t border-terminal-border px-4 py-2 flex gap-6 overflow-x-auto text-xs flex-shrink-0">
      {items.map(m => (
        <span key={m.label} className="flex gap-1 items-center whitespace-nowrap">
          <span className="text-terminal-label">{m.label}</span>
          <span className="text-terminal-text font-semibold">{m.val}</span>
        </span>
      ))}
    </div>
  )
}
