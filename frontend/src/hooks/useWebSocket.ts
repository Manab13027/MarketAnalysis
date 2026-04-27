import { useState, useEffect, useRef, useCallback } from 'react'
import type { WSMessage } from '../types'

type ConnStatus = 'connecting' | 'connected' | 'disconnected'

export function useWebSocket(url: string) {
  const [message, setMessage] = useState<WSMessage | null>(null)
  const [status,  setStatus]  = useState<ConnStatus>('connecting')
  const wsRef         = useRef<WebSocket | null>(null)
  const reconnectRef  = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onopen    = () => setStatus('connected')
    ws.onclose   = () => {
      setStatus('disconnected')
      reconnectRef.current = setTimeout(connect, 3000)
    }
    ws.onerror   = () => ws.close()
    ws.onmessage = (e) => {
      try { setMessage(JSON.parse(e.data) as WSMessage) }
      catch { /* ignore malformed */ }
    }
  }, [url])

  useEffect(() => {
    connect()
    return () => { clearTimeout(reconnectRef.current); wsRef.current?.close() }
  }, [connect])

  return { message, status }
}
