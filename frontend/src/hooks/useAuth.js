import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  withCredentials: true,
})

export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      user: null,

      login: async (email, password) => {
        const form = new FormData()
        form.append('username', email)
        form.append('password', password)
        const { data } = await api.post('/api/auth/token', form)
        if (data.mfa_required) {
          return { mfa_required: true, mfa_token: data.mfa_token }
        }
        set({ token: 'cookie', user: data.user })
        return data.user
      },

      verifyMfa: async (code, mfa_token) => {
        const { data } = await api.post('/api/auth/mfa/verify', { code, mfa_token })
        set({ token: 'cookie', user: data.user })
        return data.user
      },

      register: async (email, password, displayName) => {
        const { data } = await api.post('/api/auth/register', { email, password, display_name: displayName })
        set({ token: 'cookie', user: data.user })
        return data.user
      },

      requestEmailVerification: async () => {
        const { data } = await api.post('/api/auth/me/request-email-verification')
        const refreshed = await api.get('/api/auth/me')
        set({ user: refreshed.data })
        return data
      },

      verifyEmailOtp: async (code) => {
        const { data } = await api.post('/api/auth/me/verify-email-otp', { code })
        set({ user: data })
        return data
      },

      logout: async () => {
        await api.post('/api/auth/logout').catch(() => {})
        set({ token: null, user: null })
      },
      setUser: (user) => set({ user }),
    }),
    { name: 'memories-auth', partialize: s => ({ user: s.user, token: s.user ? 'cookie' : null }) }
  )
)
