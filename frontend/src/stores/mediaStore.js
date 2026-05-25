import { create } from 'zustand'
import { api } from '../hooks/useAuth'

export const useMediaStore = create((set, get) => ({
  items: [],
  loading: false,
  hasMore: true,
  page: 1,
  filters: { type: 'all', search: '', albumId: null, favoritesOnly: false },

  setFilter: (key, val) => {
    set(s => ({ filters: { ...s.filters, [key]: val }, items: [], page: 1, hasMore: true }))
    get().fetch(true)
  },

  fetch: async (reset = false) => {
    const { filters, page } = get()
    const p = reset ? 1 : page
    set({ loading: true })
    try {
      const { data } = await api.get('/api/media/', {
        params: {
          media_type: filters.type === 'all' ? undefined : filters.type,
          search: filters.search || undefined,
          album_id: filters.albumId || undefined,
          favorites_only: filters.favoritesOnly || undefined,
          page: p, per_page: 30,
        }
      })
      set(s => ({
        items: reset ? data : [...s.items, ...data],
        hasMore: data.length === 30,
        page: p + 1,
        loading: false,
      }))
    } catch { set({ loading: false }) }
  },

  updateItem: (id, patch) =>
    set(s => ({ items: s.items.map(i => i.id === id ? { ...i, ...patch } : i) })),

  removeItem: (id) =>
    set(s => ({ items: s.items.filter(i => i.id !== id) })),

  reset: () => set({ items: [], page: 1, hasMore: true }),
}))
