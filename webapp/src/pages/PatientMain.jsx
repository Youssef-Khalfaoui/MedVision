import { useRef, useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { animate, createScope, createTimeline } from 'animejs'
import HistoryTab from '../components/HistoryTab'
import AnalysisTab from '../components/AnalysisTab'
import PatientDetail from './PatientDetail'
import { getPatient, updatePatient, deletePatient } from '../api/patients'
import { Root, HeaderBar, Title, SubTitle, Nav, BtnGhost, MaxWide5, Panel, BtnPrimary, SectionTitle } from '../styled'

export default function PatientMain({ onLogout }) {
  const { patientId } = useParams()
  const navigate = useNavigate()
  const rootRef = useRef(null)
  const scopeRef = useRef(null)
  const [tab, setTab] = useState('history')
  const [historyVersion, setHistoryVersion] = useState(0)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [patientName, setPatientName] = useState('')
  const [editOpen, setEditOpen] = useState(false)
  const [delOpen, setDelOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [form, setForm] = useState({ full_name: '', date_of_birth: '', sex: '' })
  const [confirmText, setConfirmText] = useState('')
  const [errMsg, setErrMsg] = useState('')

  useEffect(() => {
    getPatient(patientId)
      .then((p) => {
        setPatientName(p.full_name || '')
        setForm({
          full_name: p.full_name || '',
          date_of_birth: p.date_of_birth ? String(p.date_of_birth).slice(0, 10) : '',
          sex: p.sex || '',
        })
      })
      .catch(() => setPatientName(''))
  }, [patientId])

  useEffect(() => {
    if (!rootRef.current) return
    const scope = createScope({ root: rootRef.current })
    scopeRef.current = scope
    const tl = createTimeline()
    tl.add('.pm-header', { opacity: [0, 1], translateY: [16, 0], duration: 450, ease: 'out(3)' })
      .add('.pm-content', { opacity: [0, 1], translateY: [12, 0], duration: 400, ease: 'out(2)' }, '-=200')
    return () => scope.revert()
  }, [])

  useEffect(() => {
    const scope = scopeRef.current
    if (!scope) return
    animate('.pm-content', {
      opacity: [0, 1],
      translateX: [tab === 'history' ? -16 : 16, 0],
      duration: 350,
      ease: 'out(2)',
    })
  }, [tab])

  function handleAnalysisDone() {
    setHistoryVersion((v) => v + 1)
  }

  function handleOpenExisting(examId) {
    setHistoryVersion((v) => v + 1)
    setTab('history')
  }

  async function handleSaveEdit() {
    setErrMsg('')
    if (!form.full_name.trim()) {
      setErrMsg('Le nom complet est obligatoire.')
      return
    }
    setSaving(true)
    try {
      const res = await updatePatient(patientId, {
        full_name: form.full_name.trim(),
        date_of_birth: form.date_of_birth || null,
        sex: form.sex || null,
      })
      setPatientName(res.full_name || form.full_name)
      setEditOpen(false)
    } catch (e) {
      setErrMsg(e?.message || 'Échec de la modification.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    setErrMsg('')
    setDeleting(true)
    try {
      await deletePatient(patientId)
      navigate('/doctor-home')
    } catch (e) {
      setErrMsg(e?.message || 'Échec de la suppression.')
      setDeleting(false)
      setDelOpen(false)
    }
  }

  return (
    <Root ref={rootRef} className="pm-root" style={{ padding: 0 }}>
      <HeaderBar className="pm-header" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 0, padding: '12px 24px 0', borderBottom: 'none' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minHeight: 100, position: 'relative', paddingLeft: 160 }}>
          <img src="/logo-icon.svg" alt="MedVision" style={{ position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)', height: 140, width: 140, objectFit: 'contain', flexShrink: 0 }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <Title>
              Patient {patientId}
              {patientName && (
                <span style={{ fontWeight: 400, color: '#cbd5e1', marginLeft: 8 }}>— {patientName}</span>
              )}
            </Title>
            <SubTitle>Dossier radiologique</SubTitle>
          </div>
          <BtnGhost type="button" data-testid="btn-back-search" onClick={() => navigate('/doctor-home')} style={{ flexShrink: 0 }}>
            ← Accueil
          </BtnGhost>
          <BtnGhost type="button" data-testid="btn-edit-patient" onClick={() => setEditOpen(true)} style={{ flexShrink: 0 }}>
            Modifier
          </BtnGhost>
          <BtnGhost
            type="button"
            data-testid="btn-delete-patient"
            onClick={() => { setConfirmText(''); setErrMsg(''); setDelOpen(true) }}
            style={{ flexShrink: 0, color: '#f87171', borderColor: 'rgba(248,113,113,0.4)' }}
          >
            Supprimer le dossier
          </BtnGhost>
          <BtnGhost type="button" onClick={onLogout} style={{ flexShrink: 0 }}>
            Déconnexion
          </BtnGhost>
        </div>
        <Nav style={{ marginTop: 8, paddingTop: 12, paddingBottom: 0, borderTop: '1px solid rgba(148,163,184,0.15)', justifyContent: 'flex-end' }}>
          <TabButton active={tab === 'history'} onClick={() => setTab('history')} label="Historique" disabled={isAnalyzing} />
          <TabButton active={tab === 'analysis'} onClick={() => setTab('analysis')} label="Analyse" />
          <TabButton active={tab === 'detail'} onClick={() => setTab('detail')} label="Détail patient" disabled={isAnalyzing} />
        </Nav>
      </HeaderBar>

      <MaxWide5 className="pm-content">
        {tab === 'history' ? (
          <HistoryTab key={historyVersion} patientId={patientId} />
        ) : tab === 'analysis' ? (
          <AnalysisTab patientId={patientId} onAnalysisDone={handleAnalysisDone} onOpenExisting={handleOpenExisting} onBusyChange={setIsAnalyzing} />
        ) : (
          <PatientDetail patientId={patientId} />
        )}
      </MaxWide5>

      {editOpen && (
        <Overlay onClick={() => setEditOpen(false)}>
          <Panel
            onClick={(e) => e.stopPropagation()}
            data-testid="edit-patient-dialog"
            style={{ maxWidth: 460, width: '100%', padding: 24 }}
            className="edit-patient-dialog"
          >
            <SectionTitle>Modifier le patient</SectionTitle>
            <p style={{ marginTop: 4, fontSize: 13, color: '#94a3b8' }}>
              Dossier <span style={{ fontFamily: 'monospace' }}>{patientId}</span>
            </p>
            <label style={labelStyle}>Nom complet *</label>
            <InputStyle
              type="text"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              placeholder="Nom et prénom"
            />
            <label style={labelStyle}>Date de naissance</label>
            <InputStyle
              type="date"
              value={form.date_of_birth}
              onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
            />
            <label style={labelStyle}>Sexe</label>
            <SelectStyle value={form.sex} onChange={(e) => setForm({ ...form, sex: e.target.value })}>
              <option value="">—</option>
              <option value="M">M</option>
              <option value="F">F</option>
              <option value="other">other</option>
            </SelectStyle>
            {errMsg && <p style={{ color: '#f87171', fontSize: 13, marginTop: 8 }}>{errMsg}</p>}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <BtnGhost type="button" onClick={() => setEditOpen(false)}>Annuler</BtnGhost>
              <BtnPrimary type="button" onClick={handleSaveEdit} disabled={saving}>
                {saving ? 'Enregistrement…' : 'Enregistrer'}
              </BtnPrimary>
            </div>
          </Panel>
        </Overlay>
      )}

      {delOpen && (
        <Overlay onClick={() => setDelOpen(false)}>
          <Panel
            onClick={(e) => e.stopPropagation()}
            data-testid="delete-patient-dialog"
            style={{ maxWidth: 460, width: '100%', padding: 24 }}
            className="delete-patient-dialog"
          >
            <SectionTitle style={{ color: '#f87171' }}>Supprimer le dossier</SectionTitle>
            <p style={{ marginTop: 8, fontSize: 14, color: '#cbd5e1', lineHeight: 1.5 }}>
              Cette action est <strong>irréversible</strong>. Tout le dossier de{' '}
              <span style={{ fontFamily: 'monospace' }}>{patientId}</span>
              {patientName ? ` (${patientName})` : ''} — examens, images, rapports et antécédents —
              sera supprimé définitivement.
            </p>
            <p style={{ marginTop: 8, fontSize: 13, color: '#94a3b8' }}>
              Tapez <span style={{ fontFamily: 'monospace', color: '#f87171' }}>{patientId}</span> pour confirmer.
            </p>
            <InputStyle
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder={patientId}
              style={{ marginTop: 8 }}
            />
            {errMsg && <p style={{ color: '#f87171', fontSize: 13, marginTop: 8 }}>{errMsg}</p>}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <BtnGhost type="button" onClick={() => setDelOpen(false)}>Annuler</BtnGhost>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting || confirmText !== patientId}
                style={{
                  borderRadius: 8,
                  border: 'none',
                  padding: '8px 16px',
                  fontSize: 14,
                  fontWeight: 600,
                  color: '#fff',
                  cursor: deleting || confirmText !== patientId ? 'not-allowed' : 'pointer',
                  background: deleting || confirmText !== patientId ? '#7f1d1d' : '#dc2626',
                }}
              >
                {deleting ? 'Suppression…' : 'Supprimer définitivement'}
              </button>
            </div>
          </Panel>
        </Overlay>
      )}
    </Root>
  )
}

const labelStyle = { display: 'block', marginTop: 12, fontSize: 13, color: '#cbd5e1', fontWeight: 500 }
const InputStyle = (props) => (
  <input
    {...props}
    style={{
      marginTop: 4,
      width: '100%',
      padding: '8px 10px',
      borderRadius: 8,
      border: '1px solid rgba(148,163,184,0.25)',
      background: 'rgba(15,23,42,0.6)',
      color: '#fff',
      fontSize: 14,
      outline: 'none',
      ...(props.style || {}),
    }}
  />
)
const SelectStyle = (props) => (
  <select
    {...props}
    style={{
      marginTop: 4,
      width: '100%',
      padding: '8px 10px',
      borderRadius: 8,
      border: '1px solid rgba(148,163,184,0.25)',
      background: 'rgba(15,23,42,0.6)',
      color: '#fff',
      fontSize: 14,
      outline: 'none',
    }}
  />
)
const Overlay = ({ onClick, children }) => (
  <div
    onClick={onClick}
    style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(2,6,23,0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: 16,
    }}
  >
    {children}
  </div>
)

function TabButton({ active, onClick, label, disabled }) {
  return (
    <BtnGhost
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={
        active
          ? { background: '#2563eb', color: '#fff', padding: '6px 16px', opacity: disabled ? 0.6 : 1, cursor: disabled ? 'not-allowed' : 'pointer' }
          : { padding: '6px 16px', opacity: disabled ? 0.6 : 1, cursor: disabled ? 'not-allowed' : 'pointer' }
      }
    >
      {label}
    </BtnGhost>
  )
}
