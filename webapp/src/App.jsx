import { useState, useEffect, useCallback } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import SplashScreen from './components/SplashScreen'
import AuthScreen from './pages/AuthScreen'
import MedicalInfo from './pages/MedicalInfo'
import PatientMain from './pages/PatientMain'
import ExamDetail from './pages/ExamDetail'
import DoctorHome from './pages/DoctorHome'
import DoctorProfile from './pages/DoctorProfile'
import NavBar from './components/NavBar'
import { isAuthenticated, me } from './api/auth'

function AppLayout({ doctor, onLogout, onDoctorUpdate, children }) {
  return (
    <>
      <NavBar doctor={doctor} onLogout={onLogout} />
      {children}
    </>
  )
}

export default function App() {
  const [showSplash, setShowSplash] = useState(true)
  const [authed, setAuthed] = useState(false)
  const [ready, setReady] = useState(false)
  const [doctor, setDoctor] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    const t = setTimeout(() => setShowSplash(false), 3000)
    return () => clearTimeout(t)
  }, [])

  const fetchDoctor = useCallback(async () => {
    try {
      const d = await me()
      setDoctor(d)
    } catch {
      setDoctor(null)
    }
  }, [])

  useEffect(() => {
    const authed = isAuthenticated()
    setAuthed(authed)
    if (authed) fetchDoctor()
    setReady(true)
  }, [fetchDoctor])

  const handleSplashDone = () => setShowSplash(false)

  const handleAuthSuccess = () => {
    setAuthed(true)
    fetchDoctor()
    navigate('/doctor-home')
  }

  const handleLogout = () => {
    setAuthed(false)
    setDoctor(null)
    navigate('/')
  }

  const L = ({ children }) => (
    <AppLayout doctor={doctor} onLogout={handleLogout} onDoctorUpdate={fetchDoctor}>
      {children}
    </AppLayout>
  )

  return (
    <>
      {showSplash && <SplashScreen onDone={handleSplashDone} />}
      {!showSplash && ready && (
        <Routes>
          <Route
            path="/"
            element={
              authed ? (
                <Navigate to="/doctor-home" replace />
              ) : (
                <AuthScreen onAuthSuccess={handleAuthSuccess} />
              )
            }
          />
          <Route
            path="/doctor-home"
            element={
              authed ? (
                <L><DoctorHome onLogout={handleLogout} /></L>
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route
            path="/profile"
            element={
              authed ? (
                <L><DoctorProfile onLogout={handleLogout} onDoctorUpdate={fetchDoctor} /></L>
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route
            path="/medical-info"
            element={
              authed ? (
                <L><MedicalInfo onLogout={handleLogout} /></L>
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route
            path="/patients/:patientId"
            element={
              authed ? (
                <PatientMain onLogout={handleLogout} />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route
            path="/patients/:patientId/exams/:examId"
            element={
              authed ? (
                <ExamDetail onLogout={handleLogout} />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      )}
    </>
  )
}
