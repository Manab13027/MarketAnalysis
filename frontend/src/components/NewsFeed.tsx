import { useState } from 'react'
import type { NewsItem } from '../types'
const DOT: Record<string, string>   = { positive:'bg-terminal-green', negative:'bg-terminal-red', neutral:'bg-terminal-muted' }
const COLOR: Record<string, string> = { positive:'text-terminal-green', negative:'text-terminal-red', neutral:'text-terminal-muted' }

export function NewsFeed({ news }: { news: NewsItem[] }) {
  const [region, setRegion] = useState<'all'|'india'|'global'>('all')
  const filtered = news.filter(n => region === 'all' || n.region === region)
  return (
    <div className="bg-terminal-panel border border-terminal-border rounded p-4 font-mono text-xs h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-3 border-b border-terminal-border pb-2">
        <span className="text-terminal-label tracking-widest uppercase">News Feed</span>
        <div className="flex gap-1">
          {(['all','india','global'] as const).map(r => (
            <button key={r} onClick={() => setRegion(r)}
              className={`px-2 py-0.5 rounded border text-xs transition-colors ${region===r ? 'border-terminal-blue text-terminal-blue' : 'border-terminal-border text-terminal-muted hover:text-terminal-text'}`}>
              {r.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-2">
        {filtered.length === 0 && <p className="text-terminal-muted">Loading news...</p>}
        {filtered.map(item => (
          <a key={item.id} href={item.url} target="_blank" rel="noopener noreferrer" className="block group">
            <div className="flex items-start gap-2">
              <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${DOT[item.sentiment]}`} />
              <div>
                <p className={`leading-snug group-hover:underline ${COLOR[item.sentiment]}`}>{item.title}</p>
                <p className="text-terminal-muted mt-0.5">{item.source} · {new Date(item.published_at).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}</p>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  )
}
