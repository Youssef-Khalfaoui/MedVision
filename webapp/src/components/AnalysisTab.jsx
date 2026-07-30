import { useRef, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { animate, createScope } from 'animejs'
import { uploadExam, getExam, checkDuplicate } from '../api/exams'
import ExamResult from './ExamResult'
import {
  Panel,
  SectionTitle,
  DropZone,
  BtnPrimary,
  ProgressTrack,
  ProgressFill,
  AmberBoxInner,
} from '../styled'

const STAGES = ['PENDING', 'CLASSIFYING', 'COMPARING', 'GENERATING', 'VALIDATING', 'DONE']
const STAGE_LABELS = {
  PENDING: 'En attente',
  CLASSIFYING: 'Classification (Agent 1)',
  COMPARING: 'Comparaison historique (Agent 1.5)',
  GENERATING: 'Génération rapport (Agent 2)',
  VALIDATING: 'Validation (Agent 3)',
  DONE: 'Terminé',
  FAILED: 'Échec',
  REJECTED: 'Image rejetée',
}

const REJECTED_MSG =
  "Image rejetée : ce fichier ne semble pas être une radiographie thoracique valide."

export default function AnalysisTab({ patientId, onAnalysisDone, onOpenExisting, onBusyChange }) {
  const rootRef = useRef(null)
  const scopeRef = useRef(null)
  const wsRef = useRef(null)
  const navigate = useNavigate()
  const pollRef = useRef(null)

  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [dupWarning, setDupWarning] = useState(null)

  const [examId, setExamId] = useState(null)
  const [examenNumber, setExamenNumber] = useState(null)
  const [status, setStatus] = useState(null)
  const [stageIdx, setStageIdx] = useState(-1)
  const [wsLog, setWsLog] = useState([])
  const [result, setResult] = useState(null)

  const onDrop = useCallback((accepted) => {
    if (accepted && accepted.length > 0) {
      const f = accepted[0]
      setFile(f)
      setPreview(URL.createObjectURL(f))
      setUploadError(null)
    }
  }, [])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/png': ['.png'], 'image/jpeg': ['.jpg', '.jpeg'] },
    multiple: false,
  })

  useEffect(() => {
    if (!rootRef.current) return
    const scope = createScope({ root: rootRef.current })
    scopeRef.current = scope
    animate('.an-root', { opacity: [0, 1], translateY: [12, 0], duration: 400, ease: 'out(3)' })
    return () => scope.revert()
  }, [])

  useEffect(() => {
    if (onBusyChange) onBusyChange(busy)
  }, [busy, onBusyChange])

  useEffect(() => {
    if (stageIdx < 0) return
    const pct = ((stageIdx + 1) / STAGES.length) * 100
    animate('.an-progress-fill', {
      width: [`${Math.max(0, stageIdx) * 20}%`, `${pct}%`],
      duration: 500,
      ease: 'out(2)',
    })
  }, [stageIdx])

  async function launch() {
    if (!file) return
    if (busy || uploading) return

    setDupWarning(null)
    try {
      const buf = await file.arrayBuffer()
      const digest = await crypto.subtle.digest('SHA-256', buf)
      const hash = Array.from(new Uint8Array(digest))
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('')
      const dup = await checkDuplicate(patientId, hash)
      if (dup && dup.duplicate) {
        setDupWarning({ examId: dup.exam_id, examenNumber: dup.examen_number, patientId: dup.patient_id, status: dup.status })
        return
      }
    } catch {
    }

    setBusy(true)
    setUploading(true)
    setUploadError(null)
    setResult(null)
    setStatus(null)
    setStageIdx(-1)
    setWsLog([])
    try {
      const res = await uploadExam(patientId, file)
      const id = res.exam_id
      setExamId(id)
      setExamenNumber(res.examen_number ?? null)
      setStatus(res.status)
      startPolling(id)
      connectProgress(id)
    } catch (e) {
      setUploadError(e.message || 'Échec de l’upload')
      setBusy(false)
    } finally {
      setUploading(false)
    }
  }

  function startPolling(id) {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const data = await getExam(id)
        if (data.status === 'DONE' || data.status === 'FAILED' || data.status === 'REJECTED') {
          setStatus(data.status)
          const idx = STAGES.indexOf(data.status)
          if (idx >= 0) setStageIdx(idx)
          stopPolling()
          setBusy(false)
          if (data.status === 'DONE') loadResult(id)
          else if (data.status === 'REJECTED') setUploadError(REJECTED_MSG)
          else setUploadError(data.error_message || 'Pipeline en échec')
        } else {
          setStatus(data.status)
          const idx = STAGES.indexOf(data.status)
          if (idx >= 0) setStageIdx(idx)
        }
      } catch (e) {
        if (e && e.status === 404) {
          // Exam no longer exists: Agent 0 rejected it and it was removed
          // rather than kept as a FAILED record.
          stopPolling()
          setBusy(false)
          setStatus('REJECTED')
          setUploadError(REJECTED_MSG)
        }
      }
    }, 2000)
  }
  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  function connectProgress(id) {
    const url = `/api/exams/${id}/progress?token=${encodeURIComponent(localStorage.getItem('mv_token') || '')}`
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}${url}`)
    wsRef.current = ws
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        setWsLog((l) => [...l, msg])
        const st = msg.status || msg.STATUS
        if (!st) return
        setStatus(st)
        const idx = STAGES.indexOf(st)
        if (idx >= 0) setStageIdx(idx)
        if (st === 'DONE') {
          stopPolling()
          setBusy(false)
          loadResult(id)
        } else if (st === 'FAILED' || st === 'REJECTED') {
          stopPolling()
          setBusy(false)
          setUploadError(msg.error || (st === 'REJECTED' ? REJECTED_MSG : 'Pipeline en échec'))
        }
      } catch {
      }
    }
    ws.onerror = () => {
      setUploadError('Connexion WebSocket interrompue — bascule sur interrogation')
    }
  }

  async function loadResult(id) {
    try {
      const data = await getExam(id)
      setResult(data)
      setBusy(false)
      stopPolling()
      onAnalysisDone?.(id)
    } catch (e) {
      setUploadError(e.message || 'Échec du chargement du résultat')
      setBusy(false)
    }
  }

  useEffect(
    () => () => {
      if (wsRef.current) wsRef.current.close()
      stopPolling()
    },
    [],
  )

  return (
    <div ref={rootRef} className="an-root" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Panel>
        <SectionTitle>Nouvelle analyse</SectionTitle>
        <DropZone {...getRootProps()} $active={isDragActive}>
          <input {...getInputProps()} />
          {preview ? (
            <img src={preview} alt="aperçu" style={{ maxHeight: 192, borderRadius: 8, boxShadow: '0 10px 15px rgba(0,0,0,0.4)' }} />
          ) : (
            <p style={{ fontSize: 14, color: '#94a3b8' }}>
              Glissej une radio (PNG/JPEG) ici, ou cliquez pour parcourir.
            </p>
          )}
        </DropZone>
        {file && (
          <p style={{ marginTop: 8, fontSize: 14, color: '#cbd5e1' }}>
            Fichier sélectionné : <span style={{ fontWeight: 500 }}>{file.name}</span>
          </p>
        )}
        <BtnPrimary
          type="button"
          onClick={launch}
          disabled={!file || uploading || busy}
          style={{ marginTop: 16 }}
        >
          {uploading ? 'Envoi…' : busy ? 'Analyse en cours…' : 'Lancer l’analyse'}
        </BtnPrimary>
        {uploadError && <p style={{ marginTop: 8, fontSize: 14, color: '#f87171' }}>{uploadError}</p>}
        {dupWarning && (
          <AmberBoxInner>
            <p style={{ fontWeight: 600, margin: 0 }}>Image déjà analysée</p>
            <p style={{ marginTop: 4, margin: 0 }}>
              Cette radio correspond à l'examen <span style={{ fontFamily: 'monospace' }}>#{dupWarning.examenNumber ?? dupWarning.examId}</span> du
              dossier <span style={{ fontFamily: 'monospace' }}>{dupWarning.patientId}</span> (statut : {dupWarning.status}).
              L'analyse n'a pas été relancée.
            </p>
            <button
              type="button"
              onClick={() => {
                if (onOpenExisting) onOpenExisting(dupWarning.examId)
                else navigate(`/patients/${dupWarning.patientId}`)
              }}
              style={{ marginTop: 8, borderRadius: 8, background: 'rgba(245,158,11,0.2)', border: 'none', padding: '4px 12px', fontSize: 12, fontWeight: 500, color: '#fde68a', cursor: 'pointer' }}
            >
              Ouvrir le dossier {dupWarning.patientId}
            </button>
          </AmberBoxInner>
        )}
      </Panel>

      {status && (
        <Panel>
          <SectionTitle>Progression du pipeline</SectionTitle>
          <ProgressTrack>
            <ProgressFill className="an-progress-fill" style={{ width: '0%' }} />
          </ProgressTrack>
          <p style={{ marginTop: 8, fontSize: 14, color: '#cbd5e1' }}>
            {status === 'FAILED' ? STAGE_LABELS.FAILED : STAGE_LABELS[status] || status}
            {examId != null && ` (Examen #${examenNumber ?? examId})`}
          </p>
          {wsLog.length > 0 && (
            <ul style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12, color: '#64748b', listStyle: 'none', padding: 0 }}>
              {wsLog.map((m, i) => (
                <li key={i}>{m.status || JSON.stringify(m)}</li>
              ))}
            </ul>
          )}
        </Panel>
      )}

      {result && status === 'DONE' && (
        <section style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <ExamResult exam={result} />
        </section>
      )}
    </div>
  )
}
