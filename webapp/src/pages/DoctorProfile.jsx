import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { animate, createScope } from 'animejs'
import { me, updateMe } from '../api/auth'
import {
  Root,
  MaxWide5,
  Card,
  CardTitle,
  Title,
  SubTitle,
  SectionTitle,
  Input,
  TextArea,
  BtnPrimary,
  BtnGhost,
  Spinner,
} from '../styled'
import { tokens } from '../theme'

const labelStyle = {
  display: 'block',
  fontSize: 12,
  fontWeight: 600,
  color: tokens.slate400,
  marginBottom: 6,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
}

const fieldDiv = { display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 0 }

export default function DoctorProfile({ onLogout, onDoctorUpdate }) {
  const rootRef = useRef(null)
  const navigate = useNavigate()
  const [doctor, setDoctor] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [specialty, setSpecialty] = useState('')
  const [dateOfBirth, setDateOfBirth] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState({ type: '', text: '' })

  useEffect(() => {
    if (!rootRef.current) return
    const scope = createScope({ root: rootRef.current })
    animate('.pf-header', { opacity: [0, 1], translateY: [16, 0], duration: 500, ease: 'out(3)' })
    animate('.pf-card', { opacity: [0, 1], translateY: [12, 0], duration: 450, ease: 'out(2)' }, '-=300')
    return () => scope.revert()
  }, [])

  useEffect(() => {
    me()
      .then((d) => {
        setDoctor(d)
        setFullName(d.full_name || '')
        setEmail(d.email || '')
        setSpecialty(d.specialty || '')
        setDateOfBirth(d.date_of_birth ? d.date_of_birth.slice(0, 10) : '')
        setPhone(d.phone || '')
        setAddress(d.address || '')
      })
      .catch(() => navigate('/'))
      .finally(() => setLoading(false))
  }, [navigate])

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setMessage({ type: '', text: '' })
    try {
      const body = {}
      if (fullName !== doctor.full_name) body.full_name = fullName
      if (email !== doctor.email) body.email = email
      if (specialty !== (doctor.specialty || '')) body.specialty = specialty
      if (dateOfBirth !== (doctor.date_of_birth ? doctor.date_of_birth.slice(0, 10) : ''))
        body.date_of_birth = dateOfBirth || null
      if (phone !== (doctor.phone || '')) body.phone = phone
      if (address !== (doctor.address || '')) body.address = address
      if (password) body.password = password
      if (Object.keys(body).length === 0) {
        setMessage({ type: 'info', text: 'Aucune modification.' })
        setSaving(false)
        return
      }
      await updateMe(body)
      if (onDoctorUpdate) onDoctorUpdate()
      setMessage({ type: 'success', text: 'Profil mis à jour.' })
      setPassword('')
    } catch (err) {
      setMessage({ type: 'error', text: err?.message || 'Erreur lors de la mise à jour.' })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <Root>
        <MaxWide5 style={{ paddingTop: 60 }}>
          <Spinner>Chargement du profil…</Spinner>
        </MaxWide5>
      </Root>
    )
  }

  return (
    <Root ref={rootRef}>
      <MaxWide5>
        <div className="pf-header" style={{ marginBottom: 24 }}>
          <CardTitle>Mon profil</CardTitle>
          <SubTitle style={{ marginTop: 4 }}>
            Informations personnelles du médecin
          </SubTitle>
        </div>

        <Card className="pf-card">
          <form onSubmit={handleSave}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div style={{ ...fieldDiv, flex: 2 }}>
                  <label style={labelStyle}>Nom complet</label>
                  <Input
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Dr. …"
                    required
                  />
                </div>
                <div style={fieldDiv}>
                  <label style={labelStyle}>Spécialité</label>
                  <Input
                    value={specialty}
                    onChange={(e) => setSpecialty(e.target.value)}
                    placeholder="Radiologue, …"
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div style={fieldDiv}>
                  <label style={labelStyle}>Email</label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="email@exemple.com"
                    required
                  />
                </div>
                <div style={fieldDiv}>
                  <label style={labelStyle}>Téléphone</label>
                  <Input
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+213 …"
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div style={{ ...fieldDiv, maxWidth: 250 }}>
                  <label style={labelStyle}>Date de naissance</label>
                  <Input
                    type="date"
                    value={dateOfBirth}
                    onChange={(e) => setDateOfBirth(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label style={labelStyle}>Adresse</label>
                <TextArea
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="Adresse du cabinet…"
                  style={{ minHeight: 60, resize: 'vertical' }}
                />
              </div>

              <div>
                <label style={labelStyle}>Nouveau mot de passe</label>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Laisser vide pour ne pas changer"
                />
              </div>

              {message.text && (
                <p
                  style={{
                    fontSize: 13,
                    color:
                      message.type === 'success'
                        ? '#4ade80'
                        : message.type === 'error'
                          ? '#f87171'
                          : tokens.slate400,
                    margin: 0,
                  }}
                >
                  {message.text}
                </p>
              )}

              <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
                <BtnPrimary type="submit" disabled={saving}>
                  {saving ? 'Enregistrement…' : 'Enregistrer'}
                </BtnPrimary>
                <BtnGhost
                  type="button"
                  onClick={() => navigate('/doctor-home')}
                >
                  Retour
                </BtnGhost>
              </div>
            </div>
          </form>
        </Card>
      </MaxWide5>
    </Root>
  )
}
