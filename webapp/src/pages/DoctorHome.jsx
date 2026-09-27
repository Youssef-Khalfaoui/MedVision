import { useRef, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { animate, createScope } from 'animejs'
import { searchPatients } from '../api/patients'
import {
  Root,
  MaxWide5,
  Card,
  CardTitle,
  Title,
  SubTitle,
  SectionTitle,
  Input,
  BtnGhost,
  BtnPrimary,
  FlexBetween,
  Spinner,
  Panel,
} from '../styled'
import { tokens } from '../theme'

const fieldStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  flex: 1,
  minWidth: 0,
}

const labelStyle = {
  fontSize: 11,
  fontWeight: 600,
  color: tokens.slate400,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
}

export default function DoctorHome({ onLogout }) {
  const rootRef = useRef(null)
  const navigate = useNavigate()
  const [patients, setPatients] = useState([])
  const [nameVal, setNameVal] = useState('')
  const [idVal, setIdVal] = useState('')
  const [ageVal, setAgeVal] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!rootRef.current) return
    const scope = createScope({ root: rootRef.current })
    animate('.dh-header', { opacity: [0, 1], translateY: [16, 0], duration: 500, ease: 'out(3)' })
    animate('.dh-card', { opacity: [0, 1], translateY: [12, 0], duration: 450, ease: 'out(2)' }, '-=300')
    animate('.dh-list', { opacity: [0, 1], translateY: [8, 0], duration: 400, ease: 'out(2)' }, '-=200')
    return () => scope.revert()
  }, [])

  useEffect(() => {
    setLoading(true)
    setError('')
    searchPatients({ name: nameVal, patientId: idVal, age: ageVal })
      .then((list) => {
        setPatients(Array.isArray(list) ? list : [])
      })
      .catch((err) => setError(err?.message || 'Erreur de chargement'))
      .finally(() => setLoading(false))
  }, [nameVal, idVal, ageVal])

  const handleSelectPatient = (id) => {
    navigate(`/patients/${encodeURIComponent(id)}`)
  }

  const hasFilter = nameVal || idVal || ageVal

  return (
    <Root ref={rootRef}>
      <MaxWide5>
        <FlexBetween className="dh-header" style={{ marginBottom: 16 }}>
          <div>
            <CardTitle>Accueil médecin</CardTitle>
            <SubTitle style={{ marginTop: 4 }}>
              Patients et consultations
            </SubTitle>
          </div>
        </FlexBetween>

        <Card className="dh-card" style={{ marginBottom: 24 }}>
          <FlexBetween style={{ marginBottom: 8 }}>
            <SectionTitle style={{ margin: 0 }}>Rechercher un patient</SectionTitle>
            <BtnPrimary
              type="button"
              onClick={() => navigate('/add-patient')}
              style={{ fontSize: 13, padding: '6px 16px' }}
            >
              + Nouveau patient
            </BtnPrimary>
          </FlexBetween>

          <div
            style={{
              display: 'flex',
              gap: 12,
              marginTop: 8,
              flexWrap: 'wrap',
            }}
          >
            <div style={fieldStyle}>
              <label style={labelStyle}>ID</label>
              <Input
                value={idVal}
                onChange={(e) => setIdVal(e.target.value)}
                placeholder="Identifiant…"
              />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Nom</label>
              <Input
                value={nameVal}
                onChange={(e) => setNameVal(e.target.value)}
                placeholder="Nom du patient…"
              />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Âge</label>
              <Input
                value={ageVal}
                onChange={(e) => setAgeVal(e.target.value)}
                placeholder="Âge en années…"
                type="number"
                min="0"
              />
            </div>
          </div>
        </Card>

        <Card className="dh-list">
          <FlexBetween style={{ marginBottom: 16 }}>
            <Title style={{ fontSize: '1.125rem' }}>
              Patients récents
              {!loading && (
                <span style={{ fontWeight: 400, color: '#94a3b8', marginLeft: 8, fontSize: 14 }}>
                  ({patients.length} affiché{patients.length > 1 ? 's' : ''})
                </span>
              )}
            </Title>
            {hasFilter && patients.length > 0 && (
              <SubTitle style={{ fontSize: 12 }}>
                Filtre actif
              </SubTitle>
            )}
          </FlexBetween>

          {loading && <Spinner>Chargement des patients…</Spinner>}

          {error && (
            <p style={{ color: '#f87171', fontSize: 14, margin: 0 }}>{error}</p>
          )}

          {!loading && !error && patients.length === 0 && (
            <p style={{ color: '#94a3b8', fontSize: 14, margin: 0, textAlign: 'center', padding: '2rem 0' }}>
              {hasFilter ? 'Aucun patient trouvé.' : 'Aucun patient enregistré.'}
            </p>
          )}

          {!loading && patients.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {patients.map((p, i) => (
                <PatientRow
                  key={p.id}
                  patient={p}
                  index={i}
                  onClick={() => handleSelectPatient(p.id)}
                />
              ))}
            </div>
          )}
        </Card>
      </MaxWide5>
    </Root>
  )
}

function PatientRow({ patient, index, onClick }) {
  const rowRef = useRef(null)

  useEffect(() => {
    if (!rowRef.current) return
    const scope = createScope({ root: rowRef.current })
    animate('.pr-inner', {
      opacity: [0, 1],
      translateX: [-8, 0],
      duration: 350,
      delay: index * 30,
      ease: 'out(2)',
    })
    return () => scope.revert()
  }, [index])

  const created = patient.created_at
    ? new Date(patient.created_at).toLocaleDateString('fr-FR', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
    : ''

  return (
    <div ref={rowRef}>
      <Panel
        className="pr-inner"
        style={{
          padding: '12px 16px',
          cursor: 'pointer',
          transition: 'background 0.15s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
        }}
        onClick={onClick}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(30, 41, 59, 0.8)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = '')}
      >
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>
            {patient.full_name || '(sans nom)'}
          </div>
          <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
            <span style={{ fontFamily: 'monospace' }}>{patient.id}</span>
            {patient.date_of_birth && (
              <>
                <span style={{ margin: '0 6px', color: '#475569' }}>·</span>
                {patient.date_of_birth}
              </>
            )}
            {patient.sex && (
              <>
                <span style={{ margin: '0 6px', color: '#475569' }}>·</span>
                {patient.sex}
              </>
            )}
          </div>
        </div>
        <div style={{ fontSize: 12, color: '#64748b', whiteSpace: 'nowrap', textAlign: 'right' }}>
          {created && <div>{created}</div>}
          <div style={{ fontSize: 16, color: '#475569', marginTop: 2 }}>→</div>
        </div>
      </Panel>
    </div>
  )
}
