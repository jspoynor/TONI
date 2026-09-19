import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import VcChat from './pages/VcChat.tsx'
import CompanyChat from './pages/CompanyChat.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<VcChat />} />
        <Route path="/submit-statements" element={<CompanyChat />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
