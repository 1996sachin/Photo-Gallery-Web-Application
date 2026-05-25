import { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, Pause, Play } from 'lucide-react'

export default function MemorySlideshow({ items = [] }) {
  const slides = useMemo(() => items.slice(0, 12), [items])
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    if (!playing || slides.length < 2) return undefined
    const timer = setInterval(() => setIndex(i => (i + 1) % slides.length), 4500)
    return () => clearInterval(timer)
  }, [playing, slides.length])

  useEffect(() => {
    if (index >= slides.length) setIndex(0)
  }, [index, slides.length])

  if (slides.length === 0) return null

  const active = slides[index]
  const preview = slides.slice(0, 5)
  const mediaSrc = active.media_type === 'video' ? active.file_url : (active.thumbnail_url || active.file_url)

  const previous = () => setIndex(i => (i - 1 + slides.length) % slides.length)
  const next = () => setIndex(i => (i + 1) % slides.length)

  return (
    <section className="memory-slideshow" aria-label="Featured memories slideshow">
      <div className="slideshow-stage">
        {active.media_type === 'video' ? (
          <video key={active.id} src={mediaSrc} muted playsInline autoPlay={playing} loop className="slideshow-media" />
        ) : (
          <img key={active.id} src={mediaSrc} alt={active.title || active.original_filename} className="slideshow-media" />
        )}
        <div className="slideshow-vignette" />
        <div className="slideshow-copy">
          <span>{active.media_type === 'video' ? 'Video Memory' : 'Photo Memory'}</span>
          <h2>{active.title || active.original_filename}</h2>
          {(active.taken_at || active.created_at) && <p>{new Date(active.taken_at || active.created_at).toLocaleDateString()}</p>}
        </div>
        {slides.length > 1 && (
          <>
            <button className="slideshow-arrow left tooltip" data-tip="Previous" onClick={previous} aria-label="Previous memory"><ChevronLeft size={20} /></button>
            <button className="slideshow-arrow right tooltip" data-tip="Next" onClick={next} aria-label="Next memory"><ChevronRight size={20} /></button>
          </>
        )}
        <button className="slideshow-play tooltip" data-tip={playing ? 'Pause' : 'Play'} onClick={() => setPlaying(p => !p)} aria-label={playing ? 'Pause slideshow' : 'Play slideshow'}>
          {playing ? <Pause size={16} /> : <Play size={16} />}
        </button>
      </div>
      {slides.length > 1 && (
        <div className="slideshow-strip">
          {preview.map((item, i) => (
            <button key={item.id} className={i === index ? 'active' : ''} onClick={() => setIndex(i)} aria-label={`Show memory ${i + 1}`}>
              <img src={item.thumbnail_url || item.file_url} alt="" />
            </button>
          ))}
        </div>
      )}
    </section>
  )
}
