export type ChatMsg = {
  type: 'chat'
  text: string
  sender: string
  timestamp: string
  room?: string
}

export type SystemMsg = {
  type: 'system'
  text: string
  sender: 'system'
  timestamp: string
  room?: string
}

export type ImageMsg = {
  type: 'image'
  text?: string
  imageData: string
  sender: string
  timestamp: string
  room?: string
}

export type FileMsg = {
  type: 'file'
  text?: string
  fileName: string
  fileUrl: string
  fileSize: number
  sender: string
  timestamp: string
  room?: string
}

export type UsersMsg = {
  type: 'users'
  users: string[]
}

export type ErrorMsg = {
  type: 'error'
  text: string
  reason?: string
}

export type HistoryMsg = {
  type: 'history'
  room: string
  messages: Array<ChatMsg | SystemMsg | ImageMsg | FileMsg>
}

export type AssignMsg = {
  type: 'assign'
  name: string
  room?: string
}

export type Msg = ChatMsg | SystemMsg | ImageMsg | FileMsg

export type ConnectionStatus = '연결 중' | '연결됨' | '연결 종료' | '오류'
