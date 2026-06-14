import { useState } from 'react'
import { X, Copy, Lock, Calendar, Globe, Shield } from 'lucide-react'
import { api } from '../hooks/useAuth'
import toast from 'react-hot-toast'

export default function ItemShareModal({ item, onUpdate, onClose }) {
  const [enabled, setEnabled] = useState(item.privacy === 'shared')
  const [password, setPassword] = useState('')
  const [expiresAt, setExpiresAt] = useState(item.share_expires_at ? item.share_expires_at.split('T')[0] : '')
  const [loading, setLoading] = useState(false)

  const save = async () => {
    setLoading(true)
    try {
      const { data } = await api.post(`/api/media/${item.id}/share`, {
        enabled,
        password: password || undefined,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null
      })
      onUpdate(data)
      toast.success(enabled ? 'Sharing enabled' : 'Sharing disabled')
      if (!enabled) onClose()
    } catch {
      toast.error('Failed to update sharing settings')
    } finally {
      setLoading(false)
    }
  }

  const shareUrl = `${window.location.origin}/shared/item/${item.share_token}`

  const copy = () => {
    navigator.clipboard.writeText(shareUrl)
    toast.success('Link copied to clipboard')
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="card share-modal" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <h2 className="section-title">Share Memory</h2>
          <button className="btn-icon" onClick={onClose}><X size={18} /></button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Globe size={20} color={enabled ? 'var(--c-gold)' : 'var(--c-brown-lt)'} />
            <div>
              <div style={{ fontWeight: 600, fontSize: 14 }}>Enable Public Link</div>
              <div style={{ fontSize: 12, color: 'var(--c-brown-lt)' }}>Anyone with the link can view</div>
            </div>
          </div>
          <input
            type="checkbox"
            checked={enabled}
            onChange={e => setEnabled(e.target.checked)}
            style={{ width: 18, height: 18 }}
          />
        </div>

        {enabled && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, animation: 'fadeIn 0.2s' }}>
            <div style={{ background: 'var(--c-parchment)', padding: '12px 14px', borderRadius: 9, display: 'flex', alignItems: 'center', gap: 10 }}>
              <input className="input" style={{ flex: 1, background: 'transparent', border: 'none', padding: 0, fontSize: 13 }} value={shareUrl} readOnly />
              <button className="btn btn-ghost" style={{ padding: '6px 10px' }} onClick={copy}><Copy size={14} /> Copy</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label className="label"><Lock size={12} /> Password (optional)</label>
                <input
                  className="input"
                  type="password"
                  placeholder={item.share_has_password ? '••••••••' : 'Set password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                />
              </div>
              <div>
                <label className="label"><Calendar size={12} /> Expiry date (optional)</label>
                <input
                  className="input"
                  type="date"
                  value={expiresAt}
                  onChange={e => setExpiresAt(e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, marginTop: 24, justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={save} disabled={loading}>
            {loading ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  )
}
