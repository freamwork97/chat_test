import React from 'react'

import { ConnectionStatus } from '../types/chat'

type ChatHeaderProps = {
  name: string
  room: string
  status: ConnectionStatus
  onDisconnect: () => void
}

export default function ChatHeader({ name, room, status, onDisconnect }: ChatHeaderProps) {
  return (
    <header>
      <strong>미니 채팅</strong>
      <span style={{ opacity: 0.8, marginLeft: 8 }}> {status}</span>

      <div
        style={{
          marginTop: 6,
          opacity: 0.9,
          display: 'flex',
          gap: 8,
          flexWrap: 'wrap',
          alignItems: 'center',
        }}
      >
        <div style={{ fontSize: 14 }}>
          <strong>{name}</strong> @ <strong>{room}</strong>
        </div>
        <button onClick={onDisconnect}>연결 종료</button>
      </div>
    </header>
  )
}
