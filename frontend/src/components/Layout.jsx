import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Images, BookImage, Heart, Users, LogOut, Upload, Search, X, Camera } from 'lucide-react'
import { useAuthStore } from '../hooks/useAuth'
import UploadModal from './UploadModal'

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [showUpload, setShowUpload] = useState(false)
  const [search, setSearch] = useState('')

  const initials = user?.display_name
    ? user.display_name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : '?'

  const navItems = [
    { to: '/',         icon: Images,     label: 'All Memories' },
    { to: '/albums',   icon: BookImage,  label: 'Albums' },
    { to: '/favorites',icon: Heart,      label: 'Favorites' },
    { to: '/people',   icon: Users,      label: 'People' },
  ]

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* ── Sidebar ── */}
      <aside style={{
        width: 232, flexShrink: 0, display: 'flex', flexDirection: 'column',
        background: 'linear-gradient(180deg, #1e1208 0%, #2c1e0f 100%)',
        borderRight: '1px solid rgba(200,150,60,0.12)',
      }}>
        {/* Logo */}
        <div style={{ padding: '28px 22px 22px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 34, height: 34, borderRadius: 10,
              background: 'rgba(200,150,60,0.2)', border: '1px solid rgba(200,150,60,0.35)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Camera size={17} color="#e8b86a" />
            </div>
            <div>
              <div style={{ fontFamily: 'var(--serif)', fontSize: 19, fontWeight: 600, color: '#e8b86a', lineHeight: 1.1 }}>
                Memories
              </div>
              <div style={{ fontSize: 10.5, color: 'rgba(245,230,208,0.38)', letterSpacing: '0.04em', marginTop: 1 }}>
                FOR THE ONES YOU LOVE
              </div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '16px 10px', display: 'flex', flexDirection: 'column', gap: 3 }}>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={to === '/'} style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 9,
              padding: '9px 12px', borderRadius: 9,
              fontFamily: 'var(--sans)', fontSize: 13.5, fontWeight: isActive ? 600 : 400,
              color: isActive ? '#e8b86a' : 'rgba(245,220,190,0.6)',
              background: isActive ? 'rgba(200,150,60,0.14)' : 'transparent',
              textDecoration: 'none', transition: 'all 0.15s',
              borderLeft: isActive ? '2px solid #c8963c' : '2px solid transparent',
            })}>
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Upload */}
        <div style={{ padding: '0 10px 14px' }}>
          <button
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center', padding: '10px', fontSize: 13.5 }}
            onClick={() => setShowUpload(true)}
          >
            <Upload size={15} /> Upload Memories
          </button>
        </div>

        {/* User */}
        <div onClick={() => navigate('/profile')} style={{
          margin: '0 10px 16px', padding: '12px 12px',
          borderRadius: 10, background: 'rgba(255,255,255,0.05)',
          border: '1px solid rgba(255,255,255,0.08)',
          display: 'flex', alignItems: 'center', gap: 9,
          cursor: 'pointer',
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
            background: 'linear-gradient(135deg, #c8963c, #8a5e1a)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            overflow: 'hidden',
            fontWeight: 700, fontSize: 12, color: '#fff',
          }}>
            {user?.avatar_url
              ? <img src={user.avatar_url} alt={user.display_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              : initials}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'rgba(245,230,200,0.92)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.display_name}
            </div>
            <div style={{ fontSize: 10.5, color: 'rgba(245,230,200,0.38)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.email}
            </div>
          </div>
          <button
            onClick={e => { e.stopPropagation(); logout(); navigate('/login') }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(245,230,200,0.35)', padding: 4, borderRadius: 6, transition: 'color 0.15s', flexShrink: 0 }}
            onMouseEnter={e => e.currentTarget.style.color = 'rgba(245,230,200,0.8)'}
            onMouseLeave={e => e.currentTarget.style.color = 'rgba(245,230,200,0.35)'}
            title="Sign out"
          >
            <LogOut size={14} />
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Top bar */}
        <header style={{
          padding: '12px 28px', display: 'flex', alignItems: 'center', gap: 12,
          background: 'rgba(253,248,240,0.92)', backdropFilter: 'blur(12px)',
          borderBottom: '1px solid var(--c-border)', flexShrink: 0,
          position: 'sticky', top: 0, zIndex: 50,
        }}>
          <div style={{ position: 'relative', flex: 1, maxWidth: 380 }}>
            <Search size={15} style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: 'var(--c-brown-lt)' }} />
            <input
              className="input" style={{ paddingLeft: 33, fontSize: 13 }}
              placeholder="Search memories, people, places…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </header>

        {/* Page */}
        <main style={{ flex: 1, overflow: 'auto', padding: '28px 28px 40px' }}>
          <Outlet context={{ search }} />
        </main>
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} />}
    </div>
  )
}
