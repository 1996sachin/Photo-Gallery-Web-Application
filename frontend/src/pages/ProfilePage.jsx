import { useEffect, useState } from 'react'
import { Camera, CheckCircle2, KeyRound, MailCheck, Save } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, useAuthStore } from '../hooks/useAuth'

export default function ProfilePage() {
  const { user, setUser } = useAuthStore()
  const [form, setForm] = useState({ display_name: '', email: '', bio: '' })
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [googleBusy, setGoogleBusy] = useState(false)
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '', confirm_password: '' })

  useEffect(() => {
    api.get('/api/auth/me').then(({ data }) => setUser(data)).catch(() => {})
  }, [setUser])

  useEffect(() => {
    setForm({
      display_name: user?.display_name || '',
      email: user?.email || '',
      bio: user?.bio || '',
    })
  }, [user])

  const initials = form.display_name
    ? form.display_name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : '?'

  const save = async e => {
    e.preventDefault()
    setSaving(true)
    try {
      const { data } = await api.patch('/api/auth/me', {
        display_name: form.display_name,
        email: form.email,
        bio: form.bio,
      })
      setUser(data)
      toast.success('Profile updated')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not update profile')
    } finally {
      setSaving(false)
    }
  }

  const uploadAvatar = async e => {
    const file = e.target.files?.[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    setUploading(true)
    try {
      const { data } = await api.post('/api/auth/me/avatar', fd)
      setUser(data)
      toast.success('Photo updated')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not upload photo')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const requestVerification = async () => {
    setVerifying(true)
    try {
      const { data } = await api.post('/api/auth/me/request-email-verification')
      const refreshed = await api.get('/api/auth/me')
      setUser(refreshed.data)
      toast.success(data.message || 'Verification requested')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not request verification')
    } finally {
      setVerifying(false)
    }
  }

  const verifyWithGoogle = async () => {
    setGoogleBusy(true)
    try {
      const { data } = await api.get('/api/auth/google/start')
      window.location.href = data.auth_url
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Google OAuth is not configured')
      setGoogleBusy(false)
    }
  }

  const changePassword = async e => {
    e.preventDefault()
    if (passwordForm.new_password.length < 6) return toast.error('New password must be at least 6 characters')
    if (passwordForm.new_password !== passwordForm.confirm_password) return toast.error('New passwords do not match')
    setPasswordSaving(true)
    try {
      const { data } = await api.patch('/api/auth/me/password', {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      })
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
      toast.success(data.message || 'Password updated')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not update password')
    } finally {
      setPasswordSaving(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 22 }}>
        <h1 className="page-title">Profile</h1>
        <p style={{ fontSize: 13, color: 'var(--c-brown-lt)', marginTop: 4 }}>Manage your account details and photo.</p>
      </div>

      <div className="card" style={{ padding: 22, maxWidth: 1040 }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: 28,
          alignItems: 'start',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginBottom: 24 }}>
              <div style={{
                width: 74, height: 74, borderRadius: '50%', overflow: 'hidden', flexShrink: 0,
                background: 'linear-gradient(135deg, #c8963c, #8a5e1a)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 700, fontSize: 22, color: '#fff',
              }}>
                {user?.avatar_url
                  ? <img src={user.avatar_url} alt={form.display_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  : initials}
              </div>
              <div>
                <label className="btn btn-ghost" style={{ cursor: uploading ? 'default' : 'pointer' }}>
                  {uploading ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <Camera size={14} />}
                  {uploading ? 'Uploading...' : 'Add Photo'}
                  <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={uploadAvatar} disabled={uploading} style={{ display: 'none' }} />
                </label>
                <div style={{ fontSize: 11.5, color: 'var(--c-brown-lt)', marginTop: 7 }}>JPG, PNG, WEBP or GIF up to 5 MB.</div>
              </div>
            </div>
        <form onSubmit={save} style={{ display: 'grid', gap: 15 }}>
          <div>
            <label className="label">Name</label>
            <input className="input" value={form.display_name} onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))} required />
          </div>

          <div>
            <label className="label">Gmail account</label>
            <input className="input" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
          </div>

          <div>
            <label className="label">Bio</label>
            <textarea className="input" rows={4} value={form.bio} onChange={e => setForm(f => ({ ...f, bio: e.target.value }))} style={{ resize: 'vertical', minHeight: 92 }} />
          </div>

          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
            border: '1px solid var(--c-border)', borderRadius: 10, padding: '12px 14px',
            background: 'var(--c-surface2)', flexWrap: 'wrap',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, flex: '1 1 220px' }}>
              {user?.email_verified
                ? <CheckCircle2 size={18} color="#5a9a5a" />
                : <MailCheck size={18} color="var(--c-gold)" />}
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>
                  {user?.email_verified ? 'Gmail verified' : 'Gmail verification'}
                </div>
                <div style={{ fontSize: 11.5, color: 'var(--c-brown-lt)' }}>
                  {user?.email_verification_requested_at
                    ? `Requested ${new Date(user.email_verification_requested_at).toLocaleString()}`
                    : 'Use a Gmail address, then request verification.'}
                </div>
              </div>
            </div>
            <button type="button" className="btn btn-ghost" onClick={requestVerification} disabled={verifying || user?.email_verified}>
              {verifying ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <MailCheck size={14} />}
              {user?.email_verified ? 'Verified' : 'Send Code'}
            </button>
            <button type="button" className="btn btn-ghost" onClick={verifyWithGoogle} disabled={googleBusy || user?.email_verified}>
              {googleBusy ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <MailCheck size={14} />}
              Google
            </button>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <Save size={14} />}
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
          </div>

          <div style={{
            border: '1px solid var(--c-border)',
            borderRadius: 10,
            padding: 18,
            background: 'var(--c-surface2)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <KeyRound size={18} color="var(--c-gold)" />
              <div>
                <h2 className="section-title">Change Password</h2>
                <p style={{ fontSize: 12.5, color: 'var(--c-brown-lt)', marginTop: 3 }}>Use your current password to set a new one.</p>
              </div>
            </div>

            <form onSubmit={changePassword} style={{ display: 'grid', gap: 15 }}>
              <div>
                <label className="label">Current password</label>
                <input
                  className="input"
                  type="password"
                  value={passwordForm.current_password}
                  onChange={e => setPasswordForm(f => ({ ...f, current_password: e.target.value }))}
                  required
                />
              </div>
              <div>
                <label className="label">New password</label>
                <input
                  className="input"
                  type="password"
                  value={passwordForm.new_password}
                  onChange={e => setPasswordForm(f => ({ ...f, new_password: e.target.value }))}
                  required
                  minLength={6}
                />
              </div>
              <div>
                <label className="label">Confirm new password</label>
                <input
                  className="input"
                  type="password"
                  value={passwordForm.confirm_password}
                  onChange={e => setPasswordForm(f => ({ ...f, confirm_password: e.target.value }))}
                  required
                  minLength={6}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
                <button className="btn btn-primary" type="submit" disabled={passwordSaving}>
                  {passwordSaving ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <KeyRound size={14} />}
                  {passwordSaving ? 'Updating...' : 'Update Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
