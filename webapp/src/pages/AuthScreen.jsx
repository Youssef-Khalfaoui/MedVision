import { useRef, useState, useEffect } from 'react'
import { animate, createScope } from 'animejs'
import { register, login } from '../api/auth'
import {
  RootCentered,
  Card,
  CardTitle,
  FieldLabel,
  Input,
  ErrorBox,
  BtnPrimaryWide,
  BtnLink,
} from '../styled'

export default function AuthScreen({ onAuthSuccess }) {
  const rootRef = useRef(null)
  const scopeRef = useRef(null)
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!rootRef.current) return
    const scope = createScope({ root: rootRef.current })
    scopeRef.current = scope
    animate('.auth-card', {
      opacity: [0, 1],
      translateY: [24, 0],
      duration: 600,
      ease: 'out(3)',
    })
    return () => scope.revert()
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'login') {
        await login({ email, password })
      } else {
        await register({ email, password, full_name: fullName })
      }
      animate('.auth-root', { opacity: [1, 0], duration: 450, ease: 'in(2)' }).then(() =>
        onAuthSuccess?.(),
      )
    } catch (err) {
      setError(err.message || 'Authentication failed')
    } finally {
      setBusy(false)
    }
  }

  function toggleMode() {
    setMode((m) => (m === 'login' ? 'register' : 'login'))
    setError('')
  }

  return (
    <RootCentered ref={rootRef} className="auth-root">
      <Card className="auth-card" style={{ width: '100%', maxWidth: 448, position: 'relative', paddingTop: 220 }}>
        <img
          src="/fulllogo.svg"
          alt="MedVision"
          style={{ position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)', height: 300, width: 'auto', maxWidth: '90%', objectFit: 'contain' }}
        />
        <CardTitle className="auth-title" style={{ textAlign: 'center', marginTop: 32 }}>
          {mode === 'login' ? 'Connexion' : 'Créer un compte'}
        </CardTitle>
        <p style={{ marginTop: 4, fontSize: 14, color: '#94a3b8', textAlign: 'center', margin: 0 }}>
          MedVision — espace médecin
        </p>

        <form onSubmit={handleSubmit} style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {mode === 'register' && (
            <Field label="Nom complet" value={fullName} onChange={setFullName} placeholder="Dr. Marie Dupont" />
          )}
          <Field label="Email" type="email" value={email} onChange={setEmail} placeholder="medecin@hopital.fr" />
          <Field
            label="Mot de passe"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="••••••••"
          />

          {error && <ErrorBox>{error}</ErrorBox>}

          <BtnPrimaryWide type="submit" disabled={busy}>
            {busy ? '…' : mode === 'login' ? 'Se connecter' : "S'inscrire"}
          </BtnPrimaryWide>
        </form>

        <BtnLink type="button" onClick={toggleMode}>
          {mode === 'login'
            ? "Pas de compte ? S'inscrire"
            : 'Déjà un compte ? Se connecter'}
        </BtnLink>
      </Card>
    </RootCentered>
  )
}

function Field({ label, value, onChange, type = 'text', placeholder }) {
  return (
    <label style={{ display: 'block' }}>
      <FieldLabel>{label}</FieldLabel>
      <Input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </label>
  )
}
