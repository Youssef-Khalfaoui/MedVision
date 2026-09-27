import styled from 'styled-components'
import { tokens } from './theme'

export const Root = styled.div`
  min-height: 100vh;
  background: ${tokens.ink900};
  padding: 2.5rem 1rem; /* px-4 py-10 */
  
  @media (max-width: 768px) {
    padding: 1.5rem 0.75rem;
  }
  
  @media (max-width: 480px) {
    padding: 1rem 0.5rem;
  }
`
export const RootCentered = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${tokens.ink900};
  padding: 1rem; /* px-4 */
`
export const MaxWide = styled.div`
  width: 100%;
  max-width: 42rem; /* max-w-2xl */
  margin: 0 auto;
`
export const MaxWide5 = styled.main`
  max-width: 64rem; /* max-w-5xl */
  margin: 0 auto;
  padding: 2rem 1.5rem; /* px-6 py-8 */
  
  @media (max-width: 768px) {
    padding: 1.5rem 1rem;
  }
  
  @media (max-width: 480px) {
    padding: 1rem 0.75rem;
  }
`

export const Card = styled.div`
  border-radius: 1rem; /* rounded-2xl */
  background: ${tokens.slate800}; /* slate-800/60 */
  padding: 1.5rem; /* p-6 */
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.4); /* shadow-xl */
  
  @media (max-width: 768px) {
    padding: 1.25rem;
    border-radius: 0.75rem;
  }
  
  @media (max-width: 480px) {
    padding: 1rem;
    border-radius: 0.5rem;
  }
`
export const Panel = styled.div`
  border-radius: 1rem; /* rounded-2xl */
  border: 1px solid ${tokens.slate700}; /* border-slate-700 */
  background: rgba(30, 41, 59, 0.4); /* slate-800/40 */
  padding: 1.25rem; /* p-5 */
`
export const FieldSet = styled.fieldset`
  border-radius: 0.5rem; /* rounded-lg */
  border: 1px solid ${tokens.slate700};
  padding: 1rem;
`
export const Legend = styled.legend`
  padding: 0 0.5rem;
  font-size: 0.875rem; /* text-sm */
  font-weight: 600;
  color: ${tokens.brand500};
`

export const HeaderBar = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(30, 41, 59, 0.8); /* border-slate-800 */
  padding: 1rem 1.5rem; /* px-6 py-4 */
  
  @media (max-width: 768px) {
    padding: 0.75rem 1rem;
  }
  
  @media (max-width: 480px) {
    padding: 0.5rem 0.75rem;
  }
`
export const Title = styled.h1`
  font-size: 1.25rem; /* text-xl */
  font-weight: 700;
  color: ${tokens.white};
  margin: 0;
  
  @media (max-width: 768px) {
    font-size: 1.125rem;
  }
  
  @media (max-width: 480px) {
    font-size: 1rem;
  }
`
export const SubTitle = styled.p`
  font-size: 0.875rem;
  color: ${tokens.slate400};
  margin: 0;
`
export const SectionTitle = styled.h2`
  font-size: 1.125rem; /* text-lg */
  font-weight: 600;
  color: ${tokens.white};
  margin: 0 0 0.75rem; /* mb-3 */
`
export const CardTitle = styled.h2`
  font-size: 1.5rem; /* text-2xl */
  font-weight: 700;
  color: ${tokens.white};
  margin: 0;
`

const btnBase = `
  border-radius: 0.5rem;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
  border: none;
`
export const BtnPrimary = styled.button`
  ${btnBase}
  background: ${tokens.brand600};
  color: ${tokens.white};
  &:hover { background: ${tokens.brand700}; }
  &:disabled { opacity: 0.6; cursor: not-allowed; }
`
export const BtnPrimaryWide = styled.button`
  ${btnBase}
  width: 100%;
  background: ${tokens.brand600};
  color: ${tokens.white};
  font-weight: 600;
  &:hover { background: ${tokens.brand700}; }
  &:disabled { opacity: 0.6; cursor: not-allowed; }
`
export const BtnGhost = styled.button`
  ${btnBase}
  background: transparent;
  border: 1px solid ${tokens.slate700};
  color: ${tokens.slate300};
  &:hover { background: rgba(30, 41, 59, 0.6); }
`
export const BtnLink = styled.button`
  background: none;
  border: none;
  width: 100%;
  text-align: center;
  font-size: 0.875rem;
  color: ${tokens.brand500};
  cursor: pointer;
  margin-top: 1rem; /* mt-4 */
  &:hover { color: ${tokens.brand500}; filter: brightness(1.2); }
`

export const FieldLabel = styled.span`
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
  color: ${tokens.slate300};
`
export const Input = styled.input`
  width: 100%;
  border-radius: 0.5rem;
  border: 1px solid ${tokens.slate700};
  background: rgba(15, 23, 42, 0.6); /* slate-900/60 */
  padding: 0.5rem 0.75rem;
  color: ${tokens.white};
  outline: none;
  &:focus { border-color: ${tokens.brand500}; }
`
export const Select = styled.select`
  width: 100%;
  border-radius: 0.5rem;
  border: 1px solid ${tokens.slate700};
  background: rgba(15, 23, 42, 0.6);
  padding: 0.5rem 0.75rem;
  color: ${tokens.white};
  outline: none;
  &:focus { border-color: ${tokens.brand500}; }
`
export const TextArea = styled.textarea`
  width: 100%;
  border-radius: 0.5rem;
  border: 1px solid ${tokens.slate700};
  background: rgba(15, 23, 42, 0.6);
  padding: 0.5rem 0.75rem;
  color: ${tokens.white};
  outline: none;
  &:focus { border-color: ${tokens.brand500}; }
`

export const ErrorBox = styled.p`
  border-radius: 0.375rem; /* rounded-md */
  background: rgba(239, 68, 68, 0.1); /* bg-red-500/10 */
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: ${tokens.red300};
  margin: 0;
`
export const Spinner = styled.p`
  font-size: 0.875rem;
  color: ${tokens.slate400};
  margin: 0;
`
export const Mono = styled.span`
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
`
export const ProgressTrack = styled.div`
  height: 0.5rem; /* h-2 */
  width: 100%;
  overflow: hidden;
  border-radius: 9999px;
  background: ${tokens.slate700};
`
export const ProgressFill = styled.div`
  height: 100%;
  border-radius: 9999px;
  background: ${tokens.brand500};
  width: 0%;
`
export const DropZone = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 0.75rem; /* rounded-xl */
  border: 2px dashed ${tokens.slate700};
  padding: 2rem; /* p-8 */
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  ${(p) =>
    p.$active
      ? `border-color: ${tokens.brand500}; background: rgba(59,130,246,0.1);`
      : `&:hover { border-color: #64748b; }`}
`
export const Nav = styled.nav`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`
export const Pill = styled.span`
  border-radius: 9999px;
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  background: ${(p) => p.$bg || tokens.slate700};
  color: ${(p) => p.$color || tokens.slate300};
`
export const Chip = styled.a`
  border-radius: 0.5rem;
  border: 1px solid ${tokens.slate700};
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  color: ${tokens.slate200};
  text-decoration: none;
  &:hover { background: rgba(30, 41, 59, 0.8); }
`
export const ChipSolid = styled.a`
  border-radius: 0.5rem;
  background: ${tokens.brand600};
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: ${tokens.white};
  text-decoration: none;
  &:hover { background: ${tokens.brand500}; }
`
export const ReportPre = styled.pre`
  white-space: pre-wrap;
  border-radius: 0.5rem;
  background: rgba(15, 23, 42, 0.6);
  padding: 1rem;
  font-size: 0.875rem;
  color: ${tokens.slate200};
  margin: 0;
`
export const BarOuter = styled.div`
  margin-top: 0.25rem;
  height: 0.375rem; /* h-1.5 */
  width: 100%;
  border-radius: 9999px;
  background: ${tokens.slate700};
`
export const BarInner = styled.div`
  height: 100%;
  border-radius: 9999px;
  background: linear-gradient(to right, ${tokens.orange400}, ${tokens.sky400});
`
export const AmberBox = styled.div`
  margin-top: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(180, 83, 9, 0.5);
  background: rgba(245, 158, 11, 0.1);
  padding: 0.75rem;
  font-size: 0.875rem;
  color: ${tokens.amber200};
`
export const AmberBoxInner = styled.div`
  margin-top: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(245, 158, 11, 0.5);
  background: rgba(245, 158, 11, 0.1);
  padding: 0.75rem;
  font-size: 0.875rem;
  color: ${tokens.amber200};
`

export const Row = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(51, 65, 85, 0.5);
  padding-bottom: 0.25rem;
`
export const Grid2 = styled.div`
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  @media (min-width: 768px) { grid-template-columns: repeat(2, minmax(0, 1fr)); }
`
export const CheckLabel = styled.label`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: ${tokens.slate200};
`
export const CheckBox = styled.input`
  height: 1rem;
  width: 1rem;
  border-radius: 0.25rem;
  border: 1px solid #64748b;
  background: rgba(15, 23, 42, 0.6);
  accent-color: ${tokens.brand500};
`
export const FlexBetween = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem; /* mb-8 */
`

export const BtnRow = styled.div`
  display: flex;
  gap: 0.75rem; /* gap-3 */
`
