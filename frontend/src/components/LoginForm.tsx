import React from 'react'

type LoginFormProps = {
  name: string
  room: string
  onChangeName: (value: string) => void
  onChangeRoom: (value: string) => void
  onSubmit: () => void
}

export default function LoginForm({
  name,
  room,
  onChangeName,
  onChangeRoom,
  onSubmit,
}: LoginFormProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit()
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>미니 채팅</h1>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="name">사용자명</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => onChangeName(e.target.value)}
              placeholder="사용자명"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="room">채팅방</label>
            <input
              id="room"
              type="text"
              value={room}
              onChange={(e) => onChangeRoom(e.target.value)}
              placeholder="채팅방"
            />
          </div>

          <button type="submit" className="join-btn">
            입장
          </button>
        </form>
      </div>
    </div>
  )
}
