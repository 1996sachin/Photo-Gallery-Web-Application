import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { X, Upload, Image, Film, CheckCircle2, AlertCircle, CloudUpload } from 'lucide-react'
import { api } from '../hooks/useAuth'
import { useMediaStore } from '../stores/mediaStore'
import toast from 'react-hot-toast'

const fmtSize = b => b < 1048576 ? (b / 1024).toFixed(1) + ' KB' : (b / 1048576).toFixed(1) + ' MB'

function FileRow({ name, size, type, status, progress }) {
  const isVid = type?.startsWith('video/')
  const statusColor = { done: '#5a9a5a', error: '#c94040', uploading: 'var(--c-gold)', pending: 'var(--c-border-md)' }
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px',
      borderRadius: 9, background: 'var(--c-surface2)', border: '1px solid var(--c-border)',
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 8, flexShrink: 0,
        background: isVid ? 'rgba(100,80,200,0.1)' : 'rgba(200,150,60,0.1)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {isVid ? <Film size={15} color="#8878c8" /> : <Image size={15} color="var(--c-gold)" />}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 3 }}>
          <span style={{ fontSize: 11, color: 'var(--c-brown-lt)' }}>{fmtSize(size)}</span>
          {status === 'uploading' && (
            <div style={{ flex: 1, height: 3, background: 'var(--c-border)', borderRadius: 99 }}>
              <div style={{ height: '100%', width: `${progress}%`, background: 'var(--c-gold)', borderRadius: 99, transition: 'width 0.2s' }} />
            </div>
          )}
        </div>
      </div>
      <div>
        {status === 'done' && <CheckCircle2 size={17} color="#5a9a5a" />}
        {status === 'error' && <AlertCircle size={17} color="#c94040" />}
        {status === 'uploading' && <div className="spinner" style={{ width: 15, height: 15 }} />}
        {status === 'pending' && <div style={{ width: 15, height: 15, borderRadius: '50%', background: 'var(--c-border)' }} />}
      </div>
    </div>
  )
}

export default function UploadModal({ onClose, albumId, onUploaded }) {
  const [files, setFiles] = useState([])   // [{id, file}]
  const [statuses, setStatuses] = useState({})
  const [busy, setBusy] = useState(false)
  const { fetch } = useMediaStore()

  const onDrop = useCallback(accepted => {
    const added = accepted.map(f => ({ id: crypto.randomUUID(), file: f }))
    setFiles(p => [...p, ...added])
    setStatuses(p => { const n = { ...p }; added.forEach(({ id }) => { n[id] = { status: 'pending', progress: 0 } }); return n })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp', '.heic', '.gif'], 'video/*': ['.mp4', '.mov', '.webm', '.avi'] },
  })

  const uploadAll = async () => {
    if (!files.length || busy) return
    setBusy(true)
    for (const { file, id } of files) {
      if (statuses[id]?.status === 'done') continue
      setStatuses(p => ({ ...p, [id]: { status: 'uploading', progress: 0 } }))
      const fd = new FormData()
      fd.append('file', file)
      if (albumId) fd.append('album_id', albumId)
      try {
        await api.post('/api/media/upload', fd, {
          onUploadProgress: e => {
            const pct = Math.round((e.loaded / e.total) * 100)
            setStatuses(p => ({ ...p, [id]: { status: 'uploading', progress: pct } }))
          },
        })
        setStatuses(p => ({ ...p, [id]: { status: 'done', progress: 100 } }))
      } catch {
        setStatuses(p => ({ ...p, [id]: { status: 'error', progress: 0 } }))
      }
    }
    setBusy(false)
    fetch(true)
    onUploaded?.()
    toast.success('Memories uploaded! ✨')
  }

  const allDone = files.length > 0 && files.every(({ id }) => statuses[id]?.status === 'done')

  return (
    <div className="overlay" onClick={e => e.target === e.currentTarget && !busy && onClose()}>
      <div className="card" style={{ width: '96%', maxWidth: 480, padding: 32 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 22 }}>
          <div>
            <h2 style={{ fontFamily: 'var(--serif)', fontSize: 21, fontWeight: 500 }}>Upload Memories</h2>
            <p style={{ fontSize: 12.5, color: 'var(--c-brown-lt)', marginTop: 2 }}>Photos & videos for all your loved ones</p>
          </div>
          <button className="btn btn-icon btn" onClick={onClose} disabled={busy}><X size={16} /></button>
        </div>

        {/* Drop zone */}
        <div {...getRootProps()} style={{
          border: `2px dashed ${isDragActive ? 'var(--c-gold)' : 'var(--c-border-md)'}`,
          borderRadius: 12, padding: '28px 20px', textAlign: 'center', cursor: 'pointer',
          background: isDragActive ? 'var(--c-surface2)' : 'transparent',
          transition: 'all 0.15s', marginBottom: 16,
        }}>
          <input {...getInputProps()} />
          <CloudUpload size={36} style={{ color: isDragActive ? 'var(--c-gold)' : 'var(--c-brown-lt)', margin: '0 auto 10px', display: 'block' }} />
          <div style={{ fontFamily: 'var(--serif)', fontSize: 15.5, color: 'var(--c-brown)', marginBottom: 4 }}>
            {isDragActive ? 'Drop your memories here…' : 'Drag photos & videos here'}
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--c-brown-lt)' }}>
            or click to browse · JPG PNG WEBP HEIC MP4 MOV
          </div>
        </div>

        {/* File list */}
        {files.length > 0 && (
          <div style={{ maxHeight: 260, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 18 }}>
            {files.map(({ file, id }) => (
              <FileRow
                key={id} name={file.name} size={file.size} type={file.type}
                status={statuses[id]?.status || 'pending'}
                progress={statuses[id]?.progress || 0}
              />
            ))}
          </div>
        )}

        <div style={{ display: 'flex', gap: 9, justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost" onClick={onClose} disabled={busy}>Cancel</button>
          {allDone
            ? <button className="btn btn-primary" onClick={onClose}>Done ✓</button>
            : <button className="btn btn-primary" onClick={uploadAll} disabled={busy || !files.length}>
                <Upload size={14} />
                {busy ? 'Uploading…' : files.length > 0 ? `Upload ${files.length} file${files.length > 1 ? 's' : ''}` : 'Select files'}
              </button>
          }
        </div>
      </div>
    </div>
  )
}
