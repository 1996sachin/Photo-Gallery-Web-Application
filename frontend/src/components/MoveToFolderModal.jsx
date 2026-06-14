import { useState, useEffect } from 'react'
import { X, Folder, ChevronRight, Check } from 'lucide-react'
import { api } from '../hooks/useAuth'
import toast from 'react-hot-toast'

export default function MoveToFolderModal({ selection, onMoved, onClose }) {
  const [albums, setAlbums] = useState([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [selectedId, setSelectedId] = useState(null)

  useEffect(() => {
    load()
  }, [])

  const load = async () => {
    try {
      const { data } = await api.get('/api/albums/')
      setAlbums(data)
    } catch {
      toast.error('Failed to load folders')
    } finally {
      setLoading(false)
    }
  }

  const handleMove = async () => {
    setBusy(true)
    try {
      await onMoved(selectedId)
      toast.success('Memories moved!')
      onClose()
    } catch {
      toast.error('Move failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="card" onClick={e => e.stopPropagation()} style={{ width: '100%', maxWidth: 420, padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontFamily: 'var(--serif)', fontSize: 19 }}>Move to Folder</h2>
          <button className="btn btn-icon" onClick={onClose}><X size={18} /></button>
        </div>

        <p style={{ fontSize: 13, color: 'var(--c-brown-lt)', marginBottom: 16 }}>
          Select a destination for {selection.length} memories.
        </p>

        <div style={{ 
          maxHeight: 300, overflowY: 'auto', border: '1px solid var(--c-border)', 
          borderRadius: 10, background: 'var(--c-surface2)' 
        }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: 'center' }}><div className="spinner" /></div>
          ) : albums.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--c-brown-lt)', fontSize: 13 }}>No folders found.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div 
                onClick={() => setSelectedId(null)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px',
                  cursor: 'pointer', borderBottom: '1px solid var(--c-border)',
                  background: selectedId === null ? 'rgba(200,150,60,0.1)' : 'transparent'
                }}
              >
                <Folder size={16} color="var(--c-brown-lt)" />
                <span style={{ flex: 1, fontSize: 14 }}>Root (No Album)</span>
                {selectedId === null && <Check size={14} color="var(--c-gold)" />}
              </div>
              {albums.map(album => (
                <div 
                  key={album.id}
                  onClick={() => setSelectedId(album.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px',
                    cursor: 'pointer', borderBottom: '1px solid var(--c-border)',
                    background: selectedId === album.id ? 'rgba(200,150,60,0.1)' : 'transparent'
                  }}
                >
                  <Folder size={16} color="var(--c-gold)" />
                  <span style={{ flex: 1, fontSize: 14 }}>{album.title}</span>
                  {selectedId === album.id && <Check size={14} color="var(--c-gold)" />}
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 24, justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleMove} disabled={busy || loading}>
            {busy ? 'Moving...' : 'Move Here'}
          </button>
        </div>
      </div>
    </div>
  )
}
