import { useEffect, useState } from 'react'
import { Trash2, RotateCcw, Trash, AlertTriangle } from 'lucide-react'
import { api, useAuthStore } from '../hooks/useAuth'
import MediaCard from '../components/MediaCard'
import toast from 'react-hot-toast'

export default function TrashPage() {
  const { user } = useAuthStore()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [selection, setSelection] = useState([])
  const [acting, setActing] = useState(false)

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/api/media/trash/list')
      setItems(data)
    } catch { toast.error('Failed to load trash') }
    finally { setLoading(false) }
  }

  const toggleSelect = id => {
    setSelection(s => s.includes(id) ? s.filter(i => i !== id) : [...s, id])
  }

  const onRestore = async () => {
    const ids = selection.length > 0 ? selection : items.map(i => i.id)
    if (ids.length === 0) return
    setActing(true)
    try {
      await api.post('/api/media/trash/restore', { ids })
      toast.success('Restored successfully')
      setItems(p => p.filter(i => !ids.includes(i.id)))
      setSelection([])
    } catch { toast.error('Restore failed') }
    finally { setActing(false) }
  }

  const onPermanentDelete = async () => {
    const ids = selection.length > 0 ? selection : []
    if (ids.length === 0) return
    if (!confirm(`Permanently delete ${ids.length} memories? This cannot be undone.`)) return
    
    let mfa_code = null
    if (user?.mfa_enabled) {
      mfa_code = prompt('Enter your 6-digit MFA code to confirm permanent deletion:')
      if (!mfa_code) return
    }

    setActing(true)
    try {
      await api.delete('/api/media/trash/permanent', { data: { ids, mfa_code } })
      toast.success('Deleted permanently')
      setItems(p => p.filter(i => !ids.includes(i.id)))
      setSelection([])
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Delete failed')
    } finally {
      setActing(false)
    }
  }

  const onEmptyTrash = async () => {
    if (items.length === 0) return
    if (!confirm('Permanently delete ALL items in trash? This cannot be undone.')) return
    
    let mfa_code = null
    if (user?.mfa_enabled) {
      mfa_code = prompt('Enter your 6-digit MFA code to confirm emptying trash:')
      if (!mfa_code) return
    }

    setActing(true)
    try {
      await api.delete('/api/media/trash/permanent', { data: { ids: items.map(i => i.id), mfa_code } })
      toast.success('Trash emptied')
      setItems([])
      setSelection([])
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Empty trash failed')
    } finally {
      setActing(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22 }}>
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Trash2 size={22} color="var(--c-brown-lt)" /> Trash
        </h1>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-ghost" onClick={onEmptyTrash} disabled={loading || acting || items.length === 0}>
            Empty Trash
          </button>
          <button className="btn btn-primary" onClick={onRestore} disabled={loading || acting || items.length === 0}>
            <RotateCcw size={14} /> Restore {selection.length > 0 ? 'Selected' : 'All'}
          </button>
        </div>
      </div>

      {items.length > 0 && (
        <div style={{
          background: 'rgba(200,150,60,0.1)', border: '1px solid rgba(200,150,60,0.2)',
          borderRadius: 12, padding: '12px 16px', marginBottom: 24,
          display: 'flex', alignItems: 'center', gap: 12, color: 'var(--c-brown)'
        }}>
          <AlertTriangle size={18} color="var(--c-gold)" />
          <p style={{ fontSize: 13, lineHeight: 1.5 }}>
            Items in trash will still be stored on the server. Empty the trash to permanently delete them.
          </p>
        </div>
      )}

      {loading ? (
        <div className="empty-state"><div className="spinner" /></div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <Trash size={54} color="var(--c-brown-lt)" opacity={0.5} />
          <h3>Trash is empty</h3>
          <p>Memories you delete will appear here for 30 days before being permanently removed.</p>
        </div>
      ) : (
        <>
          <div className="media-grid">
            {items.map(item => (
              <MediaCard 
                key={item.id} 
                item={item} 
                selected={selection.includes(item.id)}
                onSelect={toggleSelect}
                selectMode={true}
              />
            ))}
          </div>
          
          {selection.length > 0 && (
            <div style={{
              position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)',
              background: '#2c1e0f', color: '#fff', padding: '12px 20px',
              borderRadius: 16, display: 'flex', alignItems: 'center', gap: 16,
              boxShadow: '0 10px 40px rgba(0,0,0,0.4)', zIndex: 100
            }}>
              <span style={{ fontSize: 13.5, fontWeight: 600 }}>{selection.length} selected</span>
              <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.2)' }} />
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-ghost" onClick={onRestore} disabled={acting} style={{ color: '#fff', padding: '6px 10px' }}>
                  <RotateCcw size={15} /> Restore
                </button>
                <button className="btn btn-ghost" onClick={onPermanentDelete} disabled={acting} style={{ color: '#ff7a7a', padding: '6px 10px' }}>
                  <Trash size={15} /> Delete Permanently
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
