import React, { useEffect, useRef } from 'react'

import { Msg } from '../types/chat'
import { formatTime } from '../utils/time'

type MessageListProps = {
  messages: Msg[]
  currentUser: string
}

export default function MessageList({ messages, currentUser }: MessageListProps) {
  const logEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  return (
    <div id="log">
      {messages.map((m, index) => (
        <div key={`${m.timestamp}-${index}`} className={m.type === 'system' ? 'sys' : 'msg'}>
          {m.type === 'system' ? (
            <>
              <span className="time">{formatTime(m.timestamp)}</span> {m.text}
            </>
          ) : m.type === 'image' ? (
            <>
              <span className={m.sender === currentUser ? 'me' : 'them'}>[{m.sender}]</span>
              <span className="time">{formatTime(m.timestamp)}</span>
              <div style={{ marginTop: 8 }}>
                <img
                  src={m.imageData}
                  alt="전송된 이미지"
                  style={{ maxWidth: '100%', maxHeight: '300px', borderRadius: 8 }}
                />
              </div>
              {m.text && <div style={{ marginTop: 4 }}>{m.text}</div>}
            </>
          ) : (
            <>
              <span className={m.sender === currentUser ? 'me' : 'them'}>[{m.sender}]</span>
              <span className="time">{formatTime(m.timestamp)}</span> {m.text}
            </>
          )}
        </div>
      ))}
      <div ref={logEndRef} />
    </div>
  )
}
