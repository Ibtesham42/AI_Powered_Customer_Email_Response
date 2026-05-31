import { type FormEvent, useCallback, useEffect, useState } from 'react'

import { connectMailbox, getMailbox } from '../api/mailbox'
import { useAuth } from '../auth/useAuth'
import { MailboxStatusBadge } from '../components/Badge'
import { Button, FormError, FormNotice, TextField } from '../components/ui'
import { ApiError } from '../lib/client'
import type { Mailbox } from '../lib/types'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; mailbox: Mailbox | null }

function ConnectForm({ onConnected }: { onConnected: () => void }) {
  const [email, setEmail] = useState('')
  const [appPassword, setAppPassword] = useState('')
  const [imapHost, setImapHost] = useState('imap.gmail.com')
  const [smtpHost, setSmtpHost] = useState('smtp.gmail.com')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await connectMailbox({
        email_address: email,
        app_password: appPassword,
        imap_host: imapHost,
        smtp_host: smtpHost,
      })
      setAppPassword('')
      onConnected()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Connection failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form
      onSubmit={submit}
      className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      noValidate
    >
      <FormError message={error} />
      <TextField
        label="Support email address"
        name="email_address"
        type="email"
        autoComplete="off"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <TextField
        label="App password"
        name="app_password"
        type="password"
        autoComplete="off"
        value={appPassword}
        onChange={(e) => setAppPassword(e.target.value)}
      />
      <p className="-mt-2 text-xs text-slate-400">
        A Gmail App Password (spaces are fine). Verified against IMAP and SMTP
        before it is saved, encrypted at rest.
      </p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TextField
          label="IMAP host"
          name="imap_host"
          value={imapHost}
          onChange={(e) => setImapHost(e.target.value)}
        />
        <TextField
          label="SMTP host"
          name="smtp_host"
          value={smtpHost}
          onChange={(e) => setSmtpHost(e.target.value)}
        />
      </div>
      <div className="w-40">
        <Button type="submit" loading={busy}>
          Connect mailbox
        </Button>
      </div>
    </form>
  )
}

function MailboxDetails({ mailbox }: { mailbox: Mailbox }) {
  const rows: [string, string][] = [
    ['Email', mailbox.email_address],
    ['Provider', mailbox.provider],
    ['IMAP host', mailbox.imap_host],
    ['SMTP host', mailbox.smtp_host],
    [
      'Last polled',
      mailbox.last_polled_at
        ? new Date(mailbox.last_polled_at).toLocaleString()
        : 'never',
    ],
  ]
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">
          Connected mailbox
        </h3>
        <MailboxStatusBadge status={mailbox.status} />
      </div>
      <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs uppercase tracking-wide text-slate-400">
              {label}
            </dt>
            <dd className="text-slate-700">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

export default function MailboxPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'owner'
  const [state, setState] = useState<State>({ status: 'loading' })
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(() => {
    let cancelled = false
    setState({ status: 'loading' })
    getMailbox()
      .then((mailbox) => {
        if (!cancelled) setState({ status: 'ready', mailbox })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          message:
            err instanceof ApiError
              ? err.message
              : 'Failed to load the mailbox',
        })
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])

  function onConnected() {
    setNotice('Mailbox connected.')
    load()
  }

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Mailbox</h2>
        <p className="text-sm text-slate-500">
          The support inbox the worker polls and replies from.
        </p>
      </div>

      <FormNotice message={notice} />

      {state.status === 'loading' && (
        <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Loading…
        </p>
      )}

      {state.status === 'error' && (
        <div
          role="alert"
          className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700"
        >
          {state.message}
        </div>
      )}

      {state.status === 'ready' && (
        <>
          {state.mailbox ? (
            <MailboxDetails mailbox={state.mailbox} />
          ) : (
            <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">
              No mailbox connected yet.
            </p>
          )}

          {isOwner ? (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-900">
                {state.mailbox ? 'Reconnect / update' : 'Connect a mailbox'}
              </h3>
              <ConnectForm onConnected={onConnected} />
            </div>
          ) : (
            <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">
              Only the company owner can connect the mailbox.
            </p>
          )}
        </>
      )}
    </section>
  )
}
