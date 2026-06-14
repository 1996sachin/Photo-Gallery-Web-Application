import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Share2, BookImage, Images, Clock, User } from 'lucide-react'
import { api } from '../hooks/useAuth'
import MediaCard from '../components/MediaCard'

export default function SharedWithMePage() {
  const navigate = useNavigate()
  const [albums, setAlbums] = useState([])
  const [media, setMedia] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [albumsRes, mediaRes] = await Promise.all([
          api.get('/api/albums/shared-with-me'),
          api.get('/api/media/shared-with-me')
        ])
        setAlbums(albumsRes.data)
        setMedia(mediaRes.data)
      } catch (err) {
        console.error('Failed to load shared content', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="empty-state">
        <div className="spinner" />
      </div>
    )
  }

  const hasContent = albums.length > 0 || media.length > 0

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 26 }}>
        <Share2 size={22} color="var(--c-gold)" />
        <h1 className="page-title">Shared with me</h1>
      </div>

      {!hasContent ? (
        <div className="empty-state">
          <Share2 size={56} />
          <h3>No shared memories yet</h3>
          <p>When someone shares an album or photo with you, it will appear here.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
          {/* Shared Albums Section */}
          {albums.length > 0 && (
            <section>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                <BookImage size={16} color="var(--c-brown-lt)" />
                <h2 style={{ fontSize: 15, fontWeight: 600, color: 'var(--c-brown)' }}>Shared Albums</h2>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 14 }}>
                {albums.map(album => (
                  <div key={album.id} className="card" onClick={() => navigate(`/albums/${album.id}`)} style={{ padding: 18, cursor: 'pointer' }}>
                    <div style={{ fontFamily: 'var(--serif)', fontSize: 16, fontWeight: 500, marginBottom: 6 }}>{album.title}</div>
                    {album.description && <p style={{ fontSize: 12.5, color: 'var(--c-brown-lt)', marginBottom: 8, lineHeight: 1.4 }}>{album.description}</p>}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--c-brown-lt)', marginTop: 8 }}>
                      <Clock size={11} />
                      <span>{new Date(album.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Shared Individual Media Section */}
          {media.length > 0 && (
            <section>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                <Images size={16} color="var(--c-brown-lt)" />
                <h2 style={{ fontSize: 15, fontWeight: 600, color: 'var(--c-brown)' }}>Shared Photos & Videos</h2>
              </div>
              <div className="media-grid">
                {media.map(item => (
                  <MediaCard key={item.id} item={item} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
