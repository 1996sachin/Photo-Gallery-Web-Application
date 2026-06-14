import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Heart, Download, Pencil, Trash2, MessageCircle, Send, MapPin, Calendar, Eye, Share2, Shield, ShieldAlert, ShieldCheck, Lock, Tag, Info, Activity, RotateCcw, ZoomIn, ZoomOut, Maximize } from 'lucide-react'
import { api, useAuthStore } from '../hooks/useAuth'
import { useMediaStore } from '../stores/mediaStore'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import PhotoEditor from '../components/PhotoEditor'
import VideoEditor from '../components/VideoEditor'
import ItemShareModal from '../components/ItemShareModal'
import AccessControlModal from '../components/AccessControlModal'

export default function MediaViewPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, token } = useAuthStore()
  const removeItem = useMediaStore(s => s.removeItem)
  const [item, setItem] = useState(null)
  const [loading, setLoading] = useState(true)
  const [fav, setFav] = useState(false)
  const [comments, setComments] = useState([])
  const [commentText, setCommentText] = useState('')
  const [editing, setEditing] = useState(false)
  const [sharing, setSharing] = useState(false)
  const [managingAccess, setManagingAccess] = useState(false)
  
  // Tab State
  const [activeTab, setActiveTab] = useState('info')
  const [activity, setActivity] = useState([])
  const [versions, setVersions] = useState([])

  // Zoom State
  const [zoom, setZoom] = useState(1)
  const zoomIn = () => setZoom(prev => Math.min(prev + 0.25, 3))
  const zoomOut = () => setZoom(prev => Math.max(prev - 0.25, 0.5))
  const resetZoom = () => setZoom(1)

  const getAuthUrl = (url) => {
    if (!url) return ''
    const isProxied = url.startsWith('/') || url.includes(window.location.hostname)
    if (!isProxied || !token) return url
    return `${url}${url.includes('?') ? '&' : '?'}token=${token}`
  }

  useEffect(() => { loadMedia(); loadComments(); loadActivity(); loadVersions() }, [id])

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

  const loadActivity = async () => {
    try {
      const { data } = await api.get('/api/activity/', { params: { target_id: id, target_type: 'media' } })
      setActivity(data)
    } catch {}
  }

  const loadVersions = async () => {
    try {
      const { data } = await api.get(`/api/edits/${id}/versions`)
      setVersions(data)
    } catch {}
  }

  const restoreOriginal = async () => {
    if (!confirm('Restore this memory to its original state? Edits will be lost.')) return
    try {
      await api.post(`/api/edits/${id}/restore-original`)
      toast.success('Original restored! 🔄')
      loadMedia()
      loadVersions()
    } catch {
      toast.error('Restore failed')
    }
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
    if (!confirm('Delete this memory? It will be moved to trash.')) return
    await api.delete(`/api/media/${id}`)
    removeItem(id)
    toast.success('Moved to trash')
    navigate('/')
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
      <div className="spinner" style={{ width: 36, height: 36 }} />
    </div>
  )
  if (!item) return null

  const formatAction = (action) => {
    return action.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  }

  const infoRows = [
    item.width && ['Dimensions', `${item.width} × ${item.height}`],
    item.duration_seconds && ['Duration', `${Math.floor(item.duration_seconds / 60)}:${String(Math.floor(item.duration_seconds % 60)).padStart(2, '0')}`],
    item.file_size_bytes && ['Size', (item.file_size_bytes / 1048576).toFixed(1) + ' MB'],
    item.view_count !== undefined && ['Views', item.view_count],
    item.taken_at && ['Date taken', new Date(item.taken_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })],
    ...(item.media_metadata ? Object.entries(item.media_metadata).slice(0, 8) : []),
  ].filter(Boolean)

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <button className="btn btn-ghost" onClick={() => navigate(-1)} style={{ marginBottom: 20, fontSize: 13 }}>
        <ArrowLeft size={15} /> Back
      </button>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24, alignItems: 'start' }}>
        {/* ── Media panel ── */}
        <div>
          <div style={{
            borderRadius: 16, overflow: zoom > 1 ? 'auto' : 'hidden',
            background: '#1a120a',
            position: 'relative',
            ...(item.media_type === 'video' ? { aspectRatio: '16/9' } : { minHeight: 450 }),
          }}>
            {item.media_type === 'video' ? (
              <video src={getAuthUrl(item.file_url)} controls playsInline preload="metadata" style={{ width: '100%', height: '100%', display: 'block', background: '#000' }} />
            ) : (item.media_type === 'document' && item.mime_type === 'application/pdf') ? (
              <iframe src={getAuthUrl(item.file_url)} style={{ width: '100%', height: '75vh', border: 'none', background: '#fff' }} title={item.title || item.original_filename} />
            ) : item.media_type === 'document' ? (
              <div style={{ width: '100%', height: '100%', minHeight: 450, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, color: 'var(--c-brown-lt)' }}>
                <FileText size={80} strokeWidth={1.2} />
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 16, fontWeight: 500, color: '#fff', marginBottom: 4 }}>{item.original_filename}</div>
                  <div style={{ fontSize: 13, opacity: 0.6 }}>Document Memory ({item.mime_type})</div>
                </div>
                <button className="btn btn-primary" onClick={() => { const a = document.createElement('a'); a.href = getAuthUrl(item.file_url); a.download = item.original_filename; a.click() }}>
                  <Download size={15} /> View / Download Document
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 450, cursor: zoom > 1 ? 'move' : 'default' }}>
                <img 
                  src={getAuthUrl(item.file_url)} 
                  alt={item.title || item.original_filename}
                  style={{ 
                    maxWidth: zoom > 1 ? 'none' : '100%', 
                    maxHeight: zoom > 1 ? 'none' : '80vh', 
                    transform: `scale(${zoom})`,
                    transformOrigin: 'center center',
                    transition: 'transform 0.2s ease-out',
                    display: 'block',
                    borderRadius: zoom > 1 ? 0 : 4
                  }} 
                />
              </div>
            )}

            {/* Zoom Controls Overlay */}
            {item.media_type === 'photo' && (
              <div style={{ position: 'absolute', bottom: 20, right: 20, display: 'flex', gap: 8, zIndex: 10 }}>
                <button className="btn btn-icon" style={{ background: 'rgba(0,0,0,0.6)', color: '#fff', border: 'none', width: 32, height: 32 }} onClick={zoomOut} title="Zoom Out"><ZoomOut size={16} /></button>
                <button className="btn" style={{ background: 'rgba(0,0,0,0.6)', color: '#fff', border: 'none', fontSize: 11, padding: '0 8px', height: 32, minWidth: 50, justifyContent: 'center' }} onClick={resetZoom} title="Reset Zoom">{Math.round(zoom * 100)}%</button>
                <button className="btn btn-icon" style={{ background: 'rgba(0,0,0,0.6)', color: '#fff', border: 'none', width: 32, height: 32 }} onClick={zoomIn} title="Zoom In"><ZoomIn size={16} /></button>
              </div>
            )}
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
            <button className="btn btn-ghost" onClick={toggleFav}>
              <Heart size={14} fill={fav ? '#f08878' : 'none'} color={fav ? '#f08878' : undefined} />
              {fav ? 'Favorited' : 'Favorite'}
            </button>
            <button className="btn btn-ghost" onClick={() => { const a = document.createElement('a'); a.href = getAuthUrl(item.file_url); a.download = item.original_filename; a.click() }}>
              <Download size={14} /> Download
            </button>
            <button className="btn btn-ghost" onClick={() => setSharing(true)}>
              <Share2 size={14} color={item.privacy === 'shared' ? 'var(--c-gold)' : undefined} /> 
              {item.privacy === 'shared' ? 'Shared' : 'Share'}
            </button>
            <button className="btn btn-ghost" onClick={() => setManagingAccess(true)}>
              <Shield size={14} /> Access
            </button>
            {item.media_type !== 'document' && (
              <button className="btn btn-ghost" onClick={() => setEditing(true)}>
                <Pencil size={14} /> Edit
              </button>
            )}
            <button className="btn btn-danger btn" onClick={deleteMedia} style={{ marginLeft: 'auto' }}>
              <Trash2 size={14} /> Trash
            </button>
          </div>
        </div>

        {/* ── Sidebar ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Security status */}
          <div className="card" style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 32, height: 32, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: item.malware_scan_status === 'clean' ? 'rgba(76,175,80,0.1)' : 'rgba(244,67,54,0.1)',
              color: item.malware_scan_status === 'clean' ? '#4caf50' : '#f44336'
            }}>
              {item.malware_scan_status === 'clean' ? <ShieldCheck size={18} /> : <ShieldAlert size={18} />}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12.5, fontWeight: 600 }}>
                {item.malware_scan_status === 'clean' ? 'Safe content' : 'Malware warning'}
              </div>
              <div style={{ fontSize: 11, color: 'var(--c-brown-lt)' }}>
                {item.malware_scan_status === 'clean' ? 'Scanned & clean' : 'Potential threat detected'}
              </div>
            </div>
            {item.is_encrypted && (
              <div className="tooltip" data-tip="Encrypted at rest">
                <Lock size={14} color="var(--c-gold)" />
              </div>
            )}
          </div>

          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ display: 'flex', borderBottom: '1px solid var(--c-border)' }}>
              {['info', 'comments', 'activity'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  style={{
                    flex: 1, padding: '12px 0', fontSize: 13, fontWeight: 600,
                    textTransform: 'capitalize', border: 'none', background: 'none',
                    cursor: 'pointer', color: activeTab === tab ? 'var(--c-gold)' : 'var(--c-brown-lt)',
                    borderBottom: activeTab === tab ? '2px solid var(--c-gold)' : '2px solid transparent',
                    transition: 'all 0.2s'
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>

            <div style={{ padding: 20 }}>
              {activeTab === 'info' && (
                <>
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

                  {item.tags && item.tags.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
                      {item.tags.map(tag => (
                        <span key={tag} style={{ 
                          fontSize: 10, background: 'rgba(200,150,60,0.1)', color: 'var(--c-gold)', 
                          padding: '2px 8px', borderRadius: 99, border: '1px solid rgba(200,150,60,0.2)',
                          display: 'flex', alignItems: 'center', gap: 4
                        }}>
                          <Tag size={9} /> {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 7, borderTop: '1px solid var(--c-border)', paddingTop: 14 }}>
                    {infoRows.map(([label, val]) => (
                      <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
                        <span style={{ color: 'var(--c-brown-lt)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '60%' }}>{label}</span>
                        <span style={{ fontWeight: 500, color: 'var(--c-brown)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>{val}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {activeTab === 'comments' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 300, overflowY: 'auto' }}>
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
                  <div style={{ display: 'flex', gap: 7, marginTop: 8 }}>
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
              )}

              {activeTab === 'activity' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {versions.length > 0 && (
                    <div style={{ padding: '12px 14px', background: 'rgba(200,150,60,0.1)', borderRadius: 10, border: '1px solid rgba(200,150,60,0.2)' }}>
                       <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                         <RotateCcw size={14} /> Version History
                       </div>
                       {versions.map(v => (
                         <div key={v.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                           <span style={{ color: 'var(--c-brown)' }}>{v.name}</span>
                           {v.name === 'Original' && (
                             <button className="btn btn-ghost" onClick={restoreOriginal} style={{ padding: '4px 8px', fontSize: 11 }}>Restore</button>
                           )}
                         </div>
                       ))}
                    </div>
                  )}
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 300, overflowY: 'auto' }}>
                    {activity.length === 0
                      ? <p style={{ fontSize: 12.5, color: 'var(--c-brown-lt)', fontStyle: 'italic' }}>No activity logged.</p>
                      : activity.map(log => (
                          <div key={log.id} style={{ display: 'flex', gap: 10, fontSize: 12, borderLeft: '2px solid var(--c-border)', paddingLeft: 10 }}>
                            <div>
                              <div style={{ fontWeight: 600 }}>{formatAction(log.action)}</div>
                              <div style={{ color: 'var(--c-brown-lt)', fontSize: 11 }}>
                                {new Date(log.created_at).toLocaleDateString()} at {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </div>
                            </div>
                          </div>
                        ))
                    }
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {editing && item.media_type === 'photo' && (
        <PhotoEditor item={item} onClose={() => setEditing(false)} onSaved={(data) => {
          setEditing(false)
          if (data?.result_url) setItem(prev => ({ ...prev, file_url: data.result_url, width: data.width || prev.width, height: data.height || prev.height }))
          loadVersions()
          toast.success('Edit saved!')
        }} />
      )}
      {editing && item.media_type === 'video' && (
        <VideoEditor item={item} onClose={() => setEditing(false)} onSaved={(data) => {
          setEditing(false)
          if (data?.result_url) setItem(prev => ({ ...prev, file_url: data.result_url, duration_seconds: data.duration_seconds || prev.duration_seconds }))
          loadVersions()
          toast.success('Video edit saved!')
        }} />
      )}

      {sharing && (
        <ItemShareModal
          item={item}
          onUpdate={setItem}
          onClose={() => setSharing(false)}
        />
      )}

      {managingAccess && (
        <AccessControlModal
          type="media"
          id={item.id}
          title={item.title || item.original_filename}
          onClose={() => setManagingAccess(false)}
        />
      )}
    </div>
  )
}
