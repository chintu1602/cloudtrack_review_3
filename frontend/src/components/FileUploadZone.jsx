import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'

export default function FileUploadZone({ onFileSelect, uploading, progress }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) onFileSelect(acceptedFiles[0])
  }, [onFileSelect])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'image/png': ['.png'], 'image/jpeg': ['.jpg', '.jpeg'] },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
    disabled: uploading,
  })

  return (
    <div {...getRootProps()} className={`upload-zone ${isDragActive ? 'drag-over' : ''}`}>
      <input {...getInputProps()} />
      {uploading ? (
        <div className="text-center">
          <div className="spinner-border text-success mb-2" role="status"><span className="visually-hidden">Uploading...</span></div>
          <p className="mb-1 fw-600">Uploading document...</p>
          {progress > 0 && <div className="progress" style={{ height: '6px', maxWidth: '300px', margin: '0 auto' }}><div className="progress-bar bg-success" style={{ width: `${progress}%` }}></div></div>}
        </div>
      ) : isDragActive ? (
        <div className="text-center">
          <i className="fas fa-cloud-upload-alt mb-3" style={{ fontSize: '3rem', color: 'var(--primary-green)' }}></i>
          <p className="mb-0 fw-600">Drop your file here</p>
        </div>
      ) : (
        <div className="text-center">
          <i className="fas fa-cloud-upload-alt mb-3" style={{ fontSize: '3rem', color: 'var(--primary-green)' }}></i>
          <p className="mb-1 fw-600">Drag & drop your document here</p>
          <p className="text-muted mb-2" style={{ fontSize: '0.88rem' }}>or click to browse files</p>
          <small className="text-muted">Supported formats: PDF, PNG, JPG | Max size: 10MB</small>
        </div>
      )}
    </div>
  )
}
