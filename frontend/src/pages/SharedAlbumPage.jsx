import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Camera, FileText, Lock, Play } from 'lucide-react'
import axios from 'axios'

const publicApi = axios.create({ 
  baseURL: import.meta.env.DEV 
    ? (import.meta.env.VITE_API_URL || 'http://localhost:8000') 
    : window.location.origin 
})

export default function SharedAlbumPage() {
  const { token } = useParams()
  const [password, setPassword] = useState('')
  const [submittedPassword, setSubmittedPassword] = useState('')
  const [album, setAlbum] = useState(null)
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [needsPassword, setNeedsPassword] = useState(false)
  const [error, setError] = useState('')

  const params = useMemo(() => ({
    token,
    ...(submittedPassword ? { password: submittedPassword } : {}),
  }), [token, submittedPassword])

  async function load() {
    setLoading(true)
    setError('')
    try {
      const { data } = await publicApi.get(`/api/albums/shared/${token}`, {
        params: submittedPassword ? { password: submittedPassword } : {},
      })
      setAlbum(data.album)
      setItems(data.items)
      setNeedsPassword(false)
    } catch (err) {
      if (err.response?.status === 403) {
        setNeedsPassword(true)
        setError('Enter the album password to continue.')
      } else {
        setError(err.response?.data?.detail || 'This shared album is unavailable.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [token, submittedPassword])

  function getAuthenticatedUrl(baseUrl) {
    if (!baseUrl) return ''
    try {
      const url = new URL(baseUrl, window.location.origin)
      if (params.token) url.searchParams.set('token', params.token)
      if (params.password) url.searchParams.set('password', params.password)
      return url.toString()
    } catch (e) {
      return baseUrl
    }
  }

  if (loading) {
    return <div className="shared-shell"><div className="empty-state"><div className="spinner" /><p>Loading shared album...</p></div></div>
  }

  if (needsPassword) {
    return (
      <div className="shared-shell">
        <div className="shared-auth card">
          <Lock size={28} color="var(--c-gold)" />
          <h1 className="section-title">Protected Album</h1>
          <p>{error}</p>
          <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} onKeyDown={e => e.key === 'Enter' && setSubmittedPassword(password)} autoFocus />
          <button className="btn btn-primary" onClick={() => setSubmittedPassword(password)}>Unlock</button>
        </div>
      </div>
    )
  }

  if (error) {
    return <div className="shared-shell"><div className="empty-state"><Camera size={54} /><h3>Shared album unavailable</h3><p>{error}</p></div></div>
  }

  return (
    <div className="shared-shell">
      <header className="shared-header">
        <div>
          <div className="badge">Shared album</div>
          <h1>{album?.title}</h1>
          {album?.description && <p>{album.description}</p>}
        </div>
        {album?.share_expires_at && <span className="badge">Expires {new Date(album.share_expires_at).toLocaleDateString()}</span>}
      </header>

      {items.length === 0 ? (
        <div className="empty-state"><Camera size={54} /><h3>No media in this album</h3></div>
      ) : (
        <div className="media-grid">
          {items.map(item => {
            const isVideo = item.media_type === 'video'
            const isDoc = item.media_type === 'document'
            const url = getAuthenticatedUrl(item.file_url)
            const thumbUrl = getAuthenticatedUrl(item.thumbnail_url) || url
            return (
              <a key={item.id} className="shared-card" href={url} target="_blank" rel="noreferrer">
                {isDoc ? (
                  <div className="shared-doc"><FileText size={34} /><span>{item.original_filename}</span></div>
                ) : (
                  <img src={thumbUrl} alt={item.title || item.original_filename} loading="lazy" />
                )}
                {isVideo && <div className="shared-play"><Play size={16} fill="#fff" /></div>}
                <div className="shared-card-caption">{item.title || item.original_filename}</div>
              </a>
            )
          })}
        </div>
      )}
    </div>
  )
}
