import type { FIIDIIEntry } from '../types'

const cr  = (n: number) => `₹${Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })} Cr`
const lk  = (n: number | null) => n == null ? '—' : Math.abs(n) >= 100000
  ? `${(n / 100000).toFixed(1)}L`
  : Math.abs(n) >= 1000
  ? `${(n / 1000).toFixed(1)}K`
  : `${n}`

const NET_COLOR = (v: number | null) =>
  v == null ? 'text-terminal-muted' : v >= 0 ? 'text-terminal-green' : 'text-terminal-red'

function Section({ label, buy, sell, unit }: {
  label: string; buy: number | null; sell: number | null; unit: 'cr' | 'contracts'
}) {
  const net = buy != null && sell != null ? buy - sell : null
  const fmt = unit === 'cr' ? (v: number | null) => v != null ? cr(v) : '—'
                            : (v: number | null) => lk(v)
  return (
    <div className="flex flex-col justify-center gap-0.5 px-3 py-1 border-r border-terminal-border/60 min-w-[140px] bg-white/[0.02]">
      <div className="text-[8px] text-terminal-muted uppercase tracking-[0.2em]">{label}</div>
      <div className="flex gap-1.5 text-[9px] font-mono">
        <span className="text-terminal-green">{fmt(buy)}</span>
        <span className="text-terminal-muted">/</span>
        <span className="text-terminal-red">{fmt(sell)}</span>
      </div>
      <div className={`text-[9px] font-bold ${NET_COLOR(net)}`}>
        {net != null ? (net >= 0 ? '+' : '−') : ''}{fmt(net)}
      </div>
    </div>
  )
}

function Row({ e }: { e: FIIDIIEntry }) {
  const netCash = e.cash_net
  return (
    <div className="flex items-stretch">
      <Section label="Cash (₹Cr)"       buy={e.cash_buy}      sell={e.cash_sell}      unit="cr" />
      <Section label="Index Fut (lots)"  buy={e.fut_idx_long}  sell={e.fut_idx_short}  unit="contracts" />
      <Section label="Index Opt (lots)"  buy={e.opt_idx_long}  sell={e.opt_idx_short}  unit="contracts" />
      <Section label="Stock Fut (lots)"  buy={e.fut_stk_long}  sell={e.fut_stk_short}  unit="contracts" />
      {e.total_long != null && (
        <div className="flex flex-col justify-center px-3 border-r border-terminal-border/60 min-w-[90px] bg-white/[0.02]">
          <div className="text-[8px] text-terminal-muted uppercase tracking-[0.2em]">Total OI</div>
          <div className="text-[9px] font-mono">
            <span className="text-terminal-green">{lk(e.total_long)}</span>
            <span className="text-terminal-muted"> / </span>
            <span className="text-terminal-red">{lk(e.total_short)}</span>
          </div>
        </div>
      )}
      <div className={`flex items-center px-3 text-[10px] font-bold ${NET_COLOR(netCash)}`}>
        {netCash >= 0 ? '▲' : '▼'} {cr(netCash)}
      </div>
    </div>
  )
}

const MONTHS: Record<string, number> = {
  Jan:0,Feb:1,Mar:2,Apr:3,May:4,Jun:5,Jul:6,Aug:7,Sep:8,Oct:9,Nov:10,Dec:11
}

function parseDateStr(dateStr: string): Date | null {
  const d = new Date(dateStr)
  if (!isNaN(d.getTime())) return d
  const m = dateStr.match(/^(\d{2})-([A-Za-z]{3})-(\d{4})$/)
  if (m) return new Date(+m[3], MONTHS[m[2]], +m[1])
  return null
}

/** Most recent trading day (skips weekends). FII/DII is always T-1 data. */
function mostRecentTradingDay(): Date {
  const today = new Date()
  const day = today.getDay() // 0=Sun,1=Mon,...,6=Sat
  const back = day === 0 ? 2 : day === 1 ? 3 : day === 6 ? 1 : 1
  const d = new Date(today)
  d.setDate(d.getDate() - back)
  return d
}

/** Returns true if dateStr matches the most recent trading day (T-1 is normal). */
function isFresh(dateStr: string): boolean {
  const d = parseDateStr(dateStr)
  if (!d) return false
  const mrt = mostRecentTradingDay()
  return d.toDateString() === mrt.toDateString()
}

export function FIIDIIBar({ data }: { data: FIIDIIEntry[] | null | undefined }) {
  const date  = data?.[0]?.date
  const stale = data && data.length > 0 && date ? !isFresh(date) : false
  const dii   = data?.find(e => !e.category.includes('FII'))
  const fii   = data?.find(e =>  e.category.includes('FII'))

  return (
    <div className={`w-full overflow-x-auto border-b border-terminal-border/70 backdrop-blur-xl flex-shrink-0 ${stale ? 'bg-terminal-amber/5' : 'bg-terminal-bg/45'}`}>
      <div className="flex items-stretch min-w-max">
        <div className="flex flex-col border-r border-terminal-border/60 bg-white/[0.02] min-w-[60px]">
          <div className="flex-1 flex flex-col justify-center px-3 border-b border-terminal-border/40">
            <span className="text-[9px] text-sky-400 font-bold tracking-[0.2em] font-mono">DII</span>
            {date && <span className="text-[7px] text-terminal-amber">{date}</span>}
          </div>
          <div className="flex-1 flex flex-col justify-center px-3">
            <span className="text-[9px] text-terminal-amber font-bold tracking-[0.2em] font-mono">FII</span>
            <span className="text-[7px] text-terminal-muted/60 normal-case">
              {stale ? 'stale cache' : 'T-1 data'}
            </span>
          </div>
        </div>

        {data && data.length > 0 ? (
          <>
            <div className="flex flex-col divide-y divide-terminal-border/40">
              {dii && <Row e={dii} />}
              {fii && <Row e={fii} />}
            </div>
            {stale && (
              <div className="flex items-center px-3 self-center">
                <span className="text-[8px] text-terminal-amber border border-terminal-amber/40 rounded px-1.5 py-0.5 animate-pulse font-mono tracking-widest">
                  STALE
                </span>
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center px-4 text-[9px] text-terminal-muted font-mono">
            <span className="text-terminal-amber">⏸ FII/DII data unavailable</span>
          </div>
        )}
      </div>
    </div>
  )
}
