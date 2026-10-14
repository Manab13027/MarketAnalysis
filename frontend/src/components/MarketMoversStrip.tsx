import type { MarketMovers } from '../types'
export function MarketMoversStrip({ movers }: { movers: MarketMovers | null }) {
  if (!movers) return null
  const items = [
    { label:'USD/INR',   val: movers.usdinr.toFixed(4) },
    { label:'WTI',       val: '$' + movers.wti_crude.toFixed(2) },
    { label:'BRENT',     val: '$' + movers.brent_crude.toFixed(2) },
    { label:'GOLD',      val: '$' + movers.gold.toFixed(0) },
    { label:'VIX',       val: movers.vix.toFixed(2) },
    { label:'US 10Y',    val: movers.us10y.toFixed(2) + '%' },
    { label:'MSCI',      val: movers.msci.toFixed(2) },
    { label:'S&P 500',   val: movers.sp500.toLocaleString('en-US', {maximumFractionDigits:0}) },
    ...(movers.sp500_futures   ? [{ label:'S&P FUT',    val: movers.sp500_futures.toLocaleString('en-US',   {maximumFractionDigits:0}) }] : []),
    ...(movers.dow_futures     ? [{ label:'DOW FUT',    val: movers.dow_futures.toLocaleString('en-US',     {maximumFractionDigits:0}) }] : []),
    ...(movers.nasdaq_futures  ? [{ label:'NQ FUT',     val: movers.nasdaq_futures.toLocaleString('en-US',  {maximumFractionDigits:0}) }] : []),
    ...(movers.nikkei_futures  ? [{ label:'NIKKEI FUT', val: movers.nikkei_futures.toLocaleString('en-US',  {maximumFractionDigits:0}) }] : []),
  ]
  return (
    <div className="flex w-full gap-4 overflow-x-auto bg-terminal-bg/45 px-3 py-1 text-xs flex-shrink-0 backdrop-blur-xl border-t border-terminal-border/40">
      {items.map(m => (
        <span key={m.label} className="flex items-center gap-1.5 whitespace-nowrap border-r border-terminal-border/40 pr-4 last:border-0">
          <span className="text-[9px] uppercase tracking-[0.18em] text-terminal-muted">{m.label}</span>
          <span className="text-[10px] text-terminal-text font-semibold font-mono">{m.val}</span>
        </span>
      ))}
    </div>
  )
}
