import { createTheme } from '@mui/material/styles'

export const tokens = {
  ink900: '#0f172a',
  slate800: 'rgba(30, 41, 59, 0.6)',
  slate800Solid: '#1e293b',
  slate700: '#334155',
  slate900: '#0f172a',
  brand600: '#2563eb',
  brand500: '#3b82f6',
  brand700: '#1d4ed8',
  slate300: '#cbd5e1',
  slate400: '#94a3b8',
  slate200: '#e2e8f0',
  white: '#ffffff',
  red500: '#ef4444',
  red400: '#f87171',
  red300: '#fca5a5',
  green600: '#16a34a',
  green300: '#86efac',
  orange400: '#fb923c',
  sky400: '#38bdf8',
  amber300: '#fcd34d',
  amber200: '#fde68a',
  emerald400: '#34d399',
}

const theme = createTheme({
  palette: {
    mode: 'dark',
    background: { default: tokens.ink900, paper: tokens.slate800Solid },
    primary: { main: tokens.brand600, light: tokens.brand500, dark: tokens.brand700 },
    text: { primary: tokens.white, secondary: tokens.slate400 },
    error: { main: tokens.red500 },
    success: { main: tokens.green600 },
    divider: 'rgba(148, 163, 184, 0.2)',
  },
  shape: { borderRadius: 16 },
  typography: {
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
    h1: { fontWeight: 700 },
    h2: { fontWeight: 600 },
  },
})

export default theme
