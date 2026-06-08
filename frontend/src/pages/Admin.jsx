import { useState, useEffect } from 'react'
import api from '../api/axios'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import LoadingSpinner from '../components/LoadingSpinner'
import StatusBadge from '../components/StatusBadge'

export default function Admin() {
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [sRes, uRes, dRes] = await Promise.allSettled([
          api.get('/admin/dashboard'), api.get('/admin/users'), api.get('/admin/documents')
        ])
        if (sRes.status === 'fulfilled') setStats(sRes.value.data)
        if (uRes.status === 'fulfilled') setUsers(uRes.value.data)
        if (dRes.status === 'fulfilled') setDocuments(dRes.value.data)
      } catch {} finally { setLoading(false) }
    }
    fetchAll()
  }, [])

  const toggleUser = async (userId) => {
    try {
      const res = await api.post(`/admin/users/${userId}/toggle`)
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: res.data.is_active } : u))
    } catch (err) { alert(err.response?.data?.error || 'Failed.') }
  }

  if (loading) return <><Navbar /><main style={{ paddingTop: '76px' }}><LoadingSpinner /></main></>

  return (
    <>
      <Navbar />
      <main style={{ paddingTop: '76px' }}>
        <div className="container py-4 page-content">
          <div className="mb-4"><h3 className="fw-bold"><i className="fas fa-shield-alt text-primary-green me-2"></i>Admin Panel</h3><p className="text-muted">System overview and user management</p></div>

          {/* Stats */}
          <div className="row g-4 mb-4">
            {[
              { icon: 'fa-users', color: 'green', label: 'Total Users', val: stats?.total_users },
              { icon: 'fa-user-check', color: 'blue', label: 'Active Users', val: stats?.active_users },
              { icon: 'fa-file-medical', color: 'teal', label: 'Documents', val: stats?.total_documents },
              { icon: 'fa-utensils', color: 'orange', label: 'Diet Plans', val: stats?.total_diet_plans },
            ].map((s, i) => (
              <div key={i} className="col-6 col-lg-3">
                <div className={`stat-card ${s.color}`}><div className="d-flex align-items-center gap-3"><div className={`stat-icon ${s.color}`}><i className={`fas ${s.icon}`}></i></div><div><div className="stat-value">{s.val || 0}</div><div className="stat-label">{s.label}</div></div></div></div>
              </div>
            ))}
          </div>

          {/* Users */}
          <div className="content-card mb-4">
            <div className="card-header-custom"><h5><i className="fas fa-users text-primary-green me-2"></i>Users ({users.length})</h5></div>
            <div className="table-responsive"><table className="table table-nutriai mb-0"><thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Auth</th><th>Status</th><th>Actions</th></tr></thead><tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td className="fw-600">{u.username}</td>
                  <td>{u.email}</td>
                  <td><span className={`badge bg-${u.role === 'admin' ? 'warning' : 'primary'}`}>{u.role}</span></td>
                  <td>{u.auth_type === 'entra_id' ? 'SSO' : 'Local'}</td>
                  <td><span className={`badge bg-${u.is_active ? 'success' : 'danger'}`}>{u.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td><button className={`btn btn-sm ${u.is_active ? 'btn-outline-danger' : 'btn-outline-success'}`} onClick={() => toggleUser(u.id)}><i className={`fas ${u.is_active ? 'fa-ban' : 'fa-check'} me-1`}></i>{u.is_active ? 'Deactivate' : 'Activate'}</button></td>
                </tr>
              ))}
            </tbody></table></div>
          </div>

          {/* Documents */}
          <div className="content-card">
            <div className="card-header-custom"><h5><i className="fas fa-file-medical text-primary-green me-2"></i>All Documents ({documents.length})</h5></div>
            <div className="table-responsive"><table className="table table-nutriai mb-0"><thead><tr><th>Filename</th><th>User</th><th>Type</th><th>OCR Status</th><th>Uploaded</th></tr></thead><tbody>
              {documents.map(d => (
                <tr key={d.id}>
                  <td>{d.original_filename?.slice(0, 30)}{d.original_filename?.length > 30 ? '...' : ''}</td>
                  <td>{d.username}</td>
                  <td>{d.document_type?.replace(/_/g, ' ')}</td>
                  <td><StatusBadge status={d.ocr_status} /></td>
                  <td>{d.uploaded_at ? new Date(d.uploaded_at).toLocaleDateString() : '-'}</td>
                </tr>
              ))}
            </tbody></table></div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
