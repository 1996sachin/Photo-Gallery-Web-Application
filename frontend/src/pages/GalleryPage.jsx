import { useEffect } from 'react'
import { useOutletContext } from 'react-router-dom'
import { Images, Film, LayoutGrid } from 'lucide-react'
import { useMediaStore } from '../stores/mediaStore'
import MediaCard from '../components/MediaCard'

export default function GalleryPage() {
  const { search } = useOutletContext()
  const { items, loading, hasMore, filters, fetch, setFilter } = useMediaStore()

  useEffect(() => { fetch(true) }, [])

  useEffect(() => {
    const t = setTimeout(() => setFilter('search', search), 340)
    return () => clearTimeout(t)
  }, [search])

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
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22, flexWrap: 'wrap', gap: 10 }}>
        <h1 className="page-title">
          {search ? `"${search}"` : 'All Memories'}
          {items.length > 0 && <span style={{ fontFamily: 'var(--sans)', fontSize: 14, fontWeight: 400, color: 'var(--c-brown-lt)', marginLeft: 10 }}>{items.length} memories</span>}
        </h1>
        <div style={{ display: 'flex', gap: 7 }}>
          <FilterChip value="all"   label="All"    icon={LayoutGrid} />
          <FilterChip value="photo" label="Photos" icon={Images} />
          <FilterChip value="video" label="Videos" icon={Film} />
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
            {items.map(item => <MediaCard key={item.id} item={item} />)}
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
    </div>
  )
}
