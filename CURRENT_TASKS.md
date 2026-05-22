# Current Tasks

Active checkpoint: **Phase 4 chunk 3 COMPLETE** — backend RAG retrieval runs
on pgvector, scoped by `company_id`. The `LabData` multi-tenancy bug is fixed.
On `feature/phase-4-rag`; Phases 0–3 are merged to `main`. Next: Phase 4
chunk 4 (the last Phase 4 chunk).
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 4 Chunk 3 — done (retrieval from pgvector)

- `backend/services/rag_service.py` — `get_rag_context(db, query, company_id)`
  embeds the query and retrieves the nearest `kb_chunks` filtered by
  `company_id`, by cosine distance.
- `ai_service.generate_draft` retrieves via `rag_service`, not the legacy
  FAISS `rag_pipeline.py`.
- `EmbeddingModel.embed_query()`; retrieval uses the `get_embedding_model()`
  singleton (no more per-email reload).
- FAISS modules kept as the legacy single-tenant path (standalone apps,
  retired in Phase 7).

See `CHANGELOG.md` for commit-level detail.

## Next: Phase 4 — Chunk 4 (multi-format ingestion + grounded confidence)

The last Phase 4 chunk.

- **URL ingestion** — fetch a web page, extract readable text, ingest as a
  `KbDocument` (`doc_type=url`). Needs a new entry point (not a file upload),
  e.g. `POST /api/v1/data/url`.
- **FAQ ingestion** — add a question+answer entry directly (`doc_type=faq`),
  e.g. `POST /api/v1/data/faq`. No file; the Q+A text is the content.
- **Retrieval-grounded confidence** — replace the keyword heuristic in
  `ai_service.calculate_confidence` with retrieval similarity (cosine score
  of the top chunks) plus the LLM's self-rating.
- File formats PDF/DOCX/CSV/TXT/JSON already work (chunk 2).

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`.
2. `git checkout feature/phase-4-rag`; confirm `alembic current` =
   `4da268d4e51a`.
3. Implement Chunk 4; commit; sync the docs.
4. After chunk 4: Phase 4 is complete — merge `feature/phase-4-rag` → `main`
   (on the user's OK).

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- The embedding model + Groq are heavy/need network — verify through the
  running app where practical.
