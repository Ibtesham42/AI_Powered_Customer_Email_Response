# Current Tasks

Active checkpoint: **Phase 4 COMPLETE** (chunks 1–4) on `feature/phase-4-rag`.
Phases 0–3 are merged to `main`. Next: merge Phase 4 to `main`, then Phase 5.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 4 Chunk 4 — done (multi-format ingestion + grounded confidence)

- URL ingestion — `POST /api/v1/data/url` fetches a page (`fetch_url_text`),
  ingested as a `doc_type=url` document.
- FAQ ingestion — `POST /api/v1/data/faq` adds a question + answer
  (`doc_type=faq`), stored as a text file and ingested.
- Retrieval-grounded confidence — `calculate_confidence` scores from the top
  chunk's cosine similarity (`rag_service.retrieve` returns scored chunks).
- `httpx` added as a dependency.

See `CHANGELOG.md` for commit-level detail.

## Phase 4 complete — chunks 1–4

pgvector schema (1), in-process ingestion (2), `company_id`-scoped retrieval
(3) — fixing the `LabData` multi-tenancy bug — and multi-format ingestion +
grounded confidence (4).

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`.
2. Merge `feature/phase-4-rag` → `main` (on the user's OK).
3. Start Phase 5.

## Next: Phase 5 — AI pipeline
*Goal: structured, memory-aware, escalation-driven generation.*
- One structured Groq call → `{intent, confidence, draft, needs_human}`
  (folds in the LLM self-rating deferred from Phase 4).
- Move the Groq model name + params into config (currently hardcoded in
  `app/llm/llm_client.py`).
- Memory injection: current Ticket verbatim + past-Ticket summaries.
- Generate a Ticket `summary` on resolve/close.
- Hallucination-reduction prompt: answer only from context, else defer.
- Escalation engine: low confidence, human request, complaint, repeated
  replies, manual reject.

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- The embedding model + Groq are heavy / need network — verify through the
  running app where practical.
