import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../hooks/useAuth'
import { Camera, Heart } from 'lucide-react'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, register } = useAuthStore()
  const [mode, setMode] = useState('login')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ email: '', password: '', name: '' })
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async e => {
    e.preventDefault()
    setLoading(true)
    try {
      if (mode === 'login') {
        await login(form.email, form.password)
      } else {
        if (!form.name.trim()) { toast.error('Please enter your name'); setLoading(false); return }
        await register(form.email, form.password, form.name)
      }
      navigate('/')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Something went wrong')
    } finally { setLoading(false) }
  }

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
              {mode === 'login' ? 'Welcome back ✨' : 'Start your gallery'}
            </h2>

            <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
              {mode === 'register' && (
                <div>
                  <label className="label">Your name</label>
                  <input className="input" placeholder="e.g. Sarah & James" value={form.name} onChange={set('name')} required />
                </div>
              )}
              <div>
                <label className="label">Email address</label>
                <input className="input" type="email" placeholder="you@example.com" value={form.email} onChange={set('email')} required />
              </div>
              <div>
                <label className="label">Password</label>
                <input className="input" type="password" placeholder="••••••••" value={form.password} onChange={set('password')} required minLength={6} />
              </div>

              <button
                type="submit" className="btn btn-primary"
                style={{ width: '100%', justifyContent: 'center', padding: '12px', fontSize: 14.5, marginTop: 4, borderRadius: 10 }}
                disabled={loading}
              >
                {loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
              </button>
            </form>

            <p style={{ textAlign: 'center', marginTop: 18, fontSize: 13.5, color: 'var(--c-brown-lt)' }}>
              {mode === 'login' ? "New here? " : "Have an account? "}
              <button onClick={() => setMode(mode === 'login' ? 'register' : 'login')} style={{
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
