# Frontend is a Vite + React + TypeScript SPA

The prototype's UI is the Streamlit `dashboard_app.py`, which talks to the
FastAPI backend over HTTP. Streamlit is fine for an internal admin view but is
the wrong tool for the production customer-facing SaaS UI: limited control over
layout, interaction, and routing; awkward auth/session handling; and a
server-rendered execution model that re-runs the whole script per interaction.
The earlier roadmap planned a Next.js app (Phase 7) to replace it.

Decision: build the production frontend as a **Vite + React + TypeScript**
single-page app (Tailwind for styling), served separately from the FastAPI
backend, which it consumes purely over the versioned `/api/v1` HTTP API. This
**supersedes both** the planned Streamlit dashboard-polish phase and the Next.js
phase — the frontend work collapses into one phase.

Rationale: a plain SPA keeps a clean client/server split (the backend already is
the API and the source of all business logic, tenancy, and state transitions —
the frontend renders state and calls endpoints). Vite gives a fast dev loop and
a simple build; React + TS gives typed components and an API client whose types
mirror the backend schemas. No SSR/server-component complexity is needed for an
authenticated dashboard behind a login.

Rejected:
- **Next.js** — SSR/RSC and a Node server add complexity this app does not need;
  the UI is entirely behind auth and reads from the API.
- **Keep/extend Streamlit** — not a production customer UI (see above).

Migration: build the React app in `frontend/` **alongside** the working
Streamlit dashboard; never break the running app. Cut over and retire
`dashboard_app.py` only once React reaches parity (auth, review queue, KB,
mailbox, analytics). In dev the SPA reaches the backend through Vite's proxy
(same-origin, no CORS); a production CORS/serving decision is deferred to
cut-over.
