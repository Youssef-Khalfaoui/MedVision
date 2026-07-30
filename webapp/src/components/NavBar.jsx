import { useNavigate, useLocation } from 'react-router-dom'
import { tokens } from '../theme'
import { BtnGhost } from '../styled'

const linkStyle = (active) => ({
  background: 'none',
  border: 'none',
  fontSize: 14,
  fontWeight: active ? 600 : 400,
  color: active ? '#fff' : tokens.slate400,
  cursor: 'pointer',
  padding: '6px 12px',
  borderRadius: 6,
  transition: 'all 0.15s ease',
  textDecoration: 'none',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
})

export default function NavBar({ doctor, onLogout }) {
  const navigate = useNavigate()
  const location = useLocation()

  const isActive = (path) => location.pathname === path

  return (
    <nav
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        padding: '1.25rem 1.5rem',
        borderBottom: '1px solid rgba(30, 41, 59, 0.8)',
        position: 'relative',
      }}
    >
      <img
        src="/logo-icon.svg"
        alt="MedVision"
        onClick={() => navigate('/doctor-home')}
        style={{
          position: 'absolute',
          left: '1.5rem',
          top: -42,
          height: 180,
          width: 180,
          objectFit: 'contain',
          cursor: 'pointer',
        }}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 16, paddingLeft: 200 }}>
        <div style={{ width: 1, height: 24, background: tokens.slate700 }} />

        <button
          style={linkStyle(isActive('/doctor-home'))}
          onClick={() => navigate('/doctor-home')}
        >
          Accueil
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button
          style={linkStyle(isActive('/profile'))}
          onClick={() => navigate('/profile')}
        >
          Profil
        </button>

        {doctor && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '4px 10px',
              borderRadius: 8,
              background: 'rgba(30, 41, 59, 0.5)',
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                background: tokens.brand600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 13,
                fontWeight: 700,
                color: '#fff',
                flexShrink: 0,
              }}
            >
              {doctor.full_name
                ? doctor.full_name
                    .split(' ')
                    .map((w) => w[0])
                    .join('')
                    .slice(0, 2)
                    .toUpperCase()
                : '?'}
            </div>
            <div style={{ lineHeight: 1.3 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: '#e2e8f0',
                  whiteSpace: 'nowrap',
                }}
              >
                {doctor.full_name || 'Médecin'}
                {doctor.specialty && (
                  <span style={{ fontWeight: 400, color: tokens.slate400, marginLeft: 4 }}>
                    · {doctor.specialty}
                  </span>
                )}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: tokens.slate400,
                  whiteSpace: 'nowrap',
                }}
              >
                {doctor.email || ''}
              </div>
            </div>
          </div>
        )}

        <BtnGhost
          type="button"
          onClick={onLogout}
          style={{ fontSize: 13, padding: '4px 10px', flexShrink: 0 }}
        >
          Déconnexion
        </BtnGhost>
      </div>
    </nav>
  )
}
