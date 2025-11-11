import React, { useEffect, useMemo, useRef, useState } from 'react'

type Msg =
  | { type: 'system'; text: string; sender: 'system' }
  | { type: 'chat'; text: string; sender: string }

export default function App() {
  const [name, setName] = useState('익명')
  const [status, setStatus] = useState<'연결 중' | '연결됨' | '연결 종료' | '오류'>('연결 중')
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const wsRef = useRef<WebSocket | null>(null)

  const wsUrl = useMemo(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    // dev에서는 Vite가 5173에서 구동되고, '/ws'는 Vite proxy로 백엔드로 전달됩니다.
    return `${proto}://${location.host}/ws?name=${encodeURIComponent(name || '익명')}`
  }, [name])

  const connect = () => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    setStatus('연결 중')

    ws.onopen = () => setStatus('연결됨')
    ws.onclose = () => setStatus('연결 종료')
    ws.onerror = () => setStatus('오류')
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as Msg
        setMessages((prev) => [...prev, msg])
      } catch {
        // ignore non-JSON
      }
    }
  }

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }

  useEffect(() => {
    // auto-connect on mount
    connect()
    return () => disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const send = (e: React.FormEvent) => {
    e.preventDefault()
    const ws = wsRef.current
    const text = input.trim()
    if (!ws || ws.readyState !== WebSocket.OPEN || !text) return
    ws.send(text)
    setInput('')
  }

  return (
    <div className="wrap">
      <header>
        <strong>미니 채팅</strong>
        <span style={{ opacity: 0.8, marginLeft: 8 }}> {status}</span>
        <div style={{ marginTop: 6, opacity: 0.9 }}>
          이름{' '}
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: 160, padding: 6, borderRadius: 8, border: '1px solid #333', background: '#0f0f0f', color: '#eee' }}
          />
          <button onClick={connect} style={{ marginLeft: 8 }}>연결/재연결</button>
          <button onClick={disconnect} style={{ marginLeft: 8 }}>연결 종료</button>
        </div>
      </header>

      <div id="log">
        {messages.map((m, i) => (
          <div key={i} className={m.type === 'system' ? 'sys' : 'msg'}>
            {m.type === 'system' ? (
              <>{m.text}</>
            ) : (
              <>
                <span className={m.sender === name ? 'me' : 'them'}>[{m.sender}]</span> {m.text}
              </>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={send}>
        <input
          value={input}
          placeholder="메시지를 입력하세요..."
          onChange={(e) => setInput(e.target.value)}
          autoComplete="off"
        />
        <button type="submit">전송</button>
      </form>
    </div>
  )
}

