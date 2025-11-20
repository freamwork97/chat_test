import React from 'react'

type UsersSidebarProps = {
  users: string[]
}

export default function UsersSidebar({ users }: UsersSidebarProps) {
  return (
    <aside className="sidebar">
      <div className="users-header">
        <strong>접속자 ({users.length})</strong>
      </div>
      <div className="users-list">
        {users.map((user, index) => (
          <div key={`${user}-${index}`} className="user-item">
            <span className="user-dot">●</span> {user}
          </div>
        ))}
      </div>
    </aside>
  )
}
