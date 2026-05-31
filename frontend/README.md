# Frontend — Agent Console (Vite + React + TypeScript)

The production UI for the AI Customer Support SaaS (see `../docs/adr/0004-vite-react-frontend.md`).
Built **alongside** the legacy Streamlit `dashboard_app.py`; it will replace it
at feature parity. Holds no business logic — it renders state and calls the
backend `/api/v1` HTTP API.

## Stack

Vite 5 · React 18 · TypeScript (strict) · Tailwind CSS v4 · ESLint · Prettier.

## Develop

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

The dev server **proxies** `/api` and `/health` to the FastAPI backend at
`http://127.0.0.1:8000` (see `vite.config.ts`), so the browser sees one origin
and no CORS is needed. Run the backend separately from the repo root:

```bash
uvicorn backend.main:app --reload
```

The landing page shows a backend-connectivity badge driven by `/health`.

## Scripts

| Command                           | Purpose                                                |
| --------------------------------- | ------------------------------------------------------ |
| `npm run dev`                     | Dev server with HMR + backend proxy                    |
| `npm run build`                   | Type-check (`tsc -b`) then production build to `dist/` |
| `npm run preview`                 | Serve the production build locally                     |
| `npm run lint`                    | ESLint                                                 |
| `npm run format` / `format:check` | Prettier write / check                                 |

## Production build & deploy

```bash
npm run build      # → dist/ (static assets)
```

Serve `dist/` from any static host/CDN, with a SPA fallback that rewrites
unknown paths to `index.html` (client-side routing). Two ways to reach the API:

- **Same origin** (recommended): put the API and the static SPA behind one
  domain (reverse proxy `/api` + `/health` to the backend). Requests stay
  relative — no CORS, nothing to configure.
- **Separate origin**: set `VITE_API_BASE_URL` to the API origin at build time
  (see `.env.example`), and add that SPA origin to the backend's
  `CORS_ORIGINS`.
