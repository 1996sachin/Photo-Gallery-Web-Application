import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Camera, Download, FileText, Lock, Play, Share2, ZoomIn, ZoomOut, Maximize } from 'lucide-react'
import axios from 'axios'

const publicApi = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000' })

export default function SharedMediaPage() {
  const { token } = useParams()
  const [password, setPassword] = useState('')
  const [submittedPassword, setSubmittedPassword] = useState('')
  const [item, setItem] = useState(null)
  const [loading, setLoading] = useState(true)
  const [needsPassword, setNeedsPassword] = useState(false)
  const [error, setError] = useState('')

  // Zoom State
  const [zoom, setZoom] = useState(1)
  const zoomIn = () => setZoom(prev => Math.min(prev + 0.25, 3))
  const zoomOut = () => setZoom(prev => Math.max(prev - 0.25, 0.5))
  const resetZoom = () => setZoom(1)

  const params = useMemo(() => ({
    token,
    ...(submittedPassword ? { password: submittedPassword } : {}),
  }), [token, submittedPassword])

  async function load() {
    setLoading(true)
    setError('')
    try {
      const { data } = await publicApi.get(`/api/media/shared/${token}`, {
        params: submittedPassword ? { password: submittedPassword } : {},
      })
      setItem(data)
      setNeedsPassword(false)
    } catch (err) {
      if (err.response?.status === 403) {
        setNeedsPassword(true)
        setError('Enter the share password to view this memory.')
      } else {
        setError(err.response?.data?.detail || 'This shared memory is unavailable.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [token, submittedPassword])

  function fileUrl() {
    if (!item?.file_url) return ''
    try {
      const url = new URL(item.file_url, window.location.origin)
      if (submittedPassword) url.searchParams.set('password', submittedPassword)
      return url.toString()
    } catch (e) {
      return item.file_url
    }
  }

  if (loading) {
    return <div className="shared-shell"><div className="empty-state"><div className="spinner" /><p>Loading shared memory...</p></div></div>
  }

  if (needsPassword) {
    return (
      <div className="shared-shell">
        <div className="shared-auth card">
          <Lock size={28} color="var(--c-gold)" />
          <h1 className="section-title">Protected Memory</h1>
          <p>{error}</p>
          <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} onKeyDown={e => e.key === 'Enter' && setSubmittedPassword(password)} autoFocus />
          <button className="btn btn-primary" onClick={() => setSubmittedPassword(password)}>Unlock</button>
        </div>
      </div>
    )
  }

  if (error) {
    return <div className="shared-shell"><div className="empty-state"><Camera size={54} /><h3>Memory unavailable</h3><p>{error}</p></div></div>
  }

  const isVideo = item.media_type === 'video'
  const isDoc = item.media_type === 'document'
  const isPdf = item.mime_type === 'application/pdf'
  const url = fileUrl()

  return (
    <div className="shared-shell">
      <header className="shared-header">
        <div>
          <div className="badge">Shared memory</div>
          <h1>{item.title || item.original_filename}</h1>
          {item.caption && <p>{item.caption}</p>}
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            {item.share_expires_at && <span className="badge">Expires {new Date(item.share_expires_at).toLocaleDateString()}</span>}
            <button className="btn btn-primary" onClick={() => { const a = document.createElement('a'); a.href = url; a.download = item.original_filename; a.click() }}>
                <Download size={14} /> Download
            </button>
        </div>
      </header>

      <div style={{ maxWidth: 1000, margin: '0 auto' }}>
        <div style={{
            borderRadius: 16, overflow: zoom > 1 ? 'auto' : 'hidden',
            background: '#1a120a',
            position: 'relative',
            ...(isVideo ? { aspectRatio: '16/9' } : { minHeight: 450 }),
            boxShadow: '0 20px 50px rgba(0,0,0,0.3)',
        }}>
            {isVideo ? (
                <video src={url} controls playsInline preload="metadata" style={{ width: '100%', height: '100%', display: 'block', background: '#000' }} />
            ) : (isDoc && isPdf) ? (
                <iframe src={url} style={{ width: '100%', height: '80vh', border: 'none', background: '#fff' }} title={item.title || item.original_filename} />
            ) : isDoc ? (
                <div style={{ padding: 100, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20, color: 'var(--c-brown-lt)' }}>
                    <FileText size={80} strokeWidth={1.2} />
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 18, fontWeight: 500, color: '#fff', marginBottom: 4 }}>{item.original_filename}</div>
                        <div style={{ fontSize: 13, opacity: 0.6 }}>Document Memory ({item.mime_type})</div>
                    </div>
                </div>
            ) : (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 450, cursor: zoom > 1 ? 'move' : 'default' }}>
                    <img 
                      src={url} 
                      alt={item.title || item.original_filename}
                      style={{ 
                        maxWidth: zoom > 1 ? 'none' : '100%', 
                        maxHeight: zoom > 1 ? 'none' : '85vh', 
                        transform: `scale(${zoom})`,
                        transformOrigin: 'center center',
                        transition: 'transform 0.2s ease-out',
                        display: 'block'
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
      </div>
    </div>
  )
}
