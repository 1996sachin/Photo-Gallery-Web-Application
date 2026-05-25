import { useMemo, useState } from 'react'
import { Check, FlipHorizontal, FlipVertical, Scissors, X } from 'lucide-react'
import { api } from '../hooks/useAuth'
import toast from 'react-hot-toast'

const FILTERS = [
  { name: 'original', label: 'Original', css: '' },
  { name: 'warm', label: 'Warm', css: 'sepia(0.18) saturate(1.18) brightness(1.04)' },
  { name: 'cool', label: 'Cool', css: 'hue-rotate(15deg) saturate(0.9)' },
  { name: 'bw', label: 'B&W', css: 'grayscale(1)' },
  { name: 'fade', label: 'Fade', css: 'contrast(0.85) saturate(0.75) brightness(1.04)' },
  { name: 'vivid', label: 'Vivid', css: 'saturate(1.35) contrast(1.08)' },
]

export default function VideoEditor({ item, onClose, onSaved }) {
  const duration = Number(item.duration_seconds || 0)
  const [activeFilter, setActiveFilter] = useState('original')
  const [brightness, setBrightness] = useState(1)
  const [contrast, setContrast] = useState(1)
  const [saturation, setSaturation] = useState(1)
  const [rotation, setRotation] = useState(0)
  const [flipH, setFlipH] = useState(false)
  const [flipV, setFlipV] = useState(false)
  const [start, setStart] = useState(0)
  const [end, setEnd] = useState(duration || 10)
  const [saving, setSaving] = useState(false)

  const previewFilter = useMemo(() => {
    const f = FILTERS.find(f => f.name === activeFilter)?.css || ''
    return [`brightness(${brightness}) contrast(${contrast}) saturate(${saturation})`, f].filter(Boolean).join(' ')
  }, [activeFilter, brightness, contrast, saturation])

  const save = async () => {
    setSaving(true)
    try {
      const { data } = await api.post('/api/edits/video', {
        media_id: item.id,
        params: {
          filter: activeFilter,
          brightness,
          contrast,
          saturation,
          rotation,
          flip_horizontal: flipH,
          flip_vertical: flipV,
          start_seconds: start,
          end_seconds: end,
        },
      })
      onSaved(data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Video edit failed')
    } finally {
      setSaving(false)
    }
  }

  const Slider = ({ label, value, onChange, min = 0.4, max = 2, step = 0.05 }) => (
    <div style={{ marginBottom: 13 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <label className="label" style={{ margin: 0 }}>{label}</label>
        <span style={{ fontSize: 11.5, color: 'var(--c-brown-lt)' }}>{Number(value).toFixed(2)}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(parseFloat(e.target.value))} style={{ width: '100%', accentColor: 'var(--c-gold)' }} />
    </div>
  )

  return (
    <div className="overlay">
      <div className="card" style={{ width: '96%', maxWidth: 940, padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column', maxHeight: '92vh' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '15px 20px', borderBottom: '1px solid var(--c-border)' }}>
          <h2 style={{ fontFamily: 'var(--serif)', fontSize: 19 }}>Edit Video</h2>
          <button className="btn btn-icon btn" onClick={onClose}><X size={16} /></button>
        </div>

        <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, background: '#1a120a', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
            <video
              src={item.file_url}
              controls
              style={{
                width: '100%',
                maxHeight: '62vh',
                borderRadius: 8,
                filter: previewFilter,
                transform: `rotate(${rotation}deg) scaleX(${flipH ? -1 : 1}) scaleY(${flipV ? -1 : 1})`,
              }}
            />
          </div>

          <div style={{ width: 286, borderLeft: '1px solid var(--c-border)', padding: 14, overflowY: 'auto' }}>
            <label className="label">Filters</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 7, marginBottom: 16 }}>
              {FILTERS.map(f => (
                <button key={f.name} onClick={() => setActiveFilter(f.name)} style={{
                  padding: '9px 6px', borderRadius: 8, cursor: 'pointer',
                  border: `2px solid ${activeFilter === f.name ? 'var(--c-gold)' : 'transparent'}`,
                  background: 'var(--c-surface2)', fontSize: 12, fontFamily: 'var(--sans)',
                  color: activeFilter === f.name ? 'var(--c-gold-dk)' : 'var(--c-brown-lt)',
                }}>{f.label}</button>
              ))}
            </div>

            <Slider label="Brightness" value={brightness} onChange={setBrightness} />
            <Slider label="Contrast" value={contrast} onChange={setContrast} />
            <Slider label="Saturation" value={saturation} onChange={setSaturation} />

            <div style={{ display: 'grid', gap: 8, marginBottom: 16 }}>
              <label className="label">Transform</label>
              <select className="input" value={rotation} onChange={e => setRotation(parseInt(e.target.value, 10))}>
                <option value={0}>No rotation</option>
                <option value={90}>Rotate 90</option>
                <option value={180}>Rotate 180</option>
                <option value={270}>Rotate 270</option>
              </select>
              <button className="btn btn-ghost" onClick={() => setFlipH(v => !v)} style={{ justifyContent: 'flex-start', background: flipH ? 'var(--c-surface2)' : '' }}>
                <FlipHorizontal size={14} /> Flip horizontal
              </button>
              <button className="btn btn-ghost" onClick={() => setFlipV(v => !v)} style={{ justifyContent: 'flex-start', background: flipV ? 'var(--c-surface2)' : '' }}>
                <FlipVertical size={14} /> Flip vertical
              </button>
            </div>

            <div style={{ display: 'grid', gap: 8 }}>
              <label className="label"><Scissors size={12} /> Trim</label>
              <input className="input" type="number" min={0} max={Math.max(duration, 0)} step="0.1" value={start} onChange={e => setStart(Math.max(0, parseFloat(e.target.value) || 0))} />
              <input className="input" type="number" min={0} max={Math.max(duration, 0)} step="0.1" value={end} onChange={e => setEnd(parseFloat(e.target.value) || 0)} />
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', padding: 14, borderTop: '1px solid var(--c-border)' }}>
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={save} disabled={saving || end <= start}>
            {saving ? 'Saving...' : <><Check size={13} /> Save copy</>}
          </button>
        </div>
      </div>
    </div>
  )
}
