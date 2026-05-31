import { type FormEvent, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import * as authApi from '../api/auth'
import { AuthCard } from '../components/AuthCard'
import { Button, FormError, FormNotice, TextField } from '../components/ui'
import { ApiError } from '../lib/client'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setFieldError(null)
    setFormError(null)
    if (password.length < 8) {
      setFieldError('At least 8 characters')
      return
    }
    if (password !== confirm) {
      setFieldError('Passwords do not match')
      return
    }
    setSubmitting(true)
    try {
      await authApi.resetPassword({ token, new_password: password })
      setDone(true)
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : 'Something went wrong',
      )
    } finally {
      setSubmitting(false)
    }
  }

  if (!token) {
    return (
      <AuthCard
        title="Reset your password"
        footer={
          <Link
            to="/forgot-password"
            className="text-indigo-600 hover:underline"
          >
            Request a new link
          </Link>
        }
      >
        <FormError message="This reset link is missing its token. Request a new one." />
      </AuthCard>
    )
  }

  return (
    <AuthCard
      title="Choose a new password"
      footer={
        <Link to="/login" className="text-indigo-600 hover:underline">
          Back to sign in
        </Link>
      }
    >
      {done ? (
        <FormNotice message="Password updated. You can now sign in." />
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <FormError message={formError} />
          <TextField
            label="New password"
            name="new_password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <TextField
            label="Confirm new password"
            name="confirm_password"
            type="password"
            autoComplete="new-password"
            value={confirm}
            error={fieldError ?? undefined}
            onChange={(e) => setConfirm(e.target.value)}
          />
          <Button type="submit" loading={submitting}>
            Update password
          </Button>
        </form>
      )}
    </AuthCard>
  )
}
