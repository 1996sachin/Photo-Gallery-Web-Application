import { useEffect } from 'react'
import { useAuthStore } from './useAuth'
import toast from 'react-hot-toast'

export function useNotifications() {
  const { user } = useAuthStore()

  useEffect(() => {
    if (!user) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const apiHost = apiUrl.replace(/^https?:\/\//, '')
    const host = window.location.hostname === 'localhost' ? apiHost : window.location.host
    const ws = new WebSocket(`${protocol}//${host}/ws`)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'new_comment') {
          toast((t) => (
            <div onClick={() => { toast.dismiss(t.id); window.location.hash = `/media/${data.media_id}` }} style={{ cursor: 'pointer' }}>
              <div style={{ fontWeight: 600, fontSize: 13 }}>New comment from {data.author}</div>
              <div style={{ fontSize: 12, opacity: 0.8 }}>{data.text}</div>
            </div>
          ), { icon: '💬', duration: 5000 })
        }
      } catch (err) {
        console.error('WS Error:', err)
      }
    }

    ws.onerror = (err) => console.error('WebSocket Error', err)
    
    return () => ws.close()
  }, [user])
}
