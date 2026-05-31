import { type FormEvent, useCallback, useEffect, useState } from 'react'

import {
  ingestFaq,
  ingestUrl,
  listDocuments,
  SUPPORTED_EXTENSIONS,
  uploadFile,
} from '../api/data'
import { useAuth } from '../auth/useAuth'
import { KbStatusBadge } from '../components/Badge'
import { Button, FormError, FormNotice, TextField } from '../components/ui'
import { ApiError } from '../lib/client'
import type { KbDocument } from '../lib/types'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; documents: KbDocument[] }

type Mode = 'file' | 'url' | 'faq'

const MODES: { key: Mode; label: string }[] = [
  { key: 'file', label: 'File' },
  { key: 'url', label: 'URL' },
  { key: 'faq', label: 'FAQ' },
]

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : '—'
}

function Uploader({ onAdded }: { onAdded: () => void }) {
  const [mode, setMode] = useState<Mode>('file')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [file, setFile] = useState<File | null>(null)
  const [fileKey, setFileKey] = useState(0)
  const [url, setUrl] = useState('')
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setNotice(null)
    setBusy(true)
    try {
      let message: string
      if (mode === 'file') {
        if (!file) {
          setError('Choose a file to upload.')
          return
        }
        message = (await uploadFile(file)).message
      } else if (mode === 'url') {
        message = (await ingestUrl(url)).message
      } else {
        message = (await ingestFaq(question, answer)).message
      }
      setNotice(message)
      setFile(null)
      setFileKey((k) => k + 1)
      setUrl('')
      setQuestion('')
      setAnswer('')
      onAdded()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex gap-1">
        {MODES.map((m) => (
          <button
            key={m.key}
            type="button"
            onClick={() => setMode(m.key)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
              mode === m.key
                ? 'bg-indigo-600 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="mt-4 space-y-4" noValidate>
        <FormError message={error} />
        <FormNotice message={notice} />

        {mode === 'file' && (
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Document
            </label>
            <input
              key={fileKey}
              type="file"
              accept={SUPPORTED_EXTENSIONS.join(',')}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="mt-1 block w-full text-sm text-slate-700 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium hover:file:bg-slate-200"
            />
            <p className="mt-1 text-xs text-slate-400">
              Supported: {SUPPORTED_EXTENSIONS.join(', ')}
            </p>
          </div>
        )}

        {mode === 'url' && (
          <TextField
            label="Page URL"
            name="url"
            type="url"
            placeholder="https://example.com/help/returns"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        )}

        {mode === 'faq' && (
          <>
            <TextField
              label="Question"
              name="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <div>
              <label className="block text-sm font-medium text-slate-700">
                Answer
              </label>
              <textarea
                rows={4}
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </>
        )}

        <div className="w-40">
          <Button type="submit" loading={busy}>
            Add to knowledge base
          </Button>
        </div>
      </form>
    </div>
  )
}

export default function KnowledgeBasePage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'owner'
  const [state, setState] = useState<State>({ status: 'loading' })

  const load = useCallback(() => {
    let cancelled = false
    setState({ status: 'loading' })
    listDocuments()
      .then((documents) => {
        if (!cancelled) setState({ status: 'ready', documents })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          message:
            err instanceof ApiError ? err.message : 'Failed to load documents',
        })
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">
            Knowledge base
          </h2>
          <p className="text-sm text-slate-500">
            Sources the AI uses to ground its replies.
          </p>
        </div>
        <button
          onClick={() => load()}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          Refresh
        </button>
      </div>

      {isOwner ? (
        <Uploader onAdded={load} />
      ) : (
        <p className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">
          Only the company owner can add knowledge-base sources.
        </p>
      )}

      {state.status === 'loading' && (
        <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Loading documents…
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

      {state.status === 'ready' && state.documents.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
          No documents yet.
        </div>
      )}

      {state.status === 'ready' && state.documents.length > 0 && (
        <div className="space-y-2">
          {state.documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-900">
                  {doc.filename}
                </p>
                <p className="text-xs text-slate-400">
                  {doc.doc_type.toUpperCase()} · added{' '}
                  {formatDate(doc.created_at)}
                  {doc.status === 'error' && doc.error ? ` · ${doc.error}` : ''}
                </p>
              </div>
              <KbStatusBadge status={doc.status} />
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
