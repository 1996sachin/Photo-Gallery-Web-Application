import { useEffect, useState } from 'react'
import { Camera, CheckCircle2, MailCheck, Save, ShieldCheck, ShieldAlert, X } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, useAuthStore } from '../hooks/useAuth'

export default function ProfilePage() {
  const { user, setUser } = useAuthStore()
  const [form, setForm] = useState({ display_name: '', email: '', bio: '' })
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [googleBusy, setGoogleBusy] = useState(false)
  
  // MFA State
  const [mfaSetup, setMfaSetup] = useState(null) // {secret, qr_code}
  const [mfaCode, setMfaCode] = useState('')
  const [mfaBusy, setMfaBusy] = useState(false)

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

  const startMfaSetup = async () => {
    try {
      const { data } = await api.get('/api/auth/mfa/setup')
      setMfaSetup(data)
      setMfaCode('')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not start MFA setup')
    }
  }

  const enableMfa = async () => {
    setMfaBusy(true)
    try {
      await api.post('/api/auth/mfa/enable', { code: mfaCode, secret: mfaSetup.secret })
      const { data } = await api.get('/api/auth/me')
      setUser(data)
      setMfaSetup(null)
      toast.success('MFA enabled successfully! 🛡️')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid code')
    } finally {
      setMfaBusy(false)
    }
  }

  const disableMfa = async () => {
    const code = prompt('Enter your 6-digit MFA code to disable security:')
    if (!code) return
    setMfaBusy(true)
    try {
      await api.post('/api/auth/mfa/disable', { code })
      const { data } = await api.get('/api/auth/me')
      setUser(data)
      toast.success('MFA disabled')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid code')
    } finally {
      setMfaBusy(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 22 }}>
        <h1 className="page-title">Profile</h1>
        <p style={{ fontSize: 13, color: 'var(--c-brown-lt)', marginTop: 4 }}>Manage your account details and security.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 24, alignItems: 'start' }}>
        <div className="card" style={{ padding: 22 }}>
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
              background: 'var(--c-surface2)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                {user?.email_verified
                  ? <CheckCircle2 size={18} color="#5a9a5a" />
                  : <MailCheck size={18} color="var(--c-gold)" />}
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>
                    {user?.email_verified ? 'Gmail verified' : 'Gmail verification'}
                  </div>
                  <div style={{ fontSize: 11.5, color: 'var(--c-brown-lt)' }}>
                    {user?.email_verified ? 'Account is secure' : 'Verify your email for security.'}
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button type="button" className="btn btn-ghost" onClick={requestVerification} disabled={verifying || user?.email_verified}>
                  {verifying ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <MailCheck size={14} />}
                  {user?.email_verified ? 'Verified' : 'Send Code'}
                </button>
                <button type="button" className="btn btn-ghost" onClick={verifyWithGoogle} disabled={googleBusy || user?.email_verified}>
                  Google
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
              <button className="btn btn-primary" type="submit" disabled={saving}>
                {saving ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <Save size={14} />}
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>

        {/* Security Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              {user?.mfa_enabled ? <ShieldCheck size={20} color="#5a9a5a" /> : <ShieldAlert size={20} color="var(--c-gold)" />}
              <h3 style={{ fontSize: 15, fontWeight: 600 }}>Security</h3>
            </div>
            
            <p style={{ fontSize: 12.5, color: 'var(--c-brown-lt)', lineHeight: 1.5, marginBottom: 20 }}>
              Two-factor authentication adds an extra layer of security to your account by requiring more than just a password to log in.
            </p>

            {user?.mfa_enabled ? (
              <button className="btn btn-ghost" style={{ width: '100%', justifyContent: 'center' }} onClick={disableMfa} disabled={mfaBusy}>
                Disable MFA
              </button>
            ) : (
              <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={startMfaSetup}>
                Enable MFA
              </button>
            )}
          </div>
        </div>
      </div>

      {/* MFA Setup Modal */}
      {mfaSetup && (
        <div className="overlay">
          <div className="card" style={{ width: '100%', maxWidth: 400, padding: 32, textAlign: 'center' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 style={{ fontFamily: 'var(--serif)', fontSize: 20 }}>Setup MFA</h2>
              <button className="btn btn-icon" onClick={() => setMfaSetup(null)}><X size={16} /></button>
            </div>
            <p style={{ fontSize: 13, color: 'var(--c-brown-lt)', marginBottom: 20 }}>
              Scan this QR code with an authenticator app (like Google Authenticator or Authy).
            </p>
            <div style={{ background: '#fff', padding: 12, borderRadius: 12, display: 'inline-block', marginBottom: 20 }}>
              <img src={`data:image/png;base64,${mfaSetup.qr_code}`} alt="QR Code" style={{ width: 180, height: 180 }} />
            </div>
            <div style={{ textAlign: 'left', marginBottom: 20 }}>
              <label className="label">Verification Code</label>
              <input 
                className="input" 
                placeholder="000 000" 
                maxLength={6}
                value={mfaCode}
                onChange={e => setMfaCode(e.target.value.replace(/\D/g, ''))}
                style={{ textAlign: 'center', fontSize: 20, letterSpacing: 4 }}
              />
            </div>
            <button 
              className="btn btn-primary" 
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={enableMfa}
              disabled={mfaBusy || mfaCode.length < 6}
            >
              {mfaBusy ? 'Verifying...' : 'Verify & Enable'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
