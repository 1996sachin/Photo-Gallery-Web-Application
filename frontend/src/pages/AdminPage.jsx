import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { Activity, Database, HardDrive, Search, Shield, Users } from 'lucide-react'
import { api } from '../hooks/useAuth'

const roles = ['admin', 'business', 'client']

function formatBytes(bytes = 0) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

function StatCard({ icon: Icon, label, value, detail }) {
  return (
    <div className="card" style={{ padding: 18, minHeight: 116 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, color: 'var(--c-brown-lt)', marginBottom: 8 }}>{label}</div>
          <div style={{ fontSize: 25, fontWeight: 700, color: 'var(--c-brown)' }}>{value}</div>
        </div>
        <div style={{
          width: 38, height: 38, borderRadius: 8,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'var(--c-surface2)', border: '1px solid var(--c-border)',
          color: 'var(--c-gold)',
        }}>
          <Icon size={18} />
        </div>
      </div>
      {detail && <div style={{ fontSize: 12, color: 'var(--c-brown-lt)', marginTop: 12 }}>{detail}</div>}
    </div>
  )
}

export default function AdminPage() {
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  const roleCounts = useMemo(() => stats?.users_by_role || {}, [stats])

  async function loadAdminData() {
    setLoading(true)
    try {
      const [statsRes, usersRes, auditRes] = await Promise.all([
        api.get('/api/admin/stats'),
        api.get('/api/admin/users', { params: { search: search || undefined, per_page: 25 } }),
        api.get('/api/admin/audit-logs', { params: { per_page: 25 } }),
      ])
      setStats(statsRes.data)
      setUsers(usersRes.data.items)
      setAuditLogs(auditRes.data.items)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Unable to load admin dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(loadAdminData, 250)
    return () => clearTimeout(timer)
  }, [search])

  async function updateRole(user, role) {
    try {
      const { data } = await api.patch(`/api/admin/users/${user.id}`, { role })
      setUsers(prev => prev.map(item => item.id === user.id ? data : item))
      toast.success('Role updated')
      const statsRes = await api.get('/api/admin/stats')
      setStats(statsRes.data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not update role')
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 22 }}>
        <div>
          <h1 className="page-title">Admin Panel</h1>
          <p style={{ color: 'var(--c-brown-lt)', fontSize: 13.5, marginTop: 6 }}>
            Manage users, review access controls, and monitor system activity.
          </p>
        </div>
        <button className="btn btn-ghost" onClick={loadAdminData} disabled={loading}>
          {loading ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Refreshing</> : <><Activity size={15} /> Refresh</>}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 12, marginBottom: 18 }}>
        <StatCard icon={Users} label="Users" value={stats?.total_users ?? '-'} detail={`${stats?.verified_users ?? 0} verified, ${stats?.mfa_users ?? 0} with MFA`} />
        <StatCard icon={Shield} label="Admins" value={roleCounts.admin ?? 0} detail={`${roleCounts.business ?? 0} business, ${roleCounts.client ?? 0} clients`} />
        <StatCard icon={Database} label="Media Items" value={stats?.media_count ?? '-'} detail={Object.keys(stats?.media_by_type || {}).join(', ') || 'No uploads yet'} />
        <StatCard icon={HardDrive} label="Storage" value={formatBytes(stats?.total_storage_bytes)} detail="Original uploaded files" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.35fr) minmax(320px, 0.85fr)', gap: 16, alignItems: 'start' }}>
        <section className="card" style={{ padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 14 }}>
            <h2 className="section-title">User Management</h2>
            <div style={{ position: 'relative', width: 260, maxWidth: '100%' }}>
              <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--c-brown-lt)' }} />
              <input className="input" style={{ paddingLeft: 31 }} value={search} onChange={e => setSearch(e.target.value)} placeholder="Search users" />
            </div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="admin-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Status</th>
                  <th>MFA</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{user.display_name}</div>
                      <div style={{ color: 'var(--c-brown-lt)', fontSize: 12 }}>{user.email}</div>
                    </td>
                    <td><span className="badge">{user.email_verified ? 'Verified' : 'Pending'}</span></td>
                    <td><span className="badge">{user.mfa_enabled ? 'Enabled' : 'Off'}</span></td>
                    <td>
                      <select className="input" value={user.role} onChange={e => updateRole(user, e.target.value)} style={{ width: 132 }}>
                        {roles.map(role => <option key={role} value={role}>{role}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card" style={{ padding: 18 }}>
          <h2 className="section-title" style={{ marginBottom: 14 }}>Audit Trail</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {auditLogs.map(log => (
              <div key={log.id} style={{ paddingBottom: 10, borderBottom: '1px solid var(--c-border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 4 }}>
                  <strong style={{ fontSize: 13 }}>{log.action}</strong>
                  <span style={{ color: 'var(--c-brown-lt)', fontSize: 11 }}>{log.ip_address || 'no ip'}</span>
                </div>
                <div style={{ color: 'var(--c-brown-lt)', fontSize: 12, lineHeight: 1.5 }}>
                  {log.user_email || 'System'} · {log.created_at ? new Date(log.created_at).toLocaleString() : 'Unknown time'}
                </div>
              </div>
            ))}
            {!auditLogs.length && <div className="empty-state" style={{ padding: 28 }}>No audit activity yet.</div>}
          </div>
        </section>
      </div>
    </div>
  )
}
