import { useRef, useState, useEffect } from 'react'
import { animate, createScope } from 'animejs'
import { gradcamUrl, examImageUrl, reportPdfUrl } from '../api/exams'
import {
  Panel,
  SectionTitle,
  BarOuter,
  BarInner,
  Mono,
  Pill,
  Chip,
  ChipSolid,
  ReportPre,
  AmberBox,
} from '../styled'

export default function ExamResult({ exam }) {
  const rootRef = useRef(null)
  const scopeRef = useRef(null)
  const [reportMode, setReportMode] = useState('clinical')
  const [reportKey, setReportKey] = useState(0)

  const result = exam
  const hasPatientReport = !!result?.report_text_patient
  const showPdfBtn = reportMode === 'patient' && hasPatientReport
  const sortedFindings = result?.structured_findings
    ? Object.entries(result.structured_findings).sort((a, b) => b[1] - a[1])
    : []
  const validation = result?.validation_result_clinical

  useEffect(() => {
    if (!rootRef.current) return
    const scope = createScope({ root: rootRef.current })
    scopeRef.current = scope
    animate('.an-result', { opacity: [0, 1], translateY: [10, 0], duration: 400, ease: 'out(3)' })
    return () => scope.revert()
  }, [])

  useEffect(() => {
    const scope = scopeRef.current
    if (!scope) return
    animate('.an-report-body', { opacity: [0, 1], translateY: [8, 0], duration: 300, ease: 'out(2)' })
  }, [reportKey])

  function toggleReport() {
    setReportMode((m) => (m === 'clinical' ? 'patient' : 'clinical'))
    setReportKey((k) => k + 1)
  }

  return (
    <div ref={rootRef} className="an-result" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <SectionTitle>
        Examen {result.examen_number ? `#${result.examen_number}` : `#${result.id}`}
        <span style={{ fontWeight: 400, color: '#94a3b8', marginLeft: 8, fontSize: 13 }}>
          (réf. interne #{result.id})
        </span>
      </SectionTitle>
      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
        <Panel>
          <SectionTitle>Grad-CAM</SectionTitle>
          <img src={gradcamUrl(result.id)} alt="Grad-CAM" style={{ width: '100%', borderRadius: 8 }} />
        </Panel>
        <Panel>
          <SectionTitle>Radio originale</SectionTitle>
          <img src={examImageUrl(result.id)} alt="Radio" style={{ width: '100%', borderRadius: 8 }} />
        </Panel>
      </div>

      <Panel>
        <SectionTitle>Probabilités (triées)</SectionTitle>
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {sortedFindings.map(([label, prob]) => (
            <li key={label} style={{ fontSize: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#e2e8f0' }}>
                <span>{label}</span>
                <Mono>{(prob * 100).toFixed(1)}%</Mono>
              </div>
              <BarOuter>
                <BarInner style={{ width: `${Math.min(100, prob * 100)}%` }} />
              </BarOuter>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12, marginBottom: 12 }}>
          <SectionTitle style={{ margin: 0 }}>Rapport clinique</SectionTitle>
          {validation && (
            <Pill $bg={validation.verdict === 'PASS' ? 'rgba(22,163,74,0.3)' : 'rgba(239,68,68,0.3)'}
                  $color={validation.verdict === 'PASS' ? '#86efac' : '#fca5a5'}>
              Validation : {validation.verdict}
            </Pill>
          )}
          {result.engine && <Pill>{result.engine}</Pill>}
          <Chip href={reportPdfUrl(result.id, 'clinical', true)} target="_blank" rel="noreferrer">
            Voir PDF
          </Chip>
          <ChipSolid href={reportPdfUrl(result.id, 'clinical', false)} download>
            Télécharger PDF
          </ChipSolid>
        </div>
        <ReportPre className="an-report-body">{result.report_text_clinical}</ReportPre>
      </Panel>

      {result.report_text_patient ? (
        <Panel>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <SectionTitle style={{ margin: 0 }}>Rapport patient</SectionTitle>
            <Chip href={reportPdfUrl(result.id, 'patient', true)} target="_blank" rel="noreferrer">
              Voir PDF
            </Chip>
            <ChipSolid href={reportPdfUrl(result.id, 'patient', false)} download>
              Télécharger PDF
            </ChipSolid>
          </div>
          <ReportPre className="an-report-body">{result.report_text_patient}</ReportPre>
        </Panel>
      ) : (
        <AmberBox>Version patient non disponible — rapport clinique non validé</AmberBox>
      )}
    </div>
  )
}
