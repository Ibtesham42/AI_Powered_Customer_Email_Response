import { type FormEvent, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'

import * as authApi from '../api/auth'
import { useAuth } from '../auth/useAuth'
import { AuthCard } from '../components/AuthCard'
import { Button, FormError, TextField } from '../components/ui'
import { ApiError } from '../lib/client'
import type { SignupRequest } from '../lib/types'

const EMPTY: SignupRequest = {
  full_name: '',
  email: '',
  phone: '',
  password: '',
  verify_password: '',
  company_name: '',
  address: '',
  city: '',
  state: '',
  country: '',
  postal_code: '',
}

const FIELDS: {
  name: keyof SignupRequest
  label: string
  type?: string
  autoComplete?: string
}[] = [
  { name: 'full_name', label: 'Full name', autoComplete: 'name' },
  { name: 'email', label: 'Email', type: 'email', autoComplete: 'email' },
  { name: 'phone', label: 'Phone', autoComplete: 'tel' },
  {
    name: 'password',
    label: 'Password',
    type: 'password',
    autoComplete: 'new-password',
  },
  {
    name: 'verify_password',
    label: 'Confirm password',
    type: 'password',
    autoComplete: 'new-password',
  },
  { name: 'company_name', label: 'Company name', autoComplete: 'organization' },
  { name: 'address', label: 'Address', autoComplete: 'street-address' },
  { name: 'city', label: 'City' },
  { name: 'state', label: 'State' },
  { name: 'country', label: 'Country' },
  { name: 'postal_code', label: 'Postal code', autoComplete: 'postal-code' },
]

const REQUIRED: (keyof SignupRequest)[] = [
  'full_name',
  'company_name',
  'phone',
  'address',
  'city',
  'state',
  'country',
  'postal_code',
]

type Errors = Partial<Record<keyof SignupRequest, string>>

// Mirror backend validation (backend/models/schemas.py SignupRequest).
function validate(f: SignupRequest): Errors {
  const errs: Errors = {}
  for (const key of REQUIRED) {
    if (!f[key].trim()) errs[key] = 'Required'
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) {
    errs.email = 'Enter a valid email'
  }
  if (f.password.length < 8) {
    errs.password = 'At least 8 characters'
  }
  if (f.verify_password !== f.password) {
    errs.verify_password = 'Passwords do not match'
  }
  return errs
}

export default function SignupPage() {
  const { status, login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<SignupRequest>(EMPTY)
  const [errors, setErrors] = useState<Errors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (status === 'authenticated') return <Navigate to="/" replace />

  function update(name: keyof SignupRequest, value: string) {
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setFormError(null)
    const found = validate(form)
    setErrors(found)
    if (Object.keys(found).length > 0) return

    setSubmitting(true)
    try {
      await authApi.signup(form)
      // Signup returns ids only (not tokens) — log in with the same creds.
      await login(form.email, form.password)
      navigate('/', { replace: true })
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : 'Something went wrong',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      title="Create your account"
      subtitle="A new company workspace is created and you become its owner."
      wide
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="text-indigo-600 hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <FormError message={formError} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {FIELDS.map((field) => (
            <TextField
              key={field.name}
              label={field.label}
              name={field.name}
              type={field.type ?? 'text'}
              autoComplete={field.autoComplete}
              value={form[field.name]}
              error={errors[field.name]}
              onChange={(e) => update(field.name, e.target.value)}
            />
          ))}
        </div>
        <Button type="submit" loading={submitting}>
          Create account
        </Button>
      </form>
    </AuthCard>
  )
}
