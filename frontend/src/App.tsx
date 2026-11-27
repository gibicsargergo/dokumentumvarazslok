import { BrowserRouter, Route, Routes } from 'react-router-dom'
import SearchPage from './pages/SearchPage'
import DocumentsPage from './pages/DocumentsPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ProtectedRoute from './auth/ProtectedRoute'
import AdminRoute from './auth/AdminRoute'
import AuthenticatedLayout from './components/AuthenticatedLayout';
import SearchStatsPage from './pages/SearchStatsPage'

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
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        <Route element={<ProtectedRoute />}>
          <Route element={<AuthenticatedLayout />}>
              <Route path="/" element={<Home />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route element={<AdminRoute />}>
                <Route path="/admin/stats" element={<SearchStatsPage />} />
              </Route>
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
