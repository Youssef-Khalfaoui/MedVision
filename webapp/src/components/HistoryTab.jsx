import { useRef, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { animate, createScope } from 'animejs'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import { getPatientExams } from '../api/patients'
import { deleteExam } from '../api/exams'
import { SectionTitle, Panel, Spinner } from '../styled'

export default function HistoryTab({ patientId }) {
  const rootRef = useRef(null)
  const scopeRef = useRef(null)
  const navigate = useNavigate()
  const [exams, setExams] = useState([])
  const [loading, setLoading] = useState(true)

  const handleDelete = async (e, examId) => {
    e.stopPropagation();
    if (!window.confirm("Êtes-vous sûr de vouloir supprimer cet examen ? Cette action est irréversible.")) return;
    try {
      await deleteExam(examId);
      setExams(exams.filter(ex => ex.id !== examId));
    } catch (err) {
      console.error('Failed to delete exam', err);
    }
  }

  useEffect(() => {
    let active = true
    let timer = null

    async function fetchExams() {
      let rows = []
      try {
        rows = await getPatientExams(patientId)
        if (active) setExams(rows)
      } catch {
        if (active) setExams([])
      } finally {
        if (active) setLoading(false)
      }
      const pending = (rows || []).some(
        (e) =>
          e.status === 'PENDING' ||
          e.status === 'CLASSIFYING' ||
          e.status === 'COMPARING' ||
          e.status === 'GENERATING' ||
          e.status === 'VALIDATING',
      )
      if (pending) {
        timer = setTimeout(fetchExams, 4000)
      }
    }

    fetchExams()
    return () => {
      active = false
      if (timer) clearTimeout(timer)
    }
  }, [patientId])

  useEffect(() => {
    const scope = scopeRef.current
    if (!scope || exams.length === 0) return
    animate('.exam-row', {
      opacity: [0, 1],
      translateX: [-20, 0],
      duration: 400,
      delay: (el, i) => i * 60,
      ease: 'out(2)',
    })
  }, [exams])

  const trend = exams
    .map((ex) => {
      const sf = ex.structured_findings || {}
      const noFinding = sf['No Finding'] ?? 0
      const score = Math.round((1 - noFinding) * 100)
      return { date: new Date(ex.exam_date).toLocaleDateString('fr-FR'), score }
    })
    .reverse()

  return (
    <div ref={rootRef} className="history-tab" style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      <section>
        <SectionTitle>Tendances (sévérité globale)</SectionTitle>
        <Panel style={{ padding: 16 }}>
          {trend.length > 1 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: 'none' }}
                  labelStyle={{ color: '#e2e8f0' }}
                />
                <Line type="monotone" dataKey="score" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p style={{ fontSize: 14, color: '#94a3b8' }}>
              Au moins deux examens sont nécessaires pour afficher une tendance.
            </p>
          )}
        </Panel>
      </section>

      <section>
        <SectionTitle>Examens ({exams.length})</SectionTitle>
        {loading ? (
          <Spinner>Chargement…</Spinner>
        ) : exams.length === 0 ? (
          <p style={{ fontSize: 14, color: '#94a3b8' }}>Aucun examen pour ce patient.</p>
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {exams.map((ex) => (
              <li key={ex.id} className="exam-row" style={{ borderRadius: 12, border: '1px solid #334155', background: 'rgba(30,41,59,0.4)', padding: 16 }}>
                <div
                  onClick={() => navigate(`/patients/${patientId}/exams/${ex.id}`)}
                  style={{ width: '100%', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', transition: 'border-color 0.2s', padding: 0 }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#3b82f6')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'transparent')}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 500, color: '#fff' }}>Examen #{ex.examen_number ?? ex.id}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ fontSize: 14, color: '#94a3b8' }}>
                        {new Date(ex.exam_date).toLocaleString('fr-FR')}
                      </span>
                      <button 
                        onClick={(e) => handleDelete(e, ex.id)} 
                        style={{ background: '#ef4444', color: 'white', border: 'none', borderRadius: '6px', padding: '4px 10px', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold' }}
                      >
                        Supprimer
                      </button>
                    </div>
                  </div>
                  <p style={{ marginTop: 4, fontSize: 14, color: '#cbd5e1', margin: 0 }}>Statut : {ex.status}</p>
                  {ex.report_text_clinical && (
                    <details style={{ marginTop: 8, fontSize: 14, color: '#94a3b8' }}>
                      <summary style={{ cursor: 'pointer', color: '#60a5fa' }}>Rapport clinique</summary>
                      <pre style={{ marginTop: 8, whiteSpace: 'pre-wrap', borderRadius: 8, background: 'rgba(15,23,42,0.6)', padding: 12, fontSize: 12 }}>
                        {ex.report_text_clinical}
                      </pre>
                    </details>
                  )}
                  <p style={{ marginTop: 8, fontSize: 12, color: '#60a5fa', margin: 0 }}>Voir le détail complet →</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
