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
  const generateRandomName = () => {
    const adjectives = ['Swift', 'Brave', 'Bright', 'Merry', 'Lucky', 'Calm', 'Solar', 'Neon']
    const nouns = ['Fox', 'Tiger', 'Otter', 'Wave', 'Comet', 'Panda', 'Hawk', 'Quartz', 'Pixel', 'Breeze']
    const adjective = adjectives[Math.floor(Math.random() * adjectives.length)]
    const noun = nouns[Math.floor(Math.random() * nouns.length)]
    const number = Math.floor(Math.random() * 900 + 100)

    return `${adjective}${noun}${number}`
  }

  const handleGenerateName = () => {
    onChangeName(generateRandomName())
  }

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
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => onChangeName(e.target.value)}
                placeholder="사용자명"
                autoFocus
                style={{ flex: 1 }}
              />
              <button
                type="button"
                onClick={handleGenerateName}
                style={{
                  padding: '12px 14px',
                  borderRadius: 8,
                  background: '#262626',
                  border: '1px solid #333',
                  color: '#eee',
                  cursor: 'pointer',
                  fontSize: 14,
                  whiteSpace: 'nowrap',
                }}
              >
                랜덤 생성
              </button>
            </div>
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
