import { useCallback, useRef, useState } from 'react'

import {
  AssignMsg,
  ConnectionStatus,
  ErrorMsg,
  HistoryMsg,
  Msg,
  UsersMsg,
} from '../types/chat'

type ConnectArgs = {
  name: string
  room: string
}

type UseChatConnectionOptions = {
  onNameAssigned?: (nextName: string) => void
}

type SendImageArgs = {
  imageData: string
  text?: string
}

export function useChatConnection(options: UseChatConnectionOptions = {}) {
  const { onNameAssigned } = options

  const [status, setStatus] = useState<ConnectionStatus>('연결 중')
  const [messages, setMessages] = useState<Msg[]>([])
  const [users, setUsers] = useState<string[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const hardClose = useCallback(() => {
    if (wsRef.current) {
      try {
        wsRef.current.close()
      } catch {
        // ignore
      }
      wsRef.current = null
    }
  }, [])

  const handleSystemMessage = useCallback((text: string) => {
    setMessages((prev) => [
      ...prev,
      { type: 'system', text, sender: 'system', timestamp: new Date().toISOString() },
    ])
  }, [])

  const connect = useCallback(
    ({ name, room }: ConnectArgs) => {
      const trimmedName = name.trim()
      const trimmedRoom = room.trim()
      if (!trimmedName || !trimmedRoom) {
        return
      }

      hardClose()
      setStatus('연결 중')
      setMessages([])
      setUsers([])
      setIsConnected(true)

      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const url = `${proto}://${window.location.host}/ws?name=${encodeURIComponent(
        trimmedName
      )}&room=${encodeURIComponent(trimmedRoom)}`

      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => setStatus('연결됨')
      ws.onclose = () => {
        setStatus('연결 종료')
      }
      ws.onerror = () => setStatus('오류')

      ws.onmessage = (event) => {
        try {
          const raw = JSON.parse(event.data) as UsersMsg | ErrorMsg | AssignMsg | HistoryMsg | Msg

          if (raw.type === 'users') {
            setUsers(raw.users)
            return
          }

          if (raw.type === 'error') {
            setStatus('오류')
            handleSystemMessage(raw.text)
            hardClose()
            return
          }

          if (raw.type === 'assign') {
            onNameAssigned?.(raw.name)
            handleSystemMessage(`닉네임이 '${raw.name}'(으)로 지정되었습니다.`)
            return
          }

          if (raw.type === 'history') {
            const sorted = [...raw.messages].sort(
              (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
            )
            setMessages(sorted)
            return
          }

          if (raw.type === 'system' || raw.type === 'chat' || raw.type === 'image') {
            setMessages((prev) => [...prev, raw])
          }
        } catch {
          // ignore malformed payloads
        }
      }
    },
    [handleSystemMessage, hardClose, onNameAssigned]
  )

  const disconnect = useCallback(() => {
    hardClose()
    setIsConnected(false)
    setStatus('연결 종료')
  }, [hardClose])

  const sendChatMessage = useCallback((text: string) => {
    const ws = wsRef.current
    const trimmed = text.trim()
    if (!ws || ws.readyState !== WebSocket.OPEN || !trimmed) {
      return
    }
    ws.send(JSON.stringify({ type: 'chat', text: trimmed }))
  }, [])

  const sendImageMessage = useCallback(({ imageData, text }: SendImageArgs) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return
    }
    ws.send(
      JSON.stringify({
        type: 'image',
        imageData,
        text: text ?? '',
      })
    )
  }, [])

  return {
    status,
    messages,
    users,
    isConnected,
    connect,
    disconnect,
    sendChatMessage,
    sendImageMessage,
  }
}
