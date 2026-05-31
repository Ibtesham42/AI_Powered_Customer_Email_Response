import { type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'

import * as authApi from '../api/auth'
import { AuthCard } from '../components/AuthCard'
import { Button, FormError, FormNotice, TextField } from '../components/ui'
import { ApiError } from '../lib/client'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setNotice(null)
    setSubmitting(true)
    try {
      const res = await authApi.forgotPassword({ email })
      // The backend returns the same generic message whether or not the email
      // is registered (no account enumeration).
      setNotice(res.message)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      title="Reset your password"
      subtitle="We'll email you a reset link if the address is registered."
      footer={
        <Link to="/login" className="text-indigo-600 hover:underline">
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <FormError message={error} />
        <FormNotice message={notice} />
        <TextField
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <Button type="submit" loading={submitting}>
          Send reset link
        </Button>
      </form>
    </AuthCard>
  )
}
