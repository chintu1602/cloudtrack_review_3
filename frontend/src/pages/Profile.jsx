import { useState, useEffect } from 'react'
import api from '../api/axios'
import useAuth from '../hooks/useAuth'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import LoadingSpinner from '../components/LoadingSpinner'

export default function Profile() {
  const { user: authUser, fetchUser } = useAuth()
  const [profile, setProfile] = useState(null)
  const [allergies, setAllergies] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({})
  const [medForm, setMedForm] = useState({ medical_conditions: '', dietary_preferences: '' })
  const [allergyForm, setAllergyForm] = useState({ allergen_name: '', severity: 'moderate', notes: '' })

  useEffect(() => {
    api.get('/profile').then(res => {
      const d = res.data
      setProfile(d.profile)
      setAllergies(d.allergies)
      setForm({ full_name: d.user.full_name, age: d.user.age || '', gender: d.user.gender || '', weight: d.user.weight || '', height: d.user.height || '', blood_type: d.profile?.blood_type || '', emergency_contact: d.profile?.emergency_contact || '' })
      setMedForm({ medical_conditions: (d.profile?.medical_conditions || []).join(', '), dietary_preferences: (d.profile?.dietary_preferences || []).join(', ') })
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleProfileSave = async (e) => {
    e.preventDefault(); setSaving(true)
    try {
      const payload = { ...form, age: form.age ? parseInt(form.age) : null, weight: form.weight ? parseFloat(form.weight) : null, height: form.height ? parseFloat(form.height) : null }
      await api.post('/profile/update', payload)
      await fetchUser()
      alert('Profile updated successfully!')
    } catch {} finally { setSaving(false) }
  }

  const handleMedicalSave = async (e) => {
    e.preventDefault(); setSaving(true)
    try {
      await api.post('/profile/medical', { medical_conditions: medForm.medical_conditions.split(',').map(s => s.trim()).filter(Boolean), dietary_preferences: medForm.dietary_preferences.split(',').map(s => s.trim()).filter(Boolean) })
      alert('Medical info updated!')
    } catch {} finally { setSaving(false) }
  }

  const handleAddAllergy = async (e) => {
    e.preventDefault()
    if (!allergyForm.allergen_name.trim()) return
    try {
      const res = await api.post('/profile/allergy', allergyForm)
      setAllergies(prev => [...prev, res.data.allergy])
      setAllergyForm({ allergen_name: '', severity: 'moderate', notes: '' })
      await fetchUser()
    } catch (err) { alert(err.response?.data?.error || 'Failed to add allergy') }
  }

  const handleDeleteAllergy = async (id) => {
    try {
      await api.delete(`/profile/allergy/${id}`)
      setAllergies(prev => prev.filter(a => a.id !== id))
      await fetchUser()
    } catch {}
  }

  if (loading) return <><Navbar /><main style={{ paddingTop: '76px' }}><LoadingSpinner /></main></>

  return (
    <>
      <Navbar />
      <main style={{ paddingTop: '76px' }}>
        <div className="container py-4 page-content">
          <div className="mb-4"><h3 className="fw-bold"><i className="fas fa-user-edit text-primary-green me-2"></i>My Profile</h3><p className="text-muted">Manage your personal and medical information</p></div>

          <div className="row g-4">
            {/* Left Column */}
            <div className="col-lg-6">
              <div className="profile-section">
                <h5 className="fw-bold mb-3"><i className="fas fa-user text-primary-green me-2"></i>Personal Information</h5>
                <form onSubmit={handleProfileSave}>
                  <div className="row g-3">
                    <div className="col-12"><label className="form-label-nutriai">Full Name</label><input className="form-control form-control-nutriai" value={form.full_name || ''} onChange={e => setForm({ ...form, full_name: e.target.value })} required /></div>
                    <div className="col-md-4"><label className="form-label-nutriai">Age</label><input type="number" className="form-control form-control-nutriai" value={form.age} onChange={e => setForm({ ...form, age: e.target.value })} /></div>
                    <div className="col-md-4"><label className="form-label-nutriai">Gender</label><select className="form-control form-control-nutriai" value={form.gender} onChange={e => setForm({ ...form, gender: e.target.value })}><option value="">Select</option><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option></select></div>
                    <div className="col-md-4"><label className="form-label-nutriai">Blood Type</label><select className="form-control form-control-nutriai" value={form.blood_type} onChange={e => setForm({ ...form, blood_type: e.target.value })}><option value="">Select</option>{['A+','A-','B+','B-','O+','O-','AB+','AB-'].map(bt => <option key={bt} value={bt}>{bt}</option>)}</select></div>
                    <div className="col-md-6"><label className="form-label-nutriai">Weight (kg)</label><input type="number" step="0.1" className="form-control form-control-nutriai" value={form.weight} onChange={e => setForm({ ...form, weight: e.target.value })} /></div>
                    <div className="col-md-6"><label className="form-label-nutriai">Height (cm)</label><input type="number" step="0.1" className="form-control form-control-nutriai" value={form.height} onChange={e => setForm({ ...form, height: e.target.value })} /></div>
                    <div className="col-12"><label className="form-label-nutriai">Emergency Contact</label><input className="form-control form-control-nutriai" value={form.emergency_contact} onChange={e => setForm({ ...form, emergency_contact: e.target.value })} /></div>
                  </div>
                  <button type="submit" className="btn btn-nutriai-primary w-100 mt-3" disabled={saving}><i className="fas fa-save me-2"></i>Save Changes</button>
                </form>
              </div>

              <div className="profile-section">
                <h5 className="fw-bold mb-3"><i className="fas fa-notes-medical text-secondary-blue me-2"></i>Medical Information</h5>
                <form onSubmit={handleMedicalSave}>
                  <div className="mb-3"><label className="form-label-nutriai">Medical Conditions (comma separated)</label><input className="form-control form-control-nutriai" placeholder="e.g., Type 2 Diabetes, Hypertension" value={medForm.medical_conditions} onChange={e => setMedForm({ ...medForm, medical_conditions: e.target.value })} /></div>
                  <div className="mb-3"><label className="form-label-nutriai">Dietary Preferences (comma separated)</label><input className="form-control form-control-nutriai" placeholder="e.g., Vegetarian, Low-sodium" value={medForm.dietary_preferences} onChange={e => setMedForm({ ...medForm, dietary_preferences: e.target.value })} /></div>
                  <button type="submit" className="btn btn-nutriai-secondary w-100" disabled={saving}><i className="fas fa-save me-2"></i>Update Medical Info</button>
                </form>
              </div>
            </div>

            {/* Right Column - Allergies */}
            <div className="col-lg-6">
              <div className="profile-section">
                <h5 className="fw-bold mb-3"><i className="fas fa-allergies text-danger me-2"></i>Food Allergies</h5>
                <div className="d-flex flex-wrap gap-2 mb-3">
                  {allergies.length > 0 ? allergies.map(a => (
                    <span key={a.id} className={`allergy-badge ${a.severity}`}>
                      {a.allergen_name}
                      <span className="delete-allergy" onClick={() => handleDeleteAllergy(a.id)}><i className="fas fa-times"></i></span>
                    </span>
                  )) : <p className="text-muted">No food allergies recorded.</p>}
                </div>

                <h6 className="fw-600 mt-4 mb-3">Add New Allergy</h6>
                <form onSubmit={handleAddAllergy}>
                  <div className="row g-3">
                    <div className="col-md-5"><input className="form-control form-control-nutriai" placeholder="Allergen name (e.g., Peanuts)" value={allergyForm.allergen_name} onChange={e => setAllergyForm({ ...allergyForm, allergen_name: e.target.value })} required /></div>
                    <div className="col-md-3"><select className="form-control form-control-nutriai" value={allergyForm.severity} onChange={e => setAllergyForm({ ...allergyForm, severity: e.target.value })}><option value="mild">Mild</option><option value="moderate">Moderate</option><option value="severe">Severe</option></select></div>
                    <div className="col-md-4"><button type="submit" className="btn btn-nutriai-primary w-100"><i className="fas fa-plus me-1"></i>Add</button></div>
                  </div>
                  <div className="mt-2"><input className="form-control form-control-nutriai" placeholder="Notes (optional)" value={allergyForm.notes} onChange={e => setAllergyForm({ ...allergyForm, notes: e.target.value })} /></div>
                </form>
              </div>

              <div className="profile-section">
                <h5 className="fw-bold mb-3"><i className="fas fa-info-circle text-primary-green me-2"></i>Account Info</h5>
                <div className="row g-2">
                  <div className="col-6"><small className="text-muted">Email</small><p className="fw-600 mb-2">{authUser?.email}</p></div>
                  <div className="col-6"><small className="text-muted">Username</small><p className="fw-600 mb-2">{authUser?.username}</p></div>
                  <div className="col-6"><small className="text-muted">Auth Type</small><p className="fw-600 mb-2">{authUser?.auth_type === 'entra_id' ? 'Microsoft SSO' : 'Local'}</p></div>
                  <div className="col-6"><small className="text-muted">Member Since</small><p className="fw-600 mb-0">{authUser?.created_at ? new Date(authUser.created_at).toLocaleDateString() : '-'}</p></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
