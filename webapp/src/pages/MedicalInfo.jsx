import { useRef, useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { animate, createScope } from 'animejs'
import { getMedicalHistory, upsertMedicalHistory } from '../api/patients'
import {
  Root,
  MaxWide,
  FlexBetween,
  CardTitle,
  Card,
  FieldSet,
  Legend,
  Grid2,
  CheckLabel,
  CheckBox,
  FieldLabel,
  Select,
  Input,
  TextArea,
  ErrorBox,
  BtnPrimary,
  BtnGhost,
  BtnRow,
} from '../styled'

const GROUPS = [
  {
    title: 'Medical History',
    fields: [
      { key: 'previous_operations', label: 'Previous Operations' },
      { key: 'prior_pneumonia', label: 'Previous Pneumonia' },
      { key: 'copd', label: 'COPD' },
      { key: 'asthma', label: 'Asthma' },
      { key: 'heart_disease', label: 'Heart Disease' },
      { key: 'heart_failure', label: 'Heart Failure' },
      { key: 'hypertension', label: 'Hypertension' },
      { key: 'diabetes', label: 'Diabetes' },
      { key: 'allergies', label: 'Allergies' },
    ],
  },
  {
    title: 'Current Status',
    fields: [
      { key: 'current_symptoms', label: 'Current Symptoms' },
      { key: 'current_medication', label: 'Current Medication' },
    ],
  },
]

const BOOL_KEYS = GROUPS.flatMap((g) => g.fields.map((f) => f.key))

export default function MedicalInfo({ onLogout }) {
  const rootRef = useRef(null)
  const scopeRef = useRef(null)
  const [params] = useSearchParams()
  const patientId = params.get('id') || ''
  const navigate = useNavigate()

  const [checks, setChecks] = useState(Object.fromEntries(BOOL_KEYS.map((k) => [k, false])))
  const [smoking, setSmoking] = useState('')
  const [doctorNotes, setDoctorNotes] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!rootRef.current) return
    const scope = createScope({ root: rootRef.current })
    scopeRef.current = scope
    animate('.mi-card', { opacity: [0, 1], translateY: [20, 0], duration: 550, ease: 'out(3)' })
    return () => scope.revert()
  }, [])

  useEffect(() => {
    if (!patientId) return
    getMedicalHistory(patientId)
      .then((data) => {
        const next = { ...checks }
        for (const k of BOOL_KEYS) next[k] = !!data[k]
        setChecks(next)
        setSmoking(data.smoking_status || '')
        setDoctorNotes(data.doctor_notes || '')
        setPhone(data.phone || '')
      })
      .catch(() => {})
  }, [patientId])

  function toggle(key) {
    setChecks((c) => ({ ...c, [key]: !c[key] }))
  }

  async function handleSave(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const body = {
        ...Object.fromEntries(BOOL_KEYS.map((k) => [k, !!checks[k]])),
        smoking_status: smoking || null,
        doctor_notes: doctorNotes.trim() || null,
        phone: phone.trim() || null,
      }
      await upsertMedicalHistory(patientId, body)
      animate('.mi-root', { opacity: [1, 0], duration: 350, ease: 'in(2)' })
      navigate(`/patients/${encodeURIComponent(patientId)}`)
    } catch (err) {
      setError(err?.message || 'Erreur lors de l’enregistrement')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Root ref={rootRef} className="mi-root">
      <MaxWide>
        <FlexBetween>
          <CardTitle>Informations complémentaires</CardTitle>
          <BtnGhost type="button" onClick={onLogout}>
            Déconnexion
          </BtnGhost>
        </FlexBetween>

        <Card className="mi-card" style={{ marginTop: 8 }}>
          <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {GROUPS.map((group) => (
              <FieldSet key={group.title}>
                <Legend>{group.title}</Legend>
                <Grid2>
                  {group.fields.map((f) => (
                    <CheckLabel key={f.key}>
                      <CheckBox
                        type="checkbox"
                        checked={!!checks[f.key]}
                        onChange={() => toggle(f.key)}
                      />
                      {f.label}
                    </CheckLabel>
                  ))}
                </Grid2>
              </FieldSet>
            ))}

            <FieldSet>
              <Legend>Autres informations</Legend>
              <label style={{ display: 'block', marginBottom: 12 }}>
                <FieldLabel>Tabagisme</FieldLabel>
                <Select value={smoking} onChange={(e) => setSmoking(e.target.value)}>
                  <option value="">—</option>
                  <option value="never">Jamais</option>
                  <option value="former">Ancien</option>
                  <option value="current">Actuel</option>
                </Select>
              </label>
              <label style={{ display: 'block', marginBottom: 12 }}>
                <FieldLabel>Téléphone</FieldLabel>
                <Input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="ex: +33 6 12 34 56 78"
                />
              </label>
              <label style={{ display: 'block' }}>
                <FieldLabel>Notes médecin</FieldLabel>
                <TextArea
                  value={doctorNotes}
                  onChange={(e) => setDoctorNotes(e.target.value)}
                  rows={3}
                  placeholder="Observations cliniques…"
                />
              </label>
            </FieldSet>

            {error && <ErrorBox>{error}</ErrorBox>}

            <BtnRow>
              <BtnPrimary type="submit" disabled={busy} style={{ flex: 1 }}>
                {busy ? '…' : 'Enregistrer'}
              </BtnPrimary>
              <BtnGhost type="button" onClick={() => navigate(`/patients/${encodeURIComponent(patientId)}`)}>
                Ignorer
              </BtnGhost>
            </BtnRow>
          </form>
        </Card>
      </MaxWide>
    </Root>
  )
}
