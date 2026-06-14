import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { Images, Film, LayoutGrid, Trash2, Heart, X, FileText, Folder } from 'lucide-react'
import { useMediaStore } from '../stores/mediaStore'
import MediaCard from '../components/MediaCard'
import MoveToFolderModal from '../components/MoveToFolderModal'
import toast from 'react-hot-toast'

export default function GalleryPage() {
  const { search } = useOutletContext()
  const { items, loading, hasMore, filters, fetch, setFilter, selection, toggleSelect, clearSelection, batchDelete, batchFavorite, batchMove } = useMediaStore()
  const [acting, setActing] = useState(false)
  const [moving, setMoving] = useState(false)

  useEffect(() => { fetch(true) }, [])

  useEffect(() => {
    const t = setTimeout(() => setFilter('search', search), 340)
    return () => clearTimeout(t)
  }, [search])

  const onBatchDelete = async () => {
    if (!confirm(`Move ${selection.length} memories to trash?`)) return
    setActing(true)
    if (await batchDelete()) toast.success('Moved to trash')
    else toast.error('Batch delete failed')
    setActing(false)
  }

  const onBatchFavorite = async (fav) => {
    setActing(true)
    if (await batchFavorite(fav)) toast.success(fav ? 'Added to favorites' : 'Removed from favorites')
    else toast.error('Batch update failed')
    setActing(false)
  }

  const FilterChip = ({ value, label, icon: Icon }) => (
    <button
      className="btn"
      style={{
        padding: '7px 14px', fontSize: 12.5,
        background: filters.type === value ? 'var(--c-gold)' : 'var(--c-surface)',
        color: filters.type === value ? '#fff' : 'var(--c-brown-lt)',
        border: `1px solid ${filters.type === value ? 'var(--c-gold)' : 'var(--c-border)'}`,
        borderRadius: 99,
      }}
      onClick={() => setFilter('type', value)}
    >
      {Icon && <Icon size={13} />} {label}
    </button>
  )

  return (
    <div>
      {selection.length > 0 && (
        <div style={{
          position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--c-brown)', color: '#fff', padding: '12px 20px',
          borderRadius: 16, display: 'flex', alignItems: 'center', gap: 16,
          boxShadow: '0 10px 40px rgba(0,0,0,0.4)', zIndex: 100,
        }}>
          <span style={{ fontSize: 13.5, fontWeight: 600 }}>{selection.length} selected</span>
          <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.2)' }} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-ghost" onClick={() => onBatchFavorite(true)} disabled={acting} style={{ color: '#fff', padding: '6px 10px' }}>
              <Heart size={15} /> Favorite
            </button>
            <button className="btn btn-ghost" onClick={() => setMoving(true)} disabled={acting} style={{ color: '#fff', padding: '6px 10px' }}>
              <Folder size={15} /> Move
            </button>
            <button className="btn btn-ghost" onClick={onBatchDelete} disabled={acting} style={{ color: '#ff7a7a', padding: '6px 10px' }}>
              <Trash2 size={15} /> Trash
            </button>
            <button className="btn btn-icon" onClick={clearSelection} style={{ color: 'rgba(255,255,255,0.6)' }}>
              <X size={16} />
            </button>
          </div>
        </div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22, flexWrap: 'wrap', gap: 10 }}>
        <h1 className="page-title">
          {search ? `"${search}"` : 'All Memories'}
          {items.length > 0 && <span style={{ fontFamily: 'var(--sans)', fontSize: 14, fontWeight: 400, color: 'var(--c-brown-lt)', marginLeft: 10 }}>{items.length} memories</span>}
        </h1>
        <div style={{ display: 'flex', gap: 7 }}>
          <FilterChip value="all"      label="All"       icon={LayoutGrid} />
          <FilterChip value="photo"    label="Photos"    icon={Images} />
          <FilterChip value="video"    label="Videos"    icon={Film} />
          <FilterChip value="document" label="Documents" icon={FileText} />
        </div>
      </div>

      {loading && items.length === 0 ? (
        <div className="empty-state">
          <div className="spinner" style={{ width: 36, height: 36 }} />
          <p>Loading your memories…</p>
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <Images size={60} />
          <h3>No memories yet</h3>
          <p>Upload your first photos and videos to start your gallery for your loved ones.</p>
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
                selectMode={selection.length > 0}
              />
            ))}
          </div>
          {hasMore && (
            <div style={{ display: 'flex', justifyContent: 'center', marginTop: 32 }}>
              <button className="btn btn-ghost" onClick={() => fetch()} disabled={loading}>
                {loading ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Loading…</> : 'Load more'}
              </button>
            </div>
          )}
        </>
      )}

      {moving && (
        <MoveToFolderModal 
          selection={selection} 
          onMoved={batchMove} 
          onClose={() => setMoving(false)} 
        />
      )}
    </div>
  )
}
