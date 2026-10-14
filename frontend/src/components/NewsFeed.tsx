import { useState, useRef, useEffect } from 'react'
import type { NewsItem } from '../types'
const DOT: Record<string, string>   = { positive:'bg-terminal-green', negative:'bg-terminal-red', neutral:'bg-terminal-muted' }
const COLOR: Record<string, string> = { positive:'text-terminal-green', negative:'text-terminal-red', neutral:'text-terminal-muted' }

type Filter = 'all' | 'india' | 'global' | 'telegram'

export function NewsFeed({ news }: { news: NewsItem[] }) {
  const [filter, setFilter] = useState<Filter>('all')
  const scrollRef = useRef<HTMLDivElement>(null)
  const pausedRef = useRef(false)
  const rafRef    = useRef<number | null>(null)
  const accRef    = useRef(0) // sub-pixel accumulator

  const filtered = news.filter(n => {
    if (filter === 'telegram') return n.source.toLowerCase().includes('telegram')
    if (filter === 'india')    return n.region === 'india' && !n.source.toLowerCase().includes('telegram')
    if (filter === 'global')   return n.region === 'global' && !n.source.toLowerCase().includes('telegram')
    return true
  })

  const tabs: { key: Filter; label: string }[] = [
    { key: 'all',      label: 'ALL' },
    { key: 'india',    label: 'INDIA' },
    { key: 'global',   label: 'GLOBAL' },
    { key: 'telegram', label: '✈ TG' },
  ]

  // Auto-scroll: 20px/s, pauses on hover, resets to top at bottom
  useEffect(() => {
    const SPEED = 20 // px per second
    let last = performance.now()

    const tick = (now: number) => {
      const el = scrollRef.current
      if (el && !pausedRef.current) {
        const dt = (now - last) / 1000
        accRef.current += SPEED * dt
        const px = Math.floor(accRef.current)
        if (px >= 1) {
          accRef.current -= px
          const maxScroll = el.scrollHeight - el.clientHeight
          if (el.scrollTop >= maxScroll - 2) {
            // Brief pause at bottom then snap back
            pausedRef.current = true
            setTimeout(() => {
              if (el) el.scrollTop = 0
              pausedRef.current = false
            }, 2000)
          } else {
            el.scrollTop += px
          }
        }
      }
      last = now
      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [])

  // Reset scroll position when filter or news changes
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0
  }, [filter, news.length])

  return (
    <div className="glass-panel panel-accent rounded-3xl p-5 font-mono text-xs h-full flex flex-col">
      <div className="flex items-center justify-between gap-3 mb-4 border-b border-terminal-border/70 pb-3 flex-shrink-0">
        <div>
          <div className="font-display text-sm font-semibold uppercase tracking-[0.32em] text-slate-100">News Feed</div>
          <div className="text-[10px] uppercase tracking-[0.24em] text-terminal-label">Live headlines and sentiment</div>
        </div>
        <div className="flex gap-1 flex-wrap justify-end">
          {tabs.map(({ key, label }) => (
            <button key={key} onClick={() => setFilter(key)}
              className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.18em] transition-colors ${
                filter === key
                  ? key === 'telegram'
                    ? 'border-sky-400/50 bg-sky-500/10 text-sky-300'
                    : 'border-cyan-400/50 bg-cyan-500/10 text-cyan-200'
                  : 'border-terminal-border/70 bg-white/[0.03] text-terminal-muted hover:text-terminal-text'
              }`}>
              {label}
            </button>
          ))}
        </div>
      </div>
      <div
        ref={scrollRef}
        className="space-y-2 overflow-y-auto flex-1 scrollbar-hide pr-1"
        onMouseEnter={() => { pausedRef.current = true }}
        onMouseLeave={() => { pausedRef.current = false }}
      >
        {filtered.length === 0 && <p className="rounded-2xl border border-terminal-border/70 bg-white/[0.03] p-4 text-terminal-muted">No items...</p>}
        {filtered.map(item => {
          const isTg = item.source.toLowerCase().includes('telegram')
          return (
            <a key={item.id} href={item.url} target="_blank" rel="noopener noreferrer" className="group block rounded-2xl border border-terminal-border/70 bg-white/[0.03] p-3 transition-all hover:border-terminal-blue/40 hover:bg-white/[0.06]">
              <div className="flex items-start gap-3">
                <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${DOT[item.sentiment]}`} />
                <div>
                  <p className={`leading-snug group-hover:underline ${COLOR[item.sentiment]}`}>{item.title}</p>
                  <p className="mt-1 text-terminal-muted">
                    {isTg && <span className="text-sky-500 mr-1">✈</span>}
                    {item.source} · {new Date(item.published_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            </a>
          )
        })}
      </div>
    </div>
  )
}
