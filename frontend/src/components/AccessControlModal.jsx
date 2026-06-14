import { useState, useEffect } from 'react'
import { X, UserPlus, Trash2, Shield, Eye, MessageCircle } from 'lucide-react'
import { api } from '../hooks/useAuth'
import toast from 'react-hot-toast'

export default function AccessControlModal({ type, id, onClose, title }) {
  const [grants, setGrants] = useState([])
  const [loading, setLoading] = useState(true)
  const [email, setEmail] = useState('')
  const [permission, setPermission] = useState('view')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => { loadGrants() }, [id])

  const loadGrants = async () => {
    try {
      const { data } = await api.get('/api/access/', { params: { target_type: type, target_id: id } })
      setGrants(data)
    } catch (err) {
      toast.error('Failed to load access list')
    } finally {
      setLoading(false)
    }
  }

  const addGrant = async (e) => {
    e.preventDefault()
    if (!email.trim()) return
    setSubmitting(true)
    try {
      await api.post('/api/access/', {
        grantee_email: email.trim().toLowerCase(),
        target_type: type,
        target_id: id,
        permission
      })
      toast.success('Access granted')
      setEmail(''); loadGrants()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to grant access')
    } finally {
      setSubmitting(false)
    }
  }

  const revoke = async (grantId) => {
    try {
      await api.delete(`/api/access/${grantId}`)
      setGrants(p => p.filter(g => g.id !== grantId))
      toast.success('Access revoked')
    } catch {
      toast.error('Failed to revoke access')
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="card share-modal" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <div>
            <h2 className="section-title">Manage Access</h2>
            <p style={{ color: 'var(--c-brown-lt)', fontSize: 12.5, marginTop: 2 }}>{title}</p>
          </div>
          <button className="btn-icon" onClick={onClose}><X size={18} /></button>
        </div>

        <form onSubmit={addGrant} style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          <div style={{ flex: 1 }}>
            <input
              className="input"
              type="email"
              placeholder="User email address..."
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
          </div>
          <select className="input" style={{ width: 110 }} value={permission} onChange={e => setPermission(e.target.value)}>
            <option value="view">View</option>
            <option value="comment">Comment</option>
          </select>
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            <UserPlus size={14} /> Invite
          </button>
        </form>

        <div style={{ borderTop: '1px solid var(--c-border)', paddingTop: 18 }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--c-brown-lt)', marginBottom: 12 }}>Users with access</h3>
          {loading ? <div className="spinner" style={{ margin: '20px auto' }} /> :
           grants.length === 0 ? <p style={{ fontSize: 13, color: 'var(--c-brown-lt)', textAlign: 'center', py: 10 }}>No private invites yet.</p> :
           <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
             {grants.map(g => (
               <div key={g.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--c-parchment)', padding: '10px 14px', borderRadius: 9 }}>
                 <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                   <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--c-gold)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: 14 }}>
                     {g.grantee_email[0].toUpperCase()}
                   </div>
                   <div>
                     <div style={{ fontSize: 13.5, fontWeight: 500 }}>{g.grantee_email}</div>
                     <div style={{ fontSize: 11.5, color: 'var(--c-brown-lt)', display: 'flex', alignItems: 'center', gap: 4 }}>
                       {g.permission === 'view' ? <Eye size={10} /> : <MessageCircle size={10} />}
                       {g.permission === 'view' ? 'Can view' : 'Can comment'}
                     </div>
                   </div>
                 </div>
                 <button className="btn btn-icon btn-ghost" onClick={() => revoke(g.id)} title="Revoke access">
                   <Trash2 size={14} />
                 </button>
               </div>
             ))}
           </div>
          }
        </div>
      </div>
    </div>
  )
}
