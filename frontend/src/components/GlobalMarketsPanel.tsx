import type { IndexQuote, MarketMovers, CryptoQuote, FuturesContract } from '../types'

// ── helpers ───────────────────────────────────────────────────────────────────

function pct(n: number) { return (n >= 0 ? '+' : '') + n.toFixed(2) + '%' }
function clr(n: number) { return n >= 0 ? 'text-terminal-green' : 'text-terminal-red' }
function arr(n: number) { return n >= 0 ? '▲' : '▼' }

// ── sub-components ────────────────────────────────────────────────────────────

function IndexRow({ q }: { q: IndexQuote }) {
  const pts = q.change
  const fmtPts = Math.abs(pts) >= 100
    ? pts.toLocaleString('en-US', { maximumFractionDigits: 0 })
    : pts.toFixed(2)
  return (
    <div className="flex items-center justify-between py-1 px-3 hover:bg-white/[0.04] rounded-xl transition-colors">
      <div className="flex items-center gap-1.5 min-w-0">
        {q.is_futures && (
          <span className="text-[8px] text-terminal-muted border border-terminal-border/70 rounded-full px-1 shrink-0">FUT</span>
        )}
        <span className="text-[10px] text-terminal-label truncate uppercase tracking-[0.12em]">{q.name}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0 ml-2">
        <span className="text-[11px] font-mono font-bold text-terminal-text">
          {q.price.toLocaleString('en-US', { maximumFractionDigits: 2 })}
        </span>
        <span className={`text-[10px] font-mono ${clr(pts)}`}>
          {arr(pts)} {fmtPts}
        </span>
      </div>
    </div>
  )
}

function MacroRow({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex items-center justify-between py-1 px-3 hover:bg-white/[0.04] rounded-xl transition-colors">
      <span className="text-[10px] text-terminal-muted">{label}</span>
      <div className="text-right">
        <span className="text-[11px] font-mono font-bold text-terminal-text">{value}</span>
        {sub && <span className="text-[9px] text-terminal-muted ml-1">{sub}</span>}
      </div>
    </div>
  )
}

function MacroRowColored({ label, value, n }: { label: string; value: string; n: number }) {
  return (
    <div className="flex items-center justify-between py-1 px-3 hover:bg-white/[0.04] rounded-xl transition-colors">
      <span className="text-[10px] text-terminal-muted">{label}</span>
      <span className={`text-[11px] font-mono font-bold ${clr(n)}`}>{arr(n)} {value}</span>
    </div>
  )
}

function SectionHeader({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 px-3 pt-3 pb-1">
      <span className="text-[9px] text-terminal-muted font-mono uppercase tracking-[0.24em]">{label}</span>
      <div className="flex-1 h-px bg-terminal-border/60" />
    </div>
  )
}

// ── region config ─────────────────────────────────────────────────────────────

const AMERICAS  = ['^GSPC', '^IXIC', 'ES=F', 'NQ=F', 'YM=F']
const EUROPE    = ['^GDAXI', '^FTSE', '^FCHI']
const ASIA_PAC  = ['^N225', '^HSI', '^AXJO', 'NKD=F']

// ── Crypto row ────────────────────────────────────────────────────────────────

function CryptoRow({ c }: { c: CryptoQuote }) {
  const mcap = c.market_cap_usd
    ? c.market_cap_usd >= 1e12
      ? `$${(c.market_cap_usd / 1e12).toFixed(2)}T`
      : `$${(c.market_cap_usd / 1e9).toFixed(0)}B`
    : null
  return (
    <div className="flex items-center justify-between py-1 px-3 hover:bg-white/[0.04] rounded-xl transition-colors">
      <div className="flex items-center gap-1.5 min-w-0">
        <span className="text-[8px] text-terminal-muted/70 border border-terminal-border/50 rounded-full px-1 shrink-0">24/7</span>
        <span className="text-[10px] text-terminal-label truncate uppercase tracking-[0.12em]">{c.name}</span>
        {mcap && <span className="text-[8px] text-terminal-muted/60 font-mono shrink-0">{mcap}</span>}
      </div>
      <div className="flex items-center gap-2 shrink-0 ml-2">
        <span className="text-[11px] font-mono font-bold text-terminal-text">
          ${c.price_usd.toLocaleString('en-US', { maximumFractionDigits: c.price_usd < 10 ? 4 : 0 })}
        </span>
        <span className={`text-[10px] font-mono ${clr(c.change_pct_24h)}`}>
          {arr(c.change_pct_24h)} {pct(c.change_pct_24h)}
        </span>
      </div>
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

interface Props {
  indices:       IndexQuote[]
  movers:        MarketMovers | null
  crypto?:       CryptoQuote[] | null
  niftyFutures?: FuturesContract[] | null
}

export function GlobalMarketsPanel({ indices, movers, crypto, niftyFutures }: Props) {
  const bySymbol = Object.fromEntries(indices.map(q => [q.symbol, q]))

  const region = (syms: string[]) =>
    syms.map(s => bySymbol[s]).filter(Boolean) as IndexQuote[]

  const americas  = region(AMERICAS)
  const europe    = region(EUROPE)
  const asiaPac   = region(ASIA_PAC)
  // Prefer is_gift entry; fall back to nearest-month NIFTY future as proxy
  const giftNifty = niftyFutures?.find(f => f.is_gift)
    ?? niftyFutures?.[0]
    ?? null

  return (
    <div className="glass-panel panel-accent flex flex-col h-full rounded-3xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-terminal-border/70 bg-white/[0.03] shrink-0">
        <span className="font-display text-sm font-semibold uppercase tracking-[0.3em] text-slate-100">
          Global Markets
        </span>
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-terminal-green animate-pulse" />
          <span className="text-[9px] text-terminal-green font-mono tracking-[0.22em] uppercase">LIVE</span>
        </span>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 scrollbar-hide">

        {/* Americas */}
        {americas.length > 0 && (
          <>
            <SectionHeader label="Americas" />
            {americas.map(q => <IndexRow key={q.symbol} q={q} />)}
          </>
        )}

        {/* Europe */}
        {europe.length > 0 && (
          <>
            <SectionHeader label="Europe" />
            {europe.map(q => <IndexRow key={q.symbol} q={q} />)}
          </>
        )}

        {/* Asia-Pacific */}
        {(asiaPac.length > 0 || giftNifty) && (
          <>
            <SectionHeader label="Asia-Pacific" />
            {giftNifty && (
              <div className="flex items-center justify-between py-1 px-3 hover:bg-white/[0.04] rounded-xl transition-colors">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="text-[8px] text-sky-400 border border-sky-400/40 rounded-full px-1 shrink-0 font-bold">GIFT</span>
                  <span className="text-[10px] text-terminal-label truncate uppercase tracking-[0.12em]">{giftNifty.label}</span>
                  {giftNifty.is_prev_close && (
                    <span className="text-[8px] text-terminal-amber border border-terminal-amber/40 rounded px-0.5">PREV</span>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-2">
                  <span className="text-[11px] font-mono font-bold text-terminal-text">
                    {giftNifty.price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </span>
                  <span className={`text-[10px] font-mono ${giftNifty.change >= 0 ? 'text-terminal-green' : 'text-terminal-red'}`}>
                    {giftNifty.change >= 0 ? '▲' : '▼'} {Math.abs(giftNifty.change).toFixed(2)}
                  </span>
                </div>
              </div>
            )}
            {asiaPac.map(q => <IndexRow key={q.symbol} q={q} />)}
          </>
        )}

        {/* Commodities */}
        {movers && (
          <>
            <SectionHeader label="Commodities" />
            <MacroRow label="Gold"       value={`$${movers.gold.toFixed(0)}`}        sub="oz" />
            {movers.silver != null && (
              <MacroRow label="Silver"   value={`$${movers.silver.toFixed(2)}`}      sub="oz" />
            )}
            <MacroRow label="WTI Crude"  value={`$${movers.wti_crude.toFixed(2)}`}   sub="bbl" />
            <MacroRow label="Brent"      value={`$${movers.brent_crude.toFixed(2)}`} sub="bbl" />
          </>
        )}

        {/* Crypto — 24/7 */}
        {crypto && crypto.length > 0 && (
          <>
            <SectionHeader label="Crypto · 24/7" />
            {crypto.map(c => <CryptoRow key={c.symbol} c={c} />)}
          </>
        )}

        {/* Macro */}
        {movers && (
          <>
            <SectionHeader label="Macro" />
            <MacroRow        label="USD/INR"  value={movers.usdinr.toFixed(4)} />
            <MacroRow        label="US 10Y"   value={movers.us10y.toFixed(3) + '%'} />
            <MacroRow        label="MSCI EM"  value={movers.msci.toFixed(2)} />
            <MacroRowColored label="VIX"
              value={movers.vix.toFixed(2)}
              n={-movers.vix}   /* high VIX = fear = red */
            />
          </>
        )}

        {/* Futures strip if not already in indices */}
        {movers && !bySymbol['ES=F'] && (
          <>
            <SectionHeader label="US Futures" />
            {movers.sp500_futures  != null && (
              <MacroRow label="S&P 500 Fut" value={movers.sp500_futures.toLocaleString('en-US',  { maximumFractionDigits: 0 })} />
            )}
            {movers.dow_futures    != null && (
              <MacroRow label="Dow Fut"     value={movers.dow_futures.toLocaleString('en-US',    { maximumFractionDigits: 0 })} />
            )}
            {movers.nasdaq_futures != null && (
              <MacroRow label="NASDAQ Fut"  value={movers.nasdaq_futures.toLocaleString('en-US', { maximumFractionDigits: 0 })} />
            )}
          </>
        )}

      </div>
    </div>
  )
}
