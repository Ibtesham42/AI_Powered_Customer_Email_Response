import { useState } from 'react'

import * as messagesApi from '../api/messages'
import { ApiError } from '../lib/client'
import type { MessageDetail } from '../lib/types'
import { FormError } from './ui'

const SECONDARY =
  'rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60'
const PRIMARY =
  'rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60'
const DANGER =
  'rounded-lg border border-rose-300 px-3 py-1.5 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60'

/**
 * The draft-review controls for one inbound Message. Two-step flow matching the
 * backend: DRAFTED → approve/save (→ REVIEWED) → send (→ SENT). Reject escalates
 * the Ticket; regenerate re-runs the AI draft.
 */
export function ReviewPanel({
  message,
  onChanged,
  onEscalated,
}: {
  message: MessageDetail
  onChanged: () => void
  onEscalated: () => void
}) {
  const [text, setText] = useState(
    message.final_reply ?? message.ai_draft ?? '',
  )
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const isReviewed = message.review_status === 'reviewed'
  const disabled = busy !== null

  function fail(err: unknown) {
    setError(err instanceof ApiError ? err.message : 'Action failed')
  }

  async function onRegenerate() {
    setBusy('regenerate')
    setError(null)
    try {
      const updated = await messagesApi.regenerateDraft(message.id)
      setText(updated.ai_draft ?? '')
      onChanged()
    } catch (err) {
      fail(err)
    } finally {
      setBusy(null)
    }
  }

  async function onApprove() {
    setBusy('approve')
    setError(null)
    try {
      await messagesApi.approveDraft(message.id)
      onChanged()
    } catch (err) {
      fail(err)
    } finally {
      setBusy(null)
    }
  }

  async function onSave() {
    setBusy('save')
    setError(null)
    try {
      await messagesApi.saveDraft(message.id, text)
      onChanged()
    } catch (err) {
      fail(err)
    } finally {
      setBusy(null)
    }
  }

  async function onReject() {
    setBusy('reject')
    setError(null)
    try {
      await messagesApi.rejectDraft(message.id)
      onEscalated()
    } catch (err) {
      fail(err)
      setBusy(null)
    }
  }

  async function onSend() {
    setBusy('send')
    setError(null)
    try {
      await messagesApi.sendReply(message.id)
      onChanged()
    } catch (err) {
      fail(err)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
          Draft reply
        </p>
        {isReviewed && (
          <span className="text-xs font-medium text-emerald-700">
            Reviewed — ready to send
          </span>
        )}
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={7}
        disabled={disabled}
        className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-60"
      />

      {error && (
        <div className="mt-2">
          <FormError message={error} />
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          onClick={onRegenerate}
          disabled={disabled}
          className={SECONDARY}
        >
          {busy === 'regenerate' ? 'Regenerating…' : 'Regenerate'}
        </button>
        <button onClick={onReject} disabled={disabled} className={DANGER}>
          {busy === 'reject' ? 'Rejecting…' : 'Reject & escalate'}
        </button>
        <div className="ml-auto flex gap-2">
          {!isReviewed && (
            <button
              onClick={onApprove}
              disabled={disabled}
              className={SECONDARY}
            >
              {busy === 'approve' ? 'Approving…' : 'Approve as-is'}
            </button>
          )}
          <button onClick={onSave} disabled={disabled} className={SECONDARY}>
            {busy === 'save' ? 'Saving…' : 'Save reply'}
          </button>
          <button
            onClick={onSend}
            disabled={disabled || !isReviewed}
            className={PRIMARY}
            title={isReviewed ? undefined : 'Approve or save the reply first'}
          >
            {busy === 'send' ? 'Sending…' : 'Send reply'}
          </button>
        </div>
      </div>
    </div>
  )
}
