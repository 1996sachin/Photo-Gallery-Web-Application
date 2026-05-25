import { useEffect, useState } from 'react'
import { Activity, Clock3, Mail, RotateCw, UserRound } from 'lucide-react'
import { api } from '../hooks/useAuth'
import toast from 'react-hot-toast'

const formatDuration = seconds => {
  const total = Math.max(0, Number(seconds) || 0)
  if (total < 60) return `${total}s`
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  if (hours) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

const parseServerTime = value => {
  if (!value) return null
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)
}

const formatWhen = value => {
  const date = parseServerTime(value)
  return date ? date.toLocaleString() : 'Never'
}

const activeOnlineSeconds = user => {
  const total = Math.max(0, Number(user.total_online_seconds) || 0)
  if (!user.online) return total
  const lastSeen = parseServerTime(user.last_seen_at)
  if (!lastSeen) return total
  const liveSeconds = Math.max(0, Math.floor((Date.now() - lastSeen.getTime()) / 1000))
  return total + Math.min(liveSeconds, 120)
}

const initials = name => (name || '?')
  .split(' ')
  .filter(Boolean)
  .map(w => w[0])
  .join('')
  .slice(0, 2)
  .toUpperCase()

export default function UsersActivityPage() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [filter, setFilter] = useState('all')

  const load = async (quiet = false) => {
    quiet ? setRefreshing(true) : setLoading(true)
    try {
      const { data } = await api.get('/api/auth/users/activity')
      setUsers(data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not load user activity')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    load()
    const id = window.setInterval(() => load(true), 30000)
    return () => window.clearInterval(id)
  }, [])

  const onlineCount = users.filter(u => u.online).length
  const visibleUsers = filter === 'online' ? users.filter(u => u.online) : users

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22, gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h1 className="page-title">Users</h1>
          <p style={{ marginTop: 5, color: 'var(--c-brown-lt)', fontSize: 13.5 }}>
            Monitor online status, last activity, and accumulated online time.
          </p>
        </div>
        <button className="btn btn-ghost" onClick={() => load(true)} disabled={refreshing}>
          {refreshing ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <RotateCw size={14} />}
          Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 16 }}>
        <button
          type="button"
          className="card"
          onClick={() => setFilter('online')}
          style={{
            padding: 16,
            textAlign: 'left',
            cursor: 'pointer',
            borderColor: filter === 'online' ? 'var(--c-gold)' : 'var(--c-border)',
            background: filter === 'online' ? 'var(--c-surface2)' : 'var(--c-surface)',
          }}
        >
          <div style={{ fontSize: 12, color: 'var(--c-brown-lt)' }}>Online now</div>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 28, marginTop: 4 }}>{onlineCount}</div>
        </button>
        <button
          type="button"
          className="card"
          onClick={() => setFilter('all')}
          style={{
            padding: 16,
            textAlign: 'left',
            cursor: 'pointer',
            borderColor: filter === 'all' ? 'var(--c-gold)' : 'var(--c-border)',
            background: filter === 'all' ? 'var(--c-surface2)' : 'var(--c-surface)',
          }}
        >
          <div style={{ fontSize: 12, color: 'var(--c-brown-lt)' }}>Total users</div>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 28, marginTop: 4 }}>{users.length}</div>
        </button>
      </div>

      {loading ? <div className="empty-state"><div className="spinner" /></div>
      : users.length === 0 ? (
        <div className="empty-state"><UserRound size={56} /><h3>No users yet</h3><p>User activity appears here after accounts are created.</p></div>
      ) : visibleUsers.length === 0 ? (
        <div className="empty-state"><UserRound size={56} /><h3>No online users</h3><p>Click Total users to see everyone.</p></div>
      ) : (
        <div style={{ display: 'grid', gap: 10 }}>
          {visibleUsers.map(user => (
            <div key={user.id} className="card" style={{ padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 18, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', minWidth: 0, flex: '1 1 260px' }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: '50%', flexShrink: 0,
                    background: user.online ? 'rgba(122,158,126,.22)' : 'var(--c-surface2)',
                    border: `1px solid ${user.online ? 'rgba(122,158,126,.45)' : 'var(--c-border)'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    overflow: 'hidden', fontWeight: 700, color: user.online ? '#4f8354' : 'var(--c-brown-lt)',
                  }}>
                    {user.avatar_url ? <img src={user.avatar_url} alt={user.display_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : initials(user.display_name)}
                  </div>

                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 14.5, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user.display_name}</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 6, fontSize: 12.5, color: 'var(--c-brown-lt)', minWidth: 0 }}>
                      <Mail size={12} />
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user.email}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 6, fontSize: 12.5, color: 'var(--c-brown-lt)' }}>
                      <Activity size={12} /> {user.last_activity || 'No activity yet'}
                    </div>
                  </div>
                </div>

                <div style={{
                  minWidth: 220,
                  display: 'grid',
                  gap: 8,
                  justifyItems: 'end',
                  textAlign: 'right',
                }}>
                  <span className="badge" style={{
                    color: user.online ? '#4f8354' : 'var(--c-brown-lt)',
                    fontSize: 12.5,
                    padding: '5px 10px',
                  }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: user.online ? '#5a9a5a' : 'var(--c-border-dk)' }} />
                    {user.online ? 'Online now' : 'Offline'}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--c-brown)', fontSize: 13, fontWeight: 700 }}>
                    <Clock3 size={13} /> Online time: {formatDuration(activeOnlineSeconds(user))}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--c-brown-lt)' }}>
                    Last seen: {formatWhen(user.last_seen_at)}
                  </div>
                </div>
              </div>

              <div style={{
                marginTop: 14,
                paddingTop: 12,
                borderTop: '1px solid var(--c-border)',
                minWidth: 0,
              }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--c-brown)', marginBottom: 8 }}>Activity logs</div>
                {user.recent_events?.length ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 6 }}>
                    {user.recent_events.map((event, index) => (
                      <div key={`${user.id}-${event.created_at}-${index}`} style={{
                        fontSize: 12,
                        color: 'var(--c-brown-lt)',
                        padding: '8px 10px',
                        borderRadius: 8,
                        background: 'var(--c-surface2)',
                        border: '1px solid var(--c-border)',
                      }}>
                        <span style={{ color: 'var(--c-brown)', fontWeight: 600 }}>{event.activity}</span>
                        <span> · {formatWhen(event.created_at)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: 12, color: 'var(--c-brown-lt)' }}>No recorded events</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
