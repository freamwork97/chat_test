import React, { useRef, useState } from 'react'

type MessageComposerProps = {
  disabled?: boolean
  onSendMessage: (text: string) => void
  onSendImage: (imageData: string) => void
  onSendFile: (file: File, note?: string) => void
}

export default function MessageComposer({
  disabled,
  onSendMessage,
  onSendImage,
  onSendFile,
}: MessageComposerProps) {
  const [text, setText] = useState('')
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const archiveInputRef = useRef<HTMLInputElement | null>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || disabled) {
      return
    }
    onSendMessage(trimmed)
    setText('')
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || disabled) {
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      const base64Data = reader.result as string
      onSendImage(base64Data)
    }
    reader.readAsDataURL(file)

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleArchiveChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || disabled) {
      return
    }
    const note = text.trim() || undefined
    onSendFile(file, note)

    if (archiveInputRef.current) {
      archiveInputRef.current.value = ''
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={text}
        placeholder="메시지를 입력하세요.."
        onChange={(e) => setText(e.target.value)}
        autoComplete="off"
        disabled={disabled}
      />
      <button type="submit" disabled={disabled}>
        전송
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        style={{ display: 'none' }}
        disabled={disabled}
      />
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        title="이미지 전송"
        disabled={disabled}
      >
        이미지
      </button>
      <input
        ref={archiveInputRef}
        type="file"
        accept=".zip,.tar,.gz,.tgz,.bz2,.7z,.rar"
        onChange={handleArchiveChange}
        style={{ display: 'none' }}
        disabled={disabled}
      />
      <button
        type="button"
        onClick={() => archiveInputRef.current?.click()}
        title="압축파일 전송"
        disabled={disabled}
      >
        압축파일
      </button>
    </form>
  )
}
