import { useEffect, useState } from 'react'
import { Mail, PenLine, Plus, Send, ShieldCheck, UserRound, Users } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '../hooks/useAuth'

export default function PeoplePage() {
  const [people, setPeople] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [inviteEmails, setInviteEmails] = useState({})
  const [form, setForm] = useState({ name: '', email: '', access_level: 'view' })

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/api/people/')
      setPeople(data)
    } finally {
      setLoading(false)
    }
  }

  const create = async () => {
    const name = form.name.trim()
    const email = form.email.trim().toLowerCase()
    if (!name || !email) return toast.error('Name and Gmail are required')
    if (!email.endsWith('@gmail.com')) return toast.error('Use a Gmail address')
    setSaving(true)
    try {
      const { data } = await api.post('/api/people/', { name, email, access_level: form.access_level })
      setPeople(p => [...p, data])
      setForm({ name: '', email: '', access_level: 'view' })
      setCreating(false)
      toast.success('Invite sent')
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not send invite')
    } finally {
      setSaving(false)
    }
  }

  const updateAccess = async (person, access_level) => {
    try {
      const { data } = await api.patch(`/api/people/${person.id}/access`, { access_level })
      setPeople(p => p.map(item => item.id === person.id ? data : item))
      toast.success('Access updated')
    } catch {
      toast.error('Could not update access')
    }
  }

  const resend = async person => {
    const email = (person.email || inviteEmails[person.id] || '').trim().toLowerCase()
    if (!email) return toast.error('Add a Gmail address first')
    if (!email.endsWith('@gmail.com')) return toast.error('Use a Gmail address')
    try {
      const { data } = await api.post(`/api/people/${person.id}/resend`, person.email ? {} : { email })
      setPeople(p => p.map(item => item.id === person.id ? data : item))
      setInviteEmails(values => {
        const next = { ...values }
        delete next[person.id]
        return next
      })
      toast.success('Invite resent')
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not resend invite')
    }
  }

  const initials = n => n.split(' ').filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase()
  const colors = ['#c8963c', '#7a9e7e', '#c87878', '#7878c8', '#5c8a9c']

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22, gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h1 className="page-title">People</h1>
          <p style={{ marginTop: 5, color: 'var(--c-brown-lt)', fontSize: 13.5 }}>
            Invite loved ones by Gmail and choose what they can do.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={14} /> Add Person</button>
      </div>

      {creating && (
        <div className="card people-form">
          <div>
            <label className="label">Name</label>
            <input
              className="input"
              placeholder="e.g. Mom, Grandpa, Best Friend"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              autoFocus
            />
          </div>
          <div>
            <label className="label">Gmail</label>
            <input
              className="input"
              type="email"
              placeholder="person@gmail.com"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              onKeyDown={e => e.key === 'Enter' && create()}
            />
          </div>
          <div>
            <label className="label">Access</label>
            <div className="segmented">
              <button className={form.access_level === 'view' ? 'active' : ''} onClick={() => setForm(f => ({ ...f, access_level: 'view' }))}>
                <ShieldCheck size={13} /> View
              </button>
              <button className={form.access_level === 'edit' ? 'active' : ''} onClick={() => setForm(f => ({ ...f, access_level: 'edit' }))}>
                <PenLine size={13} /> Edit
              </button>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-primary" onClick={create} disabled={saving}>
              {saving ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Sending</> : <><Send size={14} /> Send Invite</>}
            </button>
            <button className="btn btn-ghost" onClick={() => setCreating(false)}>Cancel</button>
          </div>
        </div>
      )}

      {loading ? <div className="empty-state"><div className="spinner" /></div>
      : people.length === 0 ? (
        <div className="empty-state"><Users size={56} /><h3>No people added</h3><p>Add loved ones by Gmail to share memories with view or edit access.</p></div>
      ) : (
        <div className="people-grid">
          {people.map((p, i) => (
            <div key={p.id} className="card person-card">
              <div className="person-avatar" style={{ color: colors[i % colors.length], background: colors[i % colors.length] + '22', borderColor: colors[i % colors.length] + '44' }}>
                {p.avatar_url ? <img src={p.avatar_url} alt={p.name} /> : (initials(p.name) || <UserRound size={18} />)}
              </div>
              <div className="person-body">
                <div className="person-name">{p.name}</div>
                {p.email ? (
                  <div className="person-email"><Mail size={12} /> {p.email}</div>
                ) : (
                  <input
                    className="input"
                    type="email"
                    placeholder="person@gmail.com"
                    value={inviteEmails[p.id] || ''}
                    onChange={e => setInviteEmails(values => ({ ...values, [p.id]: e.target.value }))}
                    onKeyDown={e => e.key === 'Enter' && resend(p)}
                    style={{ marginTop: 7 }}
                  />
                )}
                <div className="segmented compact" aria-label={`Access for ${p.name}`}>
                  <button className={p.access_level === 'view' ? 'active' : ''} onClick={() => updateAccess(p, 'view')}>View</button>
                  <button className={p.access_level === 'edit' ? 'active' : ''} onClick={() => updateAccess(p, 'edit')}>Edit</button>
                </div>
              </div>
              <button className="btn btn-ghost" onClick={() => resend(p)}><Send size={13} /> Resend</button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
