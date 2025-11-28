import React, { useState } from 'react'

import ChatHeader from './components/ChatHeader'
import LoginForm from './components/LoginForm'
import MessageComposer from './components/MessageComposer'
import MessageList from './components/MessageList'
import UsersSidebar from './components/UsersSidebar'
import { useChatConnection } from './hooks/useChatConnection'

export default function App() {
  const [name, setName] = useState('')
  const [room, setRoom] = useState('')

  const {
    status,
    messages,
    users,
    isConnected,
    connect,
    disconnect,
    sendChatMessage,
    sendImageMessage,
    uploadFile,
  } = useChatConnection({ onNameAssigned: setName })

  const handleJoin = () => {
    const trimmedName = name.trim()
    const trimmedRoom = room.trim()

    if (!trimmedName) {
      alert('사용자명을 입력하세요.')
      return
    }
    if (!trimmedRoom) {
      alert('채팅방을 입력하세요.')
      return
    }

    setName(trimmedName)
    setRoom(trimmedRoom)
    connect({ name: trimmedName, room: trimmedRoom })
  }

  const handleSendFile = async (file: File, note?: string) => {
    if (!isConnected || !name || !room) {
      return
    }
    try {
      await uploadFile({ file, sender: name, room, text: note })
    } catch (err) {
      const msg = err instanceof Error ? err.message : '파일 업로드에 실패했습니다.'
      alert(msg)
    }
  }

  return (
    <div className="wrap">
      {!isConnected ? (
        <LoginForm
          name={name}
          room={room}
          onChangeName={setName}
          onChangeRoom={setRoom}
          onSubmit={handleJoin}
        />
      ) : (
        <>
          <ChatHeader name={name} room={room} status={status} onDisconnect={disconnect} />

          <div className="container">
            <MessageList messages={messages} currentUser={name} />
            <UsersSidebar users={users} />
          </div>

          <MessageComposer
            disabled={!isConnected}
            onSendMessage={sendChatMessage}
            onSendImage={(imageData) => sendImageMessage({ imageData })}
            onSendFile={handleSendFile}
          />
        </>
      )}
    </div>
  )
}
