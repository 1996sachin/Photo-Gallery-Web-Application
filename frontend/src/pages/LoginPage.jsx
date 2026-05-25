import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, useAuthStore } from '../hooks/useAuth'
import { Camera, Heart, KeyRound, MailCheck } from 'lucide-react'
import toast from 'react-hot-toast'

const getPasswordStrength = password => {
  const suggestions = []
  if (password.length < 8) suggestions.push('Use at least 8 characters')
  if (['password', 'password123', '123456', '12345678', 'qwerty'].includes(password.toLowerCase())) suggestions.push('Avoid common passwords')
  if (!/[a-z]/.test(password)) suggestions.push('Add a lowercase letter')
  if (!/[A-Z]/.test(password)) suggestions.push('Add an uppercase letter')
  if (!/\d/.test(password)) suggestions.push('Add a number')
  if (!/[^A-Za-z0-9]/.test(password)) suggestions.push('Add a symbol')
  const strength = password.length >= 12 && suggestions.length <= 1
    ? 'strong'
    : password.length >= 8 && suggestions.length <= 2
      ? 'medium'
      : 'weak'
  return { strength, suggestions }
}

const errorMessage = err => {
  const detail = err.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.message) return detail.message
  return 'Something went wrong'
}

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, register } = useAuthStore()
  const [mode, setMode] = useState('login')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ email: '', password: '', name: '' })
  const [resetStep, setResetStep] = useState('request')
  const [reset, setReset] = useState({ email: '', code: '', password: '' })
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))
  const setResetField = k => e => setReset(f => ({ ...f, [k]: e.target.value }))
  const passwordStrength = getPasswordStrength(form.password)

  const switchMode = next => {
    setMode(next)
    setLoading(false)
    if (next === 'forgot') {
      setReset(r => ({ ...r, email: form.email }))
      setResetStep('request')
    }
  }

  const submit = async e => {
    e.preventDefault()
    setLoading(true)
    try {
      if (mode === 'login') {
        const user = await login(form.email, form.password)
        navigate(user.email_verified ? '/' : '/verify-otp')
      } else {
        if (!form.name.trim()) { toast.error('Please enter your name'); setLoading(false); return }
        if (passwordStrength.strength === 'weak') {
          toast.error('Password is weak. Use the suggestions below.')
          setLoading(false)
          return
        }
        const user = await register(form.email, form.password, form.name)
        navigate(user.email_verified ? '/' : '/verify-otp')
      }
    } catch (err) {
      toast.error(errorMessage(err))
    } finally { setLoading(false) }
  }

  const requestReset = async e => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await api.post('/api/auth/forgot-password', { email: reset.email })
      toast.success(data.message || 'Reset code sent')
      setResetStep('confirm')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not send reset code')
    } finally { setLoading(false) }
  }

  const confirmReset = async e => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await api.post('/api/auth/reset-password', reset)
      toast.success(data.message || 'Password updated')
      setForm(f => ({ ...f, email: reset.email, password: '' }))
      switchMode('login')
    } catch (err) {
      toast.error(errorMessage(err) || 'Could not reset password')
    } finally { setLoading(false) }
  }

  const title = mode === 'login'
    ? 'Welcome back'
    : mode === 'register'
      ? 'Start your gallery'
      : 'Reset password'

  return (
    <div style={{
      minHeight: '100vh', display: 'flex',
      background: 'linear-gradient(135deg, #fdf8f0 0%, #f5ead8 50%, #ede0c4 100%)',
    }}>
      {/* Left panel */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 40,
      }}>
        <div style={{ width: '100%', maxWidth: 400 }}>
          {/* Brand */}
          <div style={{ marginBottom: 44, textAlign: 'center' }}>
            <div style={{
              width: 60, height: 60, borderRadius: 18,
              background: 'linear-gradient(135deg, #c8963c, #8a5e1a)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px', boxShadow: '0 8px 24px rgba(200,150,60,0.35)',
            }}>
              <Camera size={28} color="#fff" />
            </div>
            <h1 style={{ fontFamily: 'var(--serif)', fontSize: 38, fontWeight: 600, color: 'var(--c-brown)', letterSpacing: '-0.5px', marginBottom: 6 }}>
              Memories
            </h1>
            <p style={{ fontSize: 14.5, color: 'var(--c-brown-lt)', fontStyle: 'italic' }}>
              A private gallery for the ones you love
            </p>
          </div>

          {/* Card */}
          <div className="card" style={{ padding: 36 }}>
            <h2 style={{ fontFamily: 'var(--serif)', fontSize: 21, fontWeight: 500, marginBottom: 24, textAlign: 'center' }}>
              {title}
            </h2>

            {mode === 'forgot' ? (
              <form onSubmit={resetStep === 'request' ? requestReset : confirmReset} style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
                <div>
                  <label className="label">Gmail address</label>
                  <input className="input" type="email" placeholder="you@gmail.com" value={reset.email} onChange={setResetField('email')} required disabled={resetStep === 'confirm'} />
                </div>
                {resetStep === 'confirm' && (
                  <>
                    <div>
                      <label className="label">Reset code</label>
                      <input
                        className="input"
                        inputMode="numeric"
                        maxLength={6}
                        placeholder="000000"
                        value={reset.code}
                        onChange={e => setReset(r => ({ ...r, code: e.target.value.replace(/\D/g, '').slice(0, 6) }))}
                        required
                      />
                    </div>
                    <div>
                      <label className="label">New password</label>
                      <input className="input" type="password" placeholder="Minimum 6 characters" value={reset.password} onChange={setResetField('password')} required minLength={6} />
                    </div>
                  </>
                )}

                <button
                  type="submit" className="btn btn-primary"
                  style={{ width: '100%', justifyContent: 'center', padding: '12px', fontSize: 14.5, marginTop: 4, borderRadius: 10 }}
                  disabled={loading}
                >
                  {loading ? 'Please wait...' : resetStep === 'request' ? <><MailCheck size={15} /> Send reset code</> : <><KeyRound size={15} /> Update password</>}
                </button>
              </form>
            ) : (
              <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
                {mode === 'register' && (
                  <div>
                    <label className="label">Your name</label>
                    <input className="input" placeholder="e.g. Sarah & James" value={form.name} onChange={set('name')} required />
                  </div>
                )}
                <div>
                  <label className="label">Email address</label>
                  <input className="input" type="email" placeholder="you@gmail.com" value={form.email} onChange={set('email')} required />
                </div>
                <div>
                  <label className="label">Password</label>
                  <input className="input" type="password" placeholder="Minimum 6 characters" value={form.password} onChange={set('password')} required minLength={6} />
                </div>

                {mode === 'register' && form.password && (
                  <div style={{
                    border: '1px solid var(--c-border)',
                    borderRadius: 10,
                    padding: '10px 12px',
                    background: passwordStrength.strength === 'weak' ? 'rgba(201,64,64,.08)' : 'var(--c-surface2)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                      <span style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--c-brown)' }}>Password strength</span>
                      <span className="badge" style={{
                        color: passwordStrength.strength === 'weak' ? '#a83030' : passwordStrength.strength === 'medium' ? 'var(--c-gold-dk)' : '#4f8354',
                      }}>
                        {passwordStrength.strength === 'weak' ? 'Weak password' : passwordStrength.strength}
                      </span>
                    </div>
                    {passwordStrength.suggestions.length > 0 && (
                      <div style={{ display: 'grid', gap: 4, marginTop: 8 }}>
                        {passwordStrength.suggestions.map(item => (
                          <div key={item} style={{ fontSize: 12, color: 'var(--c-brown-lt)' }}>• {item}</div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {mode === 'login' && (
                  <button type="button" onClick={() => switchMode('forgot')} style={{
                    alignSelf: 'flex-end', background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--c-gold-dk)', fontWeight: 600, fontSize: 12.5, fontFamily: 'inherit',
                  }}>
                    Forgot password?
                  </button>
                )}

                <button
                  type="submit" className="btn btn-primary"
                  style={{ width: '100%', justifyContent: 'center', padding: '12px', fontSize: 14.5, marginTop: 4, borderRadius: 10 }}
                  disabled={loading || (mode === 'register' && form.password && passwordStrength.strength === 'weak')}
                >
                  {loading ? 'Please wait...' : mode === 'login' ? 'Sign in' : 'Create account'}
                </button>
              </form>
            )}

            <p style={{ textAlign: 'center', marginTop: 18, fontSize: 13.5, color: 'var(--c-brown-lt)' }}>
              {mode === 'login' ? "New here? " : "Remember your password? "}
              <button onClick={() => switchMode(mode === 'login' ? 'register' : 'login')} style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--c-gold-dk)', fontWeight: 600, fontSize: 13.5, fontFamily: 'inherit',
              }}>
                {mode === 'login' ? 'Create a gallery' : 'Sign in'}
              </button>
            </p>
          </div>

          <p style={{ textAlign: 'center', marginTop: 20, fontSize: 12.5, color: 'var(--c-brown-lt)', opacity: .6, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
            <Heart size={11} fill="currentColor" /> Your memories, stored privately
          </p>
        </div>
      </div>

      {/* Right decorative panel */}
      <div style={{
        width: '42%', background: 'linear-gradient(160deg, #2c1e0f 0%, #4a2e10 60%, #3a2510 100%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 48,
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Decorative circles */}
        {[
          { size: 320, top: -60, right: -80, opacity: 0.06 },
          { size: 200, bottom: 40, left: -50, opacity: 0.08 },
          { size: 100, top: '40%', left: '30%', opacity: 0.05 },
        ].map((c, i) => (
          <div key={i} style={{
            position: 'absolute',
            width: c.size, height: c.size, borderRadius: '50%',
            border: '1px solid rgba(200,150,60,' + c.opacity * 8 + ')',
            top: c.top, bottom: c.bottom, left: c.left, right: c.right,
            background: 'radial-gradient(circle, rgba(200,150,60,' + c.opacity + ') 0%, transparent 70%)',
          }} />
        ))}
        <div style={{ position: 'relative', textAlign: 'center' }}>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 32, fontWeight: 500, color: 'rgba(232,184,106,0.9)', lineHeight: 1.35, marginBottom: 20 }}>
            "Preserve every<br/>precious moment"
          </div>
          <div style={{ fontSize: 13, color: 'rgba(245,220,180,0.45)', letterSpacing: '0.06em' }}>
            PHOTOS · VIDEOS · MEMORIES
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 10, marginTop: 36 }}>
            {['❤️', '📸', '🎬', '✨'].map((e, i) => (
              <div key={i} style={{
                width: 44, height: 44, borderRadius: 12,
                background: 'rgba(200,150,60,0.12)', border: '1px solid rgba(200,150,60,0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20,
              }}>{e}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
