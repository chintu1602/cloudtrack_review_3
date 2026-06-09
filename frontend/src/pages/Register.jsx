import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

export default function Register() {
  const { register, microsoftLogin, showFlash } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', username: '', password: '', confirm_password: '', full_name: '', age: '', gender: '', weight: '', height: '' })
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState([])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setErrors([])
    try {
      const payload = { ...form, age: form.age ? parseInt(form.age) : null, weight: form.weight ? parseFloat(form.weight) : null, height: form.height ? parseFloat(form.height) : null }
      await register(payload)
      showFlash('Registration successful! Welcome to NutriAI.', 'success')
      navigate('/dashboard')
    } catch (err) {
      setErrors(err.response?.data?.errors || ['Registration failed. Please try again.'])
    } finally {
      setLoading(false)
    }
  }

  const handleMicrosoft = async () => {
    try {
      const authUrl = await microsoftLogin()
      if (authUrl) window.location.href = authUrl
    } catch {
      setErrors(['Failed to initiate Microsoft registration.'])
    }
  }

  const update = (field, value) => setForm(prev => ({ ...prev, [field]: value }))

  return (
    <>
      <Navbar />
      <main style={{ paddingTop: '76px' }}>
        <div className="container py-5">
          <div className="auth-card" style={{ maxWidth: '560px' }}>
            <div className="text-center mb-4">
              <i className="fas fa-leaf text-primary-green" style={{ fontSize: '2.5rem' }}></i>
              <h3 className="fw-bold mt-2">Create Account</h3>
              <p className="text-muted">Join NutriAI for personalized nutrition</p>
            </div>

            {errors.length > 0 && (
              <div className="alert alert-danger">{errors.map((e, i) => <div key={i}><i className="fas fa-exclamation-circle me-2"></i>{e}</div>)}</div>
            )}

            <button className="btn-microsoft" onClick={handleMicrosoft}>
              <svg width="20" height="20" viewBox="0 0 21 21"><rect x="1" y="1" width="9" height="9" fill="#F25022"/><rect x="11" y="1" width="9" height="9" fill="#7FBA00"/><rect x="1" y="11" width="9" height="9" fill="#00A4EF"/><rect x="11" y="11" width="9" height="9" fill="#FFB900"/></svg>
              Register with Microsoft
            </button>

            <div className="auth-divider"><span>OR</span></div>

            <form onSubmit={handleSubmit}>
              <div className="row g-3">
                <div className="col-12">
                  <label className="form-label-nutriai">Full Name *</label>
                  <input className="form-control form-control-nutriai" value={form.full_name} onChange={e => update('full_name', e.target.value)} required />
                </div>
                <div className="col-md-6">
                  <label className="form-label-nutriai">Email Address *</label>
                  <input type="email" className="form-control form-control-nutriai" value={form.email} onChange={e => update('email', e.target.value)} required />
                </div>
                <div className="col-md-6">
                  <label className="form-label-nutriai">Username *</label>
                  <input className="form-control form-control-nutriai" value={form.username} onChange={e => update('username', e.target.value)} required minLength={3} />
                </div>
                <div className="col-md-6">
                  <label className="form-label-nutriai">Password *</label>
                  <input type="password" className="form-control form-control-nutriai" value={form.password} onChange={e => update('password', e.target.value)} required minLength={6} />
                </div>
                <div className="col-md-6">
                  <label className="form-label-nutriai">Confirm Password *</label>
                  <input type="password" className="form-control form-control-nutriai" value={form.confirm_password} onChange={e => update('confirm_password', e.target.value)} required />
                </div>
                <div className="col-md-4">
                  <label className="form-label-nutriai">Age</label>
                  <input type="number" className="form-control form-control-nutriai" value={form.age} onChange={e => update('age', e.target.value)} min={1} max={150} />
                </div>
                <div className="col-md-4">
                  <label className="form-label-nutriai">Gender</label>
                  <select className="form-control form-control-nutriai" value={form.gender} onChange={e => update('gender', e.target.value)}>
                    <option value="">Select</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div className="col-md-4">
                  <label className="form-label-nutriai">Weight (kg)</label>
                  <input type="number" step="0.1" className="form-control form-control-nutriai" value={form.weight} onChange={e => update('weight', e.target.value)} />
                </div>
              </div>
              <button type="submit" className="btn btn-nutriai-primary w-100 mt-4" disabled={loading}>
                {loading ? <><span className="spinner-border spinner-border-sm me-2"></span>Creating Account...</> : <><i className="fas fa-user-plus me-2"></i>Create Account</>}
              </button>
            </form>

            <p className="text-center mt-4 mb-0" style={{ fontSize: '0.9rem' }}>
              Already have an account? <Link to="/login" className="text-primary-green fw-600">Sign In</Link>
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
