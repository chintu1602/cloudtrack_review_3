import { createContext, useState, useEffect, useCallback } from 'react'
import api from '../api/axios'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [flash, setFlash] = useState(null)

  const showFlash = useCallback((message, type = 'success') => {
    setFlash({ message, type })
    setTimeout(() => setFlash(null), 5000)
  }, [])

  const fetchUser = useCallback(async () => {
    try {
      const res = await api.get('/auth/me')
      setUser(res.data)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password })
    if (res.data.user) {
      setUser(res.data.user)
      await fetchUser()
    }
    return res.data
  }

  const register = async (formData) => {
    const res = await api.post('/auth/register', formData)
    if (res.data.user) {
      setUser(res.data.user)
      await fetchUser()
    }
    return res.data
  }

  const logout = async () => {
    try {
      await api.get('/auth/logout')
    } catch {}
    setUser(null)
  }

  const microsoftLogin = async () => {
    const res = await api.get('/auth/microsoft')
    return res.data.auth_url
  }

  return (
    <AuthContext.Provider value={{
      user, loading, flash, showFlash,
      login, register, logout, microsoftLogin, fetchUser
    }}>
      {children}
    </AuthContext.Provider>
  )
}
