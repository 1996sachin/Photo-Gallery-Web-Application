import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000' })

api.interceptors.request.use(cfg => {
  const token = useAuthStore.getState().token
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
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
        set({ token: data.access_token, user: data.user })
        return data.user
      },

      register: async (email, password, displayName) => {
        const { data } = await api.post('/api/auth/register', { email, password, display_name: displayName })
        set({ token: data.access_token, user: data.user })
        return data.user
      },

      logout: () => set({ token: null, user: null }),
      setUser: (user) => set({ user }),
    }),
    { name: 'memories-auth', partialize: s => ({ token: s.token, user: s.user }) }
  )
)
