import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Heart, Download, Pencil, Trash2, MessageCircle, Send, MapPin, Maximize2, Minimize2 } from 'lucide-react'
import { api } from '../hooks/useAuth'
import { useAuthStore } from '../hooks/useAuth'
import { useMediaStore } from '../stores/mediaStore'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import PhotoEditor from '../components/PhotoEditor'
import VideoEditor from '../components/VideoEditor'

export default function MediaViewPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const removeItem = useMediaStore(s => s.removeItem)
  const [item, setItem] = useState(null)
  const [loading, setLoading] = useState(true)
  const [fav, setFav] = useState(false)
  const [comments, setComments] = useState([])
  const [commentText, setCommentText] = useState('')
  const [editing, setEditing] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const mediaFrameRef = useRef(null)

  useEffect(() => { loadMedia(); loadComments() }, [id])

  useEffect(() => {
    const onFullscreenChange = () => setIsFullscreen(document.fullscreenElement === mediaFrameRef.current)
    document.addEventListener('fullscreenchange', onFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', onFullscreenChange)
  }, [])

  const loadMedia = async () => {
    setLoading(true)
    try {
      const { data } = await api.get(`/api/media/${id}`)
      setItem(data); setFav(data.is_favorite)
    } catch { toast.error('Not found'); navigate('/') }
    finally { setLoading(false) }
  }

  const loadComments = async () => {
    try { const { data } = await api.get(`/api/comments/${id}`); setComments(data) } catch {}
  }

  const toggleFav = async () => {
    const { data } = await api.patch(`/api/media/${id}/favorite`)
    setFav(data.is_favorite)
    toast.success(data.is_favorite ? '❤️ Favorited' : 'Removed from favorites')
  }

  const postComment = async () => {
    if (!commentText.trim()) return
    const { data } = await api.post('/api/comments/', { media_id: id, body: commentText.trim() })
    setComments(p => [...p, { ...data, author_id: user.id }])
    setCommentText('')
  }

  const deleteMedia = async () => {
    if (!confirm('Delete this memory permanently?')) return
    await api.delete(`/api/media/${id}`)
    removeItem(id)
    toast.success('Memory deleted')
    navigate('/')
  }

  const toggleFullscreen = async () => {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen()
      } else {
        await mediaFrameRef.current?.requestFullscreen()
      }
    } catch {
      toast.error('Fullscreen is not available in this browser')
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
      <div className="spinner" style={{ width: 36, height: 36 }} />
    </div>
  )
  if (!item) return null

  const infoRows = [
    item.width && ['Dimensions', `${item.width} × ${item.height}`],
    item.duration_seconds && ['Duration', `${Math.floor(item.duration_seconds / 60)}:${String(Math.floor(item.duration_seconds % 60)).padStart(2, '0')}`],
    item.file_size_bytes && ['Size', (item.file_size_bytes / 1048576).toFixed(1) + ' MB'],
    item.view_count !== undefined && ['Views', item.view_count],
    item.taken_at && ['Date taken', new Date(item.taken_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })],
  ].filter(Boolean)

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <button className="btn btn-ghost" onClick={() => navigate(-1)} style={{ marginBottom: 20, fontSize: 13 }}>
        <ArrowLeft size={15} /> Back
      </button>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 24, alignItems: 'start' }}>
        {/* ── Media panel ── */}
        <div>
          <div ref={mediaFrameRef} className="media-viewer-frame" style={{
            position: 'relative',
            borderRadius: 16, overflow: 'hidden',
            background: '#1a120a',
            ...(item.media_type === 'video' ? { aspectRatio: '16/9' } : {}),
          }}>
            {item.media_type === 'video'
              ? <video src={item.file_url} controls playsInline preload="metadata" style={{ width: '100%', height: '100%', display: 'block', background: '#000', objectFit: 'contain' }} />
              : <img src={item.file_url} alt={item.title || item.original_filename}
                  style={{ width: '100%', maxHeight: isFullscreen ? '100vh' : '70vh', height: isFullscreen ? '100vh' : 'auto', objectFit: 'contain', display: 'block' }} />
            }
            <button
              type="button"
              className="btn btn-icon"
              onClick={toggleFullscreen}
              title={isFullscreen ? 'Exit fullscreen' : 'View fullscreen'}
              style={{
                position: 'absolute',
                top: 12,
                right: 12,
                background: 'rgba(44,30,15,.62)',
                color: '#fff',
                borderColor: 'rgba(255,255,255,.18)',
                backdropFilter: 'blur(6px)',
              }}
            >
              {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
            <button className="btn btn-ghost" onClick={toggleFav}>
              <Heart size={14} fill={fav ? '#f08878' : 'none'} color={fav ? '#f08878' : undefined} />
              {fav ? 'Favorited' : 'Favorite'}
            </button>
            <button className="btn btn-ghost" onClick={() => { const a = document.createElement('a'); a.href = item.file_url; a.download = item.original_filename; a.click() }}>
              <Download size={14} /> Download
            </button>
            <button className="btn btn-ghost" onClick={toggleFullscreen}>
              {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
              {isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            </button>
            <button className="btn btn-ghost" onClick={() => setEditing(true)}>
              <Pencil size={14} /> Edit
            </button>
            <button className="btn btn-danger btn" onClick={deleteMedia} style={{ marginLeft: 'auto' }}>
              <Trash2 size={14} /> Delete
            </button>
          </div>
        </div>

        {/* ── Sidebar ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Info card */}
          <div className="card" style={{ padding: 20 }}>
            <h2 style={{ fontFamily: 'var(--serif)', fontSize: 19, fontWeight: 500, marginBottom: 6, lineHeight: 1.3 }}>
              {item.title || item.original_filename}
            </h2>
            {item.caption && (
              <p style={{ fontSize: 13.5, color: 'var(--c-brown-lt)', lineHeight: 1.65, marginBottom: 14 }}>{item.caption}</p>
            )}
            {item.location_name && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12.5, color: 'var(--c-brown-lt)', marginBottom: 14 }}>
                <MapPin size={12} /> {item.location_name}
              </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7, borderTop: '1px solid var(--c-border)', paddingTop: 14 }}>
              {infoRows.map(([label, val]) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
                  <span style={{ color: 'var(--c-brown-lt)' }}>{label}</span>
                  <span style={{ fontWeight: 500, color: 'var(--c-brown)' }}>{val}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Comments */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 14 }}>
              <MessageCircle size={15} color="var(--c-gold)" />
              <span style={{ fontFamily: 'var(--serif)', fontSize: 15, fontWeight: 500 }}>
                Comments {comments.length > 0 && `(${comments.length})`}
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 260, overflowY: 'auto', marginBottom: 12 }}>
              {comments.length === 0
                ? <p style={{ fontSize: 12.5, color: 'var(--c-brown-lt)', fontStyle: 'italic' }}>No comments yet…</p>
                : comments.map(c => (
                    <div key={c.id} style={{
                      padding: '9px 11px', background: 'var(--c-surface2)', borderRadius: 9,
                      border: '1px solid var(--c-border)',
                    }}>
                      <p style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--c-brown)' }}>{c.body}</p>
                      <p style={{ fontSize: 11, color: 'var(--c-brown-lt)', marginTop: 4 }}>
                        {c.created_at ? formatDistanceToNow(new Date(c.created_at), { addSuffix: true }) : ''}
                      </p>
                    </div>
                  ))
              }
            </div>

            <div style={{ display: 'flex', gap: 7 }}>
              <input
                className="input" style={{ flex: 1, fontSize: 13 }}
                placeholder="Leave a memory…"
                value={commentText}
                onChange={e => setCommentText(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && postComment()}
              />
              <button className="btn btn-primary" onClick={postComment} style={{ padding: '9px 12px' }}>
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {editing && item.media_type === 'photo' && (
        <PhotoEditor item={item} onClose={() => setEditing(false)} onSaved={(data) => {
          setEditing(false)
          if (data?.result_url) setItem(prev => ({ ...prev, file_url: data.result_url, width: data.width || prev.width, height: data.height || prev.height }))
          toast.success('Edit saved!')
        }} />
      )}
      {editing && item.media_type === 'video' && (
        <VideoEditor item={item} onClose={() => setEditing(false)} onSaved={(data) => {
          setEditing(false)
          if (data?.result_url) setItem(prev => ({ ...prev, file_url: data.result_url, duration_seconds: data.duration_seconds || prev.duration_seconds }))
          toast.success('Video edit saved!')
        }} />
      )}
    </div>
  )
}
