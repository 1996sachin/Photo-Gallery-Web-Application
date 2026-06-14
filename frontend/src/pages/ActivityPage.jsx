import { useState, useEffect } from 'react'
import { Activity, Clock, User, Shield, Info, Image as ImageIcon, Trash2, Heart, MessageCircle } from 'lucide-react'
import { api } from '../hooks/useAuth'

export default function ActivityPage() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    load()
  }, [])

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/api/activity/')
      setLogs(data)
    } finally {
      setLoading(false)
    }
  }

  const getIcon = (action) => {
    if (action.includes('delete')) return <Trash2 size={16} color="#ff7a7a" />
    if (action.includes('favorite')) return <Heart size={16} color="var(--c-gold)" />
    if (action.includes('comment')) return <MessageCircle size={16} color="var(--c-gold)" />
    if (action.includes('mfa')) return <Shield size={16} color="#5a9a5a" />
    if (action.includes('upload')) return <ImageIcon size={16} color="var(--c-gold)" />
    return <Info size={16} color="var(--c-brown-lt)" />
  }

  const formatAction = (action) => {
    return action.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 26 }}>
        <Activity size={22} color="var(--c-gold)" />
        <h1 className="page-title">Recent Activity</h1>
      </div>

      {loading ? (
        <div className="empty-state"><div className="spinner" /></div>
      ) : logs.length === 0 ? (
        <div className="empty-state">
          <Activity size={56} />
          <h3>No activity recorded</h3>
          <p>Actions you take on your memories will appear here.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {logs.map((log, i) => (
              <div key={log.id} style={{
                display: 'flex', gap: 16, padding: '16px 20px',
                borderBottom: i === logs.length - 1 ? 'none' : '1px solid var(--c-border)',
                background: i % 2 === 0 ? 'transparent' : 'rgba(200,150,60,0.03)'
              }}>
                <div style={{
                  width: 36, height: 36, borderRadius: 10, flexShrink: 0,
                  background: 'var(--c-surface)', border: '1px solid var(--c-border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  {getIcon(log.action)}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{formatAction(log.action)}</div>
                    <div style={{ fontSize: 11.5, color: 'var(--c-brown-lt)', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Clock size={11} />
                      {new Date(log.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--c-brown-lt)' }}>
                    {Object.keys(log.details).length > 0 ? (
                      <pre style={{ 
                        margin: '8px 0 0', padding: 8, background: 'var(--c-surface)', 
                        borderRadius: 6, fontSize: 11, color: 'var(--c-brown)',
                        whiteSpace: 'pre-wrap'
                      }}>
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    ) : (
                      'No additional details provided.'
                    )}
                  </div>
                  {log.ip_address && (
                    <div style={{ fontSize: 10, color: 'var(--c-brown-lt)', marginTop: 8, opacity: 0.6 }}>
                      IP: {log.ip_address}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
