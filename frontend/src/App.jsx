import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './hooks/useAuth'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import GalleryPage from './pages/GalleryPage'
import AlbumsPage from './pages/AlbumsPage'
import FavoritesPage from './pages/FavoritesPage'
import PeoplePage from './pages/PeoplePage'
import MediaViewPage from './pages/MediaViewPage'
import ProfilePage from './pages/ProfilePage'
import VerifyOtpPage from './pages/VerifyOtpPage'

function Guard({ children }) {
  const token = useAuthStore(s => s.token)
  const user = useAuthStore(s => s.user)
  if (!token) return <Navigate to="/login" replace />
  if (user && !user.email_verified) return <Navigate to="/verify-otp" replace />
  return children
}

function VerificationRoute() {
  const token = useAuthStore(s => s.token)
  const user = useAuthStore(s => s.user)
  if (!token) return <Navigate to="/login" replace />
  if (user?.email_verified) return <Navigate to="/" replace />
  return <VerifyOtpPage />
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="bottom-center"
        toastOptions={{
          style: {
            background: '#2c1e0f', color: '#fdf8f0',
            borderRadius: '11px', border: '1px solid rgba(200,150,60,0.3)',
            fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13.5px',
          },
          success: { iconTheme: { primary: '#c8963c', secondary: '#fdf8f0' } },
        }}
      />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/verify-otp" element={<VerificationRoute />} />
        <Route path="/" element={<Guard><Layout /></Guard>}>
          <Route index element={<GalleryPage />} />
          <Route path="albums" element={<AlbumsPage />} />
          <Route path="albums/:id" element={<AlbumsPage />} />
          <Route path="favorites" element={<FavoritesPage />} />
          <Route path="people" element={<PeoplePage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="media/:id" element={<MediaViewPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
