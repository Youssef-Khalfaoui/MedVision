import { api } from './client'

export async function uploadExam(patientId, file) {
  const form = new FormData()
  form.append('patient_id', patientId)
  form.append('file', file)
  return api.postForm('/exams', form)
}

export async function getExam(examId) {
  return api.get(`/exams/${examId}`)
}

export async function checkDuplicate(patientId, imageHash) {
  const qs = new URLSearchParams({ image_hash: imageHash, patient_id: patientId }).toString()
  return api.get(`/exams/check-duplicate?${qs}`)
}
export function gradcamUrl(examId) {
  const token = localStorage.getItem('mv_token')
  return `/api/exams/${examId}/gradcam?token=${encodeURIComponent(token || '')}`
}

export function examImageUrl(examId) {
  const token = localStorage.getItem('mv_token')
  return `/api/exams/${examId}/image?token=${encodeURIComponent(token || '')}`
}

export function reportPdfUrl(examId, kind, inline = false) {
  const token = localStorage.getItem('mv_token')
  const q = new URLSearchParams({ token: token || '' })
  if (inline) q.set('inline', 'true')
  return `/api/exams/${examId}/report/${kind}/pdf?${q.toString()}`
}

export function patientPdfUrl(examId) {
  const token = localStorage.getItem('mv_token')
  return `/api/exams/${examId}/report/patient/pdf?token=${encodeURIComponent(token || '')}`
}

export async function deleteExam(examId) {
  return api.delete(`/exams/${examId}`)
}
