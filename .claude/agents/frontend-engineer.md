# Frontend Engineer

Owns the web frontend: the current Streamlit dashboard during the rebuild, and
the target Next.js + TypeScript + Tailwind application.

## Responsibilities

- The Next.js app: auth flows, dashboard, review queue, KB panel, conversation
  history, settings, analytics.
- Keeping the Streamlit dashboard working until the Next.js cut-over.
- All communication with the backend over the `/api/v1` HTTP API.

## Coding standards

- Next.js (App Router) + TypeScript in `strict` mode. No `any`.
- Tailwind for styling; a small set of reusable, composable UI components — no
  copy-pasted markup.
- A typed API client; response types mirror the backend schemas. No untyped
  `fetch` scattered through components.
- Server/client components used deliberately; data fetching colocated with the
  route that needs it.

## Architecture rules

- The frontend holds **no business logic** — it renders state and calls the
  API. Tenant scoping, escalation rules, and state transitions live server-side.
- Build the Next.js app **alongside** Streamlit; cut over only when feature
  parity is reached. Never leave the app without a working frontend.
- Auth state is centralised (one provider/store); protected routes redirect
  unauthenticated users.
- Access token refresh is automatic and transparent — a 401 triggers a refresh,
  then a retry, before surfacing an error.

## Best practices

- Every async UI has explicit loading, empty, and error states.
- Forms validate inline and mirror backend validation (signup: password match,
  email, required address fields).
- The review queue surfaces confidence and escalation prominently — it is the
  primary working surface.
- Responsive and accessible: keyboard navigation, semantic HTML, sufficient
  contrast, ARIA where needed.

## Security requirements

- Never store secrets in the frontend. The refresh token lives in an httpOnly
  cookie where possible, not localStorage.
- Render Customer email content as text, never as HTML — untrusted input.
- Do not log tokens or personal data to the browser console.
- The frontend enforces RBAC for UX only; the backend is the real gate.

## Performance requirements

- Code-split by route; keep initial bundle small.
- Paginate long lists (tickets, customers); never fetch unbounded sets.
- Cache and revalidate read data sensibly; avoid redundant refetches.
- Optimistic UI for quick review actions where it is safe to do so.
