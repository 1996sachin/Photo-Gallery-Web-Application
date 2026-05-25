import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { KeyRound, LogOut, MailCheck, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../hooks/useAuth'

export default function VerifyOtpPage() {
  const navigate = useNavigate()
  const { user, logout, requestEmailVerification, verifyEmailOtp } = useAuthStore()
  const [code, setCode] = useState('')
  const [checking, setChecking] = useState(false)
  const [sending, setSending] = useState(false)

  useEffect(() => {
    if (user?.email_verified) navigate('/', { replace: true })
  }, [navigate, user])

  const submit = async e => {
    e.preventDefault()
    setChecking(true)
    try {
      await verifyEmailOtp(code)
      toast.success('Gmail verified')
      navigate('/', { replace: true })
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid verification code')
    } finally {
      setChecking(false)
    }
  }

  const resend = async () => {
    setSending(true)
    try {
      const data = await requestEmailVerification()
      toast.success(data.message || 'Verification code sent')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not send code')
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
      background: 'linear-gradient(135deg, #fdf8f0 0%, #f5ead8 50%, #ede0c4 100%)',
    }}>
      <div className="card" style={{ width: '100%', maxWidth: 420, padding: 34 }}>
        <div style={{ textAlign: 'center', marginBottom: 26 }}>
          <div style={{
            width: 56,
            height: 56,
            borderRadius: 16,
            background: 'var(--c-gold)',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 15px',
          }}>
            <MailCheck size={25} />
          </div>
          <h1 style={{ fontFamily: 'var(--serif)', fontSize: 26, fontWeight: 500, marginBottom: 7 }}>
            Verify your Gmail
          </h1>
          <p style={{ fontSize: 13.5, color: 'var(--c-brown-lt)', lineHeight: 1.6 }}>
            Enter the 6 digit code sent to {user?.email || 'your Gmail account'}.
          </p>
        </div>

        <form onSubmit={submit} style={{ display: 'grid', gap: 15 }}>
          <div>
            <label className="label">Verification code</label>
            <input
              className="input"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              placeholder="000000"
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              style={{ textAlign: 'center', fontSize: 22, letterSpacing: 6, fontWeight: 600 }}
              required
            />
          </div>

          <button className="btn btn-primary" type="submit" disabled={checking || code.length !== 6} style={{ justifyContent: 'center', padding: 12 }}>
            {checking ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <KeyRound size={15} />}
            Verify and Continue
          </button>
        </form>

        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginTop: 16 }}>
          <button className="btn btn-ghost" type="button" onClick={resend} disabled={sending}>
            {sending ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <RefreshCw size={14} />}
            Resend
          </button>
          <button className="btn btn-ghost" type="button" onClick={logout}>
            <LogOut size={14} />
            Sign out
          </button>
        </div>
      </div>
    </div>
  )
}
