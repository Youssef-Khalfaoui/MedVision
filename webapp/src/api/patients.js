import { api } from './client'

export async function searchPatients({ name = '', patientId = '', age = '' } = {}) {
  let params = `limit=50`
  if (name) params += `&name=${encodeURIComponent(name)}`
  if (patientId) params += `&patient_id=${encodeURIComponent(patientId)}`
  if (age) params += `&age=${encodeURIComponent(age)}`
  return api.get(`/patients?${params}`)
}

export async function getPatient(id) {
  return api.get(`/patients/${encodeURIComponent(id)}`)
}

export async function createPatient({ id, full_name, date_of_birth, sex }) {
  return api.post('/patients', { id, full_name, date_of_birth, sex })
}

export async function patientExists(id) {
  return api.get(`/patients/${encodeURIComponent(id)}/exists`)
}

export async function getPatientExams(id) {
  return api.get(`/patients/${encodeURIComponent(id)}/exams`)
}

export async function updatePatient(id, body) {
  return api.put(`/patients/${encodeURIComponent(id)}`, body)
}

export async function deletePatient(id) {
  return api.delete(`/patients/${encodeURIComponent(id)}`)
}

export async function getMedicalHistory(id) {
  return api.get(`/patients/${encodeURIComponent(id)}/medical-history`)
}

export async function upsertMedicalHistory(id, body) {
  return api.put(`/patients/${encodeURIComponent(id)}/medical-history`, body)
}
