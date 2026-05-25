import { useState } from 'react'
import { X, Check } from 'lucide-react'
import { api } from '../hooks/useAuth'
import toast from 'react-hot-toast'

const FILTERS = [
  { name: 'original', label: 'Original', css: '' },
  { name: 'warm',     label: 'Warm',     css: 'sepia(0.25) saturate(1.35) brightness(1.05)' },
  { name: 'cool',     label: 'Cool',     css: 'hue-rotate(18deg) saturate(0.88)' },
  { name: 'sepia',    label: 'Sepia',    css: 'sepia(0.78)' },
  { name: 'bw',       label: 'B&W',      css: 'grayscale(1)' },
  { name: 'fade',     label: 'Fade',     css: 'contrast(0.82) saturate(0.72) brightness(1.08)' },
  { name: 'vivid',    label: 'Vivid',    css: 'saturate(1.7) contrast(1.1)' },
  { name: 'golden',   label: 'Golden',   css: 'sepia(0.45) saturate(1.5) hue-rotate(-8deg)' },
]

export default function PhotoEditor({ item, onClose, onSaved }) {
  const [activeFilter, setActiveFilter] = useState('original')
  const [rotation, setRotation] = useState(0)
  const [brightness, setBrightness] = useState(1)
  const [contrast, setContrast] = useState(1)
  const [saturation, setSaturation] = useState(1)
  const [saving, setSaving] = useState(false)
  const [tab, setTab] = useState('filters')

  const previewFilter = () => {
    const f = FILTERS.find(f => f.name === activeFilter)?.css || ''
    const adj = `brightness(${brightness}) contrast(${contrast}) saturate(${saturation})`
    return [adj, f].filter(Boolean).join(' ')
  }

  const save = async () => {
    setSaving(true)
    try {
      const calls = []
      if (activeFilter !== 'original') calls.push(api.post('/api/edits/photo', { media_id: item.id, edit_type: 'filter', params: { name: activeFilter } }))
      if (rotation !== 0) calls.push(api.post('/api/edits/photo', { media_id: item.id, edit_type: 'rotate', params: { degrees: rotation } }))
      if (brightness !== 1 || contrast !== 1 || saturation !== 1) calls.push(api.post('/api/edits/photo', { media_id: item.id, edit_type: 'adjust', params: { brightness, contrast, saturation } }))
      await Promise.all(calls)
      onSaved()
    } catch { toast.error('Edit failed') }
    finally { setSaving(false) }
  }

  const Tab = ({ id, label }) => (
    <button onClick={() => setTab(id)} style={{
      flex: 1, padding: '7px', border: 'none', cursor: 'pointer', borderRadius: 7,
      fontSize: 12.5, fontWeight: 500, fontFamily: 'var(--sans)',
      background: tab === id ? 'var(--c-surface)' : 'transparent',
      color: tab === id ? 'var(--c-brown)' : 'var(--c-brown-lt)',
      transition: 'all 0.15s', boxShadow: tab === id ? 'var(--shadow-sm)' : 'none',
    }}>{label}</button>
  )

  const Slider = ({ label, value, onChange, min = 0.4, max = 2, step = 0.05 }) => (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <label className="label" style={{ margin: 0 }}>{label}</label>
        <span style={{ fontSize: 11.5, color: 'var(--c-brown-lt)' }}>{value.toFixed(2)}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        style={{ width: '100%', accentColor: 'var(--c-gold)' }} />
    </div>
  )

  return (
    <div className="overlay">
      <div className="card" style={{ width: '96%', maxWidth: 860, padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column', maxHeight: '92vh' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '15px 20px', borderBottom: '1px solid var(--c-border)', flexShrink: 0 }}>
          <h2 style={{ fontFamily: 'var(--serif)', fontSize: 19 }}>Edit Photo</h2>
          <button className="btn btn-icon btn" onClick={onClose}><X size={16} /></button>
        </div>

        <div style={{ display: 'flex', flex: 1, overflow: 'hidden', minHeight: 0 }}>
          {/* Preview */}
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#1a120a', padding: 20, overflow: 'hidden' }}>
            <img
              src={item.file_url} alt="preview"
              style={{
                maxWidth: '100%', maxHeight: '58vh', objectFit: 'contain', borderRadius: 8,
                filter: previewFilter(),
                transform: `rotate(${rotation}deg)`,
                transition: 'filter 0.3s, transform 0.3s',
              }}
            />
          </div>

          {/* Controls */}
          <div style={{ width: 252, borderLeft: '1px solid var(--c-border)', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
            <div style={{ display: 'flex', background: 'var(--c-surface2)', margin: 14, borderRadius: 9, padding: 3, gap: 3, flexShrink: 0 }}>
              <Tab id="filters" label="Filters" />
              <Tab id="adjust"  label="Adjust" />
              <Tab id="transform" label="Transform" />
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '0 14px' }}>
              {tab === 'filters' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 7 }}>
                  {FILTERS.map(f => (
                    <button key={f.name} onClick={() => setActiveFilter(f.name)} style={{
                      padding: '10px 6px', borderRadius: 8, cursor: 'pointer',
                      border: `2px solid ${activeFilter === f.name ? 'var(--c-gold)' : 'transparent'}`,
                      background: 'var(--c-surface2)', fontSize: 12, fontWeight: activeFilter === f.name ? 600 : 400,
                      color: activeFilter === f.name ? 'var(--c-gold-dk)' : 'var(--c-brown-lt)',
                      fontFamily: 'var(--sans)', transition: 'all 0.15s',
                    }}>{f.label}</button>
                  ))}
                </div>
              )}
              {tab === 'adjust' && (
                <>
                  <Slider label="Brightness" value={brightness} onChange={setBrightness} />
                  <Slider label="Contrast"   value={contrast}   onChange={setContrast} />
                  <Slider label="Saturation" value={saturation} onChange={setSaturation} />
                  <button className="btn btn-ghost" style={{ width: '100%', justifyContent: 'center', fontSize: 12.5 }}
                    onClick={() => { setBrightness(1); setContrast(1); setSaturation(1) }}>
                    Reset adjustments
                  </button>
                </>
              )}
              {tab === 'transform' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {[0, 90, 180, 270].map(deg => (
                    <button key={deg} className="btn btn-ghost" style={{ justifyContent: 'flex-start', fontSize: 13, background: rotation === deg ? 'var(--c-surface2)' : '' }}
                      onClick={() => setRotation(deg)}>
                      Rotate {deg === 0 ? 'none' : deg + '°'}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: 8, padding: 14, borderTop: '1px solid var(--c-border)', flexShrink: 0 }}>
              <button className="btn btn-ghost" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
              <button className="btn btn-primary" style={{ flex: 1 }} onClick={save} disabled={saving}>
                {saving ? 'Saving…' : <><Check size={13} /> Save</>}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
