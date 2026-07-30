import { api, setToken, getToken, clearToken } from './client'

export async function register({ email, password, full_name }) {
  const data = await api.post('/auth/register', { email, password, full_name })
  setToken(data.access_token)
  return data
}

export async function login({ email, password }) {
  const data = await api.post('/auth/login', { email, password })
  setToken(data.access_token)
  return data
}

export function logout() {
  clearToken()
}

export async function me() {
  return api.get('/auth/me')
}

export async function updateMe(body) {
  return api.put('/auth/me', body)
}

export function isAuthenticated() {
  return !!getToken()
}
