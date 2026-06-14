import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import { Map as MapIcon, Calendar, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../hooks/useAuth'
import L from 'leaflet'

// Fix for default marker icons in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

export default function MapPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    load()
  }, [])

  const load = async () => {
    try {
      const { data } = await api.get('/api/media/', { params: { per_page: 500 } })
      // Filter only items with coordinates
      setItems(data.filter(i => i.latitude && i.longitude))
    } catch { }
    finally { setLoading(false) }
  }

  if (loading) return <div className="empty-state"><div className="spinner" /></div>

  return (
    <div style={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 0 }}>
          <MapIcon size={22} color="var(--c-gold)" /> Memory Map
        </h1>
        <div style={{ fontSize: 13, color: 'var(--c-brown-lt)' }}>
          {items.length} memories with location data
        </div>
      </div>

      <div style={{ flex: 1, borderRadius: 20, overflow: 'hidden', border: '1px solid var(--c-border)', boxShadow: 'var(--shadow-lg)' }}>
        <MapContainer 
          center={[20, 0]} 
          zoom={2} 
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {items.map(item => (
            <Marker key={item.id} position={[item.latitude, item.longitude]}>
              <Popup className="map-popup">
                <div style={{ width: 180 }}>
                  <img 
                    src={item.thumbnail_url} 
                    style={{ width: '100%', borderRadius: 8, marginBottom: 8 }} 
                  />
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: 'var(--c-brown)' }}>
                    {item.title || item.original_filename}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--c-brown-lt)', display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
                    <Calendar size={10} /> {new Date(item.taken_at || item.created_at).toLocaleDateString()}
                  </div>
                  <Link to={`/media/${item.id}`} className="btn btn-primary" style={{ fontSize: 11, padding: '5px 10px', width: '100%', display: 'flex', justifyContent: 'center' }}>
                    View Detail <ArrowRight size={12} style={{ marginLeft: 4 }} />
                  </Link>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}
