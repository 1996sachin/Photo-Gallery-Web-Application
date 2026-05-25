import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, BookImage, Plus, Trash2, Share2, Heart, Users, Upload } from 'lucide-react'
import { api } from '../hooks/useAuth'
import MediaCard from '../components/MediaCard'
import UploadModal from '../components/UploadModal'
import toast from 'react-hot-toast'

// ─── Albums ──────────────────────────────────────────────
export function AlbumsPage() {
  const navigate = useNavigate()
  const { id: activeAlbumId } = useParams()
  const [albums, setAlbums] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ title: '', description: '' })
  const [items, setItems] = useState([])
  const [mediaLoading, setMediaLoading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)

  useEffect(() => { load() }, [])
  useEffect(() => { if (activeAlbumId) loadAlbumMedia(activeAlbumId) }, [activeAlbumId])

  const load = async () => {
    setLoading(true)
    try { const { data } = await api.get('/api/albums/'); setAlbums(data) }
    finally { setLoading(false) }
  }

  const loadAlbumMedia = async albumId => {
    setMediaLoading(true)
    try {
      const { data } = await api.get('/api/media/', { params: { album_id: albumId, per_page: 100 } })
      setItems(data)
    } finally {
      setMediaLoading(false)
    }
  }

  const create = async () => {
    if (!form.title.trim()) return
    const { data } = await api.post('/api/albums/', { title: form.title.trim(), description: form.description.trim() || null })
    setAlbums(p => [data, ...p])
    setForm({ title: '', description: '' })
    setCreating(false)
    toast.success('Album created!')
  }

  const remove = async id => {
    if (!confirm('Delete this album? Photos inside are kept.')) return
    await api.delete(`/api/albums/${id}`)
    setAlbums(p => p.filter(a => a.id !== id))
    if (activeAlbumId === id) navigate('/albums')
    toast.success('Album deleted')
  }

  const share = async (event, album) => {
    event?.stopPropagation()
    const { data } = await api.post(`/api/albums/${album.id}/share`)
    if (data.is_shared && data.share_token) {
      await navigator.clipboard.writeText(`${window.location.origin}/shared/${data.share_token}`).catch(() => {})
      toast.success('Share link copied to clipboard!')
    } else {
      toast.success('Album is now private')
    }
    setAlbums(p => p.map(a => a.id === album.id ? { ...a, ...data } : a))
  }

  const activeAlbum = albums.find(a => a.id === activeAlbumId)

  if (activeAlbumId) {
    return (
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22, gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
            <button className="btn btn-icon btn" style={{ width: 34, height: 34 }} onClick={() => navigate('/albums')} title="Back to albums">
              <ArrowLeft size={15} />
            </button>
            <div style={{ minWidth: 0 }}>
              <h1 className="page-title" style={{ marginBottom: 2 }}>{activeAlbum?.title || 'Album'}</h1>
              {activeAlbum?.description && <p style={{ fontSize: 13, color: 'var(--c-brown-lt)' }}>{activeAlbum.description}</p>}
            </div>
          </div>
          <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
            <Upload size={14} /> Add Photos
          </button>
        </div>

        {mediaLoading ? (
          <div className="empty-state"><div className="spinner" /></div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <BookImage size={56} />
            <h3>No photos in this album yet</h3>
            <p>Upload photos or videos here to add them to this album.</p>
            <button className="btn btn-primary" onClick={() => setShowUpload(true)}><Upload size={14} /> Add Photos</button>
          </div>
        ) : (
          <div className="media-grid">{items.map(item => <MediaCard key={item.id} item={item} />)}</div>
        )}

        {showUpload && (
          <UploadModal
            albumId={activeAlbumId}
            onUploaded={() => loadAlbumMedia(activeAlbumId)}
            onClose={() => setShowUpload(false)}
          />
        )}
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22 }}>
        <h1 className="page-title">Albums</h1>
        <button className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={14} /> New Album</button>
      </div>

      {creating && (
        <div className="card" style={{ padding: 20, marginBottom: 18, display: 'flex', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label className="label">Album name</label>
            <input className="input" placeholder="e.g. Summer 2025" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} onKeyDown={e => e.key === 'Enter' && create()} autoFocus />
          </div>
          <div style={{ flex: 1 }}>
            <label className="label">Description (optional)</label>
            <input className="input" placeholder="A short description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          </div>
          <button className="btn btn-primary" onClick={create}>Create</button>
          <button className="btn btn-ghost" onClick={() => setCreating(false)}>Cancel</button>
        </div>
      )}

      {loading ? <div className="empty-state"><div className="spinner" /></div>
      : albums.length === 0 ? (
        <div className="empty-state"><BookImage size={56} /><h3>No albums yet</h3><p>Create albums to organise memories by event, trip, or year.</p></div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 14 }}>
          {albums.map(album => (
            <div key={album.id} className="card" onClick={() => navigate(`/albums/${album.id}`)} style={{ padding: 18, transition: 'box-shadow 0.15s', cursor: 'pointer' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 6 }}>
                <div style={{ fontFamily: 'var(--serif)', fontSize: 16, fontWeight: 500, flex: 1, lineHeight: 1.3 }}>{album.title}</div>
                <div style={{ display: 'flex', gap: 3, flexShrink: 0 }}>
                  <button className="btn btn-icon btn" style={{ width: 28, height: 28 }} title={album.is_shared ? 'Sharing on — click to disable' : 'Share album'} onClick={e => share(e, album)}>
                    <Share2 size={12} color={album.is_shared ? 'var(--c-gold)' : undefined} />
                  </button>
                  <button className="btn btn-icon btn" style={{ width: 28, height: 28 }} onClick={e => { e.stopPropagation(); remove(album.id) }}>
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
              {album.description && <p style={{ fontSize: 12.5, color: 'var(--c-brown-lt)', marginBottom: 8, lineHeight: 1.5 }}>{album.description}</p>}
              <div style={{ fontSize: 11.5, color: 'var(--c-brown-lt)', marginTop: 6 }}>{new Date(album.created_at).toLocaleDateString()}</div>
              {album.is_shared && <div className="badge" style={{ marginTop: 8 }}>Shared</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Favorites ───────────────────────────────────────────
export function FavoritesPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/api/media/', { params: { favorites_only: true, per_page: 100 } })
      .then(({ data }) => setItems(data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="empty-state"><div className="spinner" /></div>

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 22 }}>
        <Heart size={20} color="var(--c-gold)" fill="var(--c-gold)" />
        <h1 className="page-title">Favorites</h1>
        {items.length > 0 && <span style={{ fontSize: 13.5, color: 'var(--c-brown-lt)', fontFamily: 'var(--sans)', fontWeight: 400 }}>{items.length} memories</span>}
      </div>
      {items.length === 0
        ? <div className="empty-state"><Heart size={56} /><h3>No favorites yet</h3><p>Tap the heart on any photo or video to add it here.</p></div>
        : <div className="media-grid">{items.map(item => <MediaCard key={item.id} item={item} />)}</div>
      }
    </div>
  )
}

// ─── People ──────────────────────────────────────────────
export function PeoplePage() {
  const [people, setPeople] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')

  useEffect(() => { load() }, [])
  const load = async () => {
    setLoading(true)
    try { const { data } = await api.get('/api/people/'); setPeople(data) }
    finally { setLoading(false) }
  }

  const create = async () => {
    if (!name.trim()) return
    const { data } = await api.post('/api/people/', { name: name.trim() })
    setPeople(p => [...p, data])
    setName(''); setCreating(false)
    toast.success('Person added!')
  }

  const initials = n => n.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
  const colors = ['#c8963c','#7a9e7e','#c87878','#7878c8','#c87878']

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22 }}>
        <h1 className="page-title">People</h1>
        <button className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={14} /> Add Person</button>
      </div>

      {creating && (
        <div className="card" style={{ padding: 16, marginBottom: 16, display: 'flex', gap: 9, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label className="label">Name</label>
            <input className="input" placeholder="e.g. Mom, Grandpa, Best Friend" value={name} onChange={e => setName(e.target.value)} onKeyDown={e => e.key === 'Enter' && create()} autoFocus />
          </div>
          <button className="btn btn-primary" onClick={create}>Add</button>
          <button className="btn btn-ghost" onClick={() => setCreating(false)}>Cancel</button>
        </div>
      )}

      {loading ? <div className="empty-state"><div className="spinner" /></div>
      : people.length === 0 ? (
        <div className="empty-state"><Users size={56} /><h3>No people added</h3><p>Add your loved ones to tag them in photos and videos.</p></div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 12 }}>
          {people.map((p, i) => (
            <div key={p.id} className="card" style={{ padding: 18, textAlign: 'center' }}>
              <div style={{
                width: 52, height: 52, borderRadius: '50%', margin: '0 auto 10px',
                background: colors[i % colors.length] + '22',
                border: `2px solid ${colors[i % colors.length]}44`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 700, fontSize: 16, color: colors[i % colors.length],
              }}>{initials(p.name)}</div>
              <div style={{ fontFamily: 'var(--serif)', fontSize: 14, fontWeight: 500 }}>{p.name}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AlbumsPage
