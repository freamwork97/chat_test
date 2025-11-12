import React, { useEffect, useMemo, useRef, useState } from 'react'

type ChatMsg = { type: 'chat'; text: string; sender: string; timestamp: string; room?: string }
type SystemMsg = { type: 'system'; text: string; sender: 'system'; timestamp: string; room?: string }
type UsersMsg = { type: 'users'; users: string[] }
type ErrorMsg = { type: 'error'; text: string; reason?: string }
type HistoryMsg = { type: 'history'; room: string; messages: Array<ChatMsg | SystemMsg> }
type AssignMsg = { type: 'assign'; name: string; room?: string }

type Msg = ChatMsg | SystemMsg

// 타임스탬프를 간단한 형식으로 변환 (HH:MM:SS)
function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  } catch {
    return timestamp
  }
}

export default function App() {
  const [name, setName] = useState('익명')
  const [room, setRoom] = useState('lobby')
  const [status, setStatus] = useState<'연결 중' | '연결됨' | '연결 종료' | '오류'>('연결 중')
  const [messages, setMessages] = useState<Msg[]>([])
  const [users, setUsers] = useState<string[]>([])
  const [input, setInput] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const logEndRef = useRef<HTMLDivElement | null>(null)

  // 자동 스크롤
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  const wsUrl = useMemo(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    // Vite 프록시를 쓰는 경우에도 host 기준으로 붙습니다.
    const u = `${proto}://${location.host}/ws?name=${encodeURIComponent(name || '익명')}&room=${encodeURIComponent(room || 'lobby')}`
    return u
  }, [name, room])

  const hardClose = () => {
    if (wsRef.current) {
      try { wsRef.current.close() } catch {}
      wsRef.current = null
    }
  }

  const connect = () => {
    // 기존 연결 종료 + 상태 초기화
    hardClose()
    setStatus('연결 중')
    setMessages([])   // 새 방 접속 시 히스토리부터 다시 채움
    setUsers([])

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => setStatus('연결됨')
    ws.onclose = () => setStatus('연결 종료')
    ws.onerror = () => setStatus('오류')

    ws.onmessage = (ev) => {
      try {
        const raw = JSON.parse(ev.data) as
          | UsersMsg
          | ErrorMsg
          | AssignMsg
          | HistoryMsg
          | Msg

        // 1) 사용자 목록
        if ('type' in raw && raw.type === 'users') {
          setUsers(raw.users)
          return
        }

        // 2) 에러 (닉네임 중복 등의 서버 에러를 시스템 메시지로 표시)
        if ('type' in raw && raw.type === 'error') {
          setStatus('오류')
          setMessages((prev) => [
            ...prev,
            { type: 'system', text: raw.text, sender: 'system', timestamp: new Date().toISOString() }
          ])
          hardClose()
          return
        }

        // 3) 서버에서 닉네임 자동 할당
        if ('type' in raw && raw.type === 'assign') {
          const newName = (raw as AssignMsg).name
          setName(newName)
          setMessages((prev) => [
            ...prev,
            { type: 'system', text: `닉네임이 '${newName}'(으)로 지정되었습니다.`, sender: 'system', timestamp: new Date().toISOString() }
          ])
          return
        }

        // 4) 히스토리: 최근 50개를 한 번에 내려줌
        if ('type' in raw && raw.type === 'history') {
          const h = raw as HistoryMsg
          // 안전하게 시간순 정렬(서버에서 이미 정렬되어 오지만, 보수적으로)
          const sorted = [...h.messages].sort(
            (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          )
          setMessages(sorted)
          return
        }

        // 5) 일반 메시지(system/chat)
        const msg = raw as Msg
        if (msg.type === 'system' || msg.type === 'chat') {
          setMessages((prev) => [...prev, msg])
        }
      } catch {
        // ignore non-JSON
      }
    }
  }

  const disconnect = () => {
    hardClose()
  }

  useEffect(() => {
    // 마운트 시 자동 연결
    connect()
    return () => disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const send = (e: React.FormEvent) => {
    e.preventDefault()
    const ws = wsRef.current
    const text = input.trim()
    if (!ws || ws.readyState !== WebSocket.OPEN || !text) return

    // 백엔드가 순수 텍스트도 지원하지만,
    // 앞으로 확장을 위해 JSON 형태로 전송(타입 포함)
    const payload = JSON.stringify({ type: 'chat', text })
    ws.send(payload)
    setInput('')
  }

  return (
    <div className="wrap">
      <header>
        <strong>미니 채팅</strong>
        <span style={{ opacity: 0.8, marginLeft: 8 }}> {status}</span>

        <div style={{ marginTop: 6, opacity: 0.9, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <label>
            이름{' '}
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{ width: 160, padding: 6, borderRadius: 8, border: '1px solid #333', background: '#0f0f0f', color: '#eee' }}
            />
          </label>

          <label>
            방{' '}
            <input
              value={room}
              onChange={(e) => setRoom(e.target.value)}
              placeholder="lobby"
              style={{ width: 160, padding: 6, borderRadius: 8, border: '1px solid #333', background: '#0f0f0f', color: '#eee' }}
            />
          </label>

          <button onClick={connect}>연결/재연결</button>
          <button onClick={disconnect}>연결 종료</button>
        </div>
      </header>

      <div className="container">
        <div id="log">
          {messages.map((m, i) => (
            <div key={i} className={m.type === 'system' ? 'sys' : 'msg'}>
              {m.type === 'system' ? (
                <>
                  <span className="time">{formatTime(m.timestamp)}</span> {m.text}
                </>
              ) : (
                <>
                  <span className={m.sender === name ? 'me' : 'them'}>[{m.sender}]</span>
                  <span className="time">{formatTime(m.timestamp)}</span> {m.text}
                </>
              )}
            </div>
          ))}
          <div ref={logEndRef} />
        </div>

        <aside className="sidebar">
          <div className="users-header">
            <strong>접속자 ({users.length})</strong>
          </div>
          <div className="users-list">
            {users.map((user, i) => (
              <div key={i} className="user-item">
                <span className="user-dot">●</span> {user}
              </div>
            ))}
          </div>
        </aside>
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
