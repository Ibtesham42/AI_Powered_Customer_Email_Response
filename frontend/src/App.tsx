import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from './auth/AuthProvider'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { AppLayout } from './components/AppLayout'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import KnowledgeBasePage from './pages/KnowledgeBasePage'
import LoginPage from './pages/LoginPage'
import MailboxPage from './pages/MailboxPage'
import OverviewPage from './pages/OverviewPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import ReviewQueuePage from './pages/ReviewQueuePage'
import SignupPage from './pages/SignupPage'
import TicketDetailPage from './pages/TicketDetailPage'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<ReviewQueuePage />} />
              <Route path="/overview" element={<OverviewPage />} />
              <Route path="/tickets/:ticketId" element={<TicketDetailPage />} />
              <Route path="/knowledge-base" element={<KnowledgeBasePage />} />
              <Route path="/mailbox" element={<MailboxPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
