import { BrowserRouter, Route, Routes } from 'react-router-dom'
import SearchPage from './pages/SearchPage'
import SearchStatsPage from './pages/SearchStatsPage'
import DocumentsPage from './pages/DocumentsPage'

function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900">
          Document Vault
        </h1>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/admin/stats" element={<SearchStatsPage />} />
      </Routes>
    </BrowserRouter>
  )
}
