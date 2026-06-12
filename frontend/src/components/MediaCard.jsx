import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Heart, Play, FileText } from 'lucide-react'
import { api } from '../hooks/useAuth'
import { useMediaStore } from '../stores/mediaStore'
import toast from 'react-hot-toast'

export default function MediaCard({ item }) {
  const navigate = useNavigate()
  const updateItem = useMediaStore(s => s.updateItem)
  const [hov, setHov] = useState(false)
  const [fav, setFav] = useState(item.is_favorite)

  const toggleFav = async e => {
    e.stopPropagation()
    try {
      const { data } = await api.patch(`/api/media/${item.id}/favorite`)
      setFav(data.is_favorite)
      updateItem(item.id, { is_favorite: data.is_favorite })
      if (data.is_favorite) toast.success('Added to favorites ❤️')
    } catch { toast.error('Could not update') }
  }

  const thumb = item.thumbnail_url || item.file_url
  const isDoc = item.media_type === 'document'
  const isVid = item.media_type === 'video'

  return (
    <div
      onClick={() => navigate(`/media/${item.id}`)}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        position: 'relative', cursor: 'pointer',
        borderRadius: 11, overflow: 'hidden',
        background: 'var(--c-parchment)',
        boxShadow: hov ? 'var(--shadow-lg)' : 'var(--shadow-sm)',
        transform: hov ? 'scale(1.025)' : 'scale(1)',
        transition: 'transform 0.2s var(--ease), box-shadow 0.2s var(--ease)',
        marginBottom: '12px',
        display: 'block'
      }}
    >
      <img
        src={thumb} alt={item.title || item.original_filename}
        loading="lazy"
        style={{
          width: '100%', height: 'auto', display: 'block',
          transform: hov ? 'scale(1.06)' : 'scale(1)',
          transition: 'transform 0.35s var(--ease)',
          minHeight: isDoc ? '140px' : 'auto'
        }}
        onError={e => { e.target.style.opacity = '0' }}
      />

      {/* Video play icon */}
      {isVid && (
        <div style={{
          position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
          width: 38, height: 38, borderRadius: '50%',
          background: 'rgba(44,30,15,0.62)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(2px)', pointerEvents: 'none',
        }}>
          <Play size={16} color="#fff" fill="#fff" />
        </div>
      )}

      {/* Document icon overlay */}
      {isDoc && (
        <div style={{
          position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
          color: 'var(--c-brown)', opacity: 0.8, pointerEvents: 'none'
        }}>
          <FileText size={32} />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.05em' }}>
            {item.original_filename.split('.').pop().toUpperCase()}
          </span>
        </div>
      )}

      {/* Bottom gradient + info */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(to top, rgba(44,30,15,0.72) 0%, rgba(44,30,15,0.1) 45%, transparent 70%)',
        opacity: hov ? 1 : 0, transition: 'opacity 0.22s',
      }} />
      {hov && (
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '8px 10px' }}>
          <div style={{ fontSize: 11.5, color: 'rgba(253,248,240,0.92)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
            {item.title || item.original_filename}
          </div>
          {item.duration_seconds > 0 && (
            <div style={{ fontSize: 10.5, color: 'rgba(253,248,240,0.6)', marginTop: 2 }}>
              {Math.floor(item.duration_seconds / 60)}:{String(Math.floor(item.duration_seconds % 60)).padStart(2, '0')}
            </div>
          )}
        </div>
      )}

      {/* Fav btn */}
      <button
        onClick={toggleFav}
        style={{
          position: 'absolute', top: 7, right: 7,
          width: 28, height: 28, borderRadius: '50%', border: 'none', cursor: 'pointer',
          background: 'rgba(44,30,15,0.48)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          opacity: hov || fav ? 1 : 0, transition: 'opacity 0.2s, transform 0.15s',
          transform: fav ? 'scale(1.1)' : 'scale(1)',
        }}
        title={fav ? 'Remove from favorites' : 'Favorite'}
      >
        <Heart size={13} color={fav ? '#f08878' : '#fff'} fill={fav ? '#f08878' : 'none'} />
      </button>

      {/* Badges */}
      <div style={{ position: 'absolute', top: 7, left: 7, display: 'flex', gap: 4 }}>
        {isVid && (
          <div style={{
            background: 'rgba(44,30,15,0.55)', backdropFilter: 'blur(3px)',
            borderRadius: 5, padding: '2px 6px',
            fontSize: 10, color: '#e8b86a', fontWeight: 600, letterSpacing: '0.04em',
          }}>
            VIDEO
          </div>
        )}
        {isDoc && (
          <div style={{
            background: 'rgba(44,30,15,0.55)', backdropFilter: 'blur(3px)',
            borderRadius: 5, padding: '2px 6px',
            fontSize: 10, color: '#f5ead8', fontWeight: 600, letterSpacing: '0.04em',
          }}>
            DOC
          </div>
        )}
      </div>
    </div>
  )
}
