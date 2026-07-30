import { useRef, useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { animate, createScope } from 'animejs'
import { getExam } from '../api/exams'
import { getPatient } from '../api/patients'
import ExamResult from '../components/ExamResult'
import { Root, HeaderBar, Title, SubTitle, Nav, BtnGhost, MaxWide5, Spinner } from '../styled'

export default function ExamDetail({ onLogout }) {
  const { patientId, examId } = useParams()
  const navigate = useNavigate()
  const rootRef = useRef(null)
  const scopeRef = useRef(null)
  const [exam, setExam] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [patientName, setPatientName] = useState('')

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const data = await getExam(examId)
        if (active) setExam(data)
      } catch (e) {
        if (active) setError(e.message || 'Examen introuvable')
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    getPatient(patientId)
      .then((p) => active && setPatientName(p.full_name || ''))
      .catch(() => {})
    return () => { active = false }
  }, [examId, patientId])

  useEffect(() => {
    if (!rootRef.current) return
    const scope = createScope({ root: rootRef.current })
    scopeRef.current = scope
    animate('.pm-header', { opacity: [0, 1], translateY: [16, 0], duration: 450, ease: 'out(3)' })
    return () => scope.revert()
  }, [])

  function back() {
    navigate(`/patients/${patientId}`)
  }

  return (
    <Root ref={rootRef} className="pm-root" style={{ padding: 0 }}>
      <HeaderBar className="pm-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <img src="/logo-icon.svg" alt="MedVision" style={{ height: 80, width: 80, objectFit: 'contain' }} />
          <div>
            <Title>Examen #{examId}</Title>
            <SubTitle>
              Dossier {patientId}
              {patientName && <span style={{ color: '#cbd5e1', marginLeft: 8 }}>— {patientName}</span>}
            </SubTitle>
          </div>
        </div>
        <Nav>
          <BtnGhost type="button" onClick={back}>
            ← Retour au dossier
          </BtnGhost>
          <BtnGhost type="button" onClick={onLogout} style={{ marginLeft: 8 }}>
            Déconnexion
          </BtnGhost>
        </Nav>
      </HeaderBar>

      <MaxWide5 className="pm-content">
        {loading ? (
          <Spinner>Chargement…</Spinner>
        ) : error ? (
          <p style={{ fontSize: 14, color: '#f87171' }}>{error}</p>
        ) : exam && exam.status === 'DONE' ? (
          <ExamResult exam={exam} />
        ) : exam ? (
          <p style={{ fontSize: 14, color: '#94a3b8' }}>Statut de l'examen : {exam.status}</p>
        ) : null}
      </MaxWide5>
    </Root>
  )
}
