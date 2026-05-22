# Current Tasks

Active checkpoint: **Phase 4 chunk 2 COMPLETE** — KB uploads index in-process
into pgvector. On `feature/phase-4-rag`; Phases 0–3 are merged to `main`.
Next: Phase 4 chunk 3.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 4 Chunk 2 — done (in-process KB ingestion into pgvector)

- `app/rag/extract.py` — plain-text extraction (PDF/DOCX/TXT/CSV/JSON).
- `backend/services/kb_service.py` — `create_document` + `ingest_document`
  (background task: extract → chunk → embed → store `KbChunk` rows; tracks
  `KbDocument.status`).
- `app/rag/embeddings.py` — `get_embedding_model()` singleton +
  `embed_documents()`.
- `POST /api/v1/data/upload` indexes in-process (FastAPI `BackgroundTasks`),
  no `subprocess`. New `GET /api/v1/data/documents`.

See `CHANGELOG.md` for commit-level detail.

## Next: Phase 4 — Chunk 3 (retrieval from pgvector)

The read path — the chunk that fixes the multi-tenancy break.

- Rewrite `app/rag/get_rag_context(query, company_id)` to embed the query
  (`get_embedding_model().embed_query(...)`) and retrieve the top-k
  `KbChunk` rows **filtered by `company_id`**, ordered by
  `embedding.cosine_distance(...)`.
- Add `embed_query()` to `EmbeddingModel` (returns a plain list).
- This needs a DB session — decide how `get_rag_context` gets one (it is
  called from `ai_service.generate_draft`, which already has `db`). Likely:
  pass `db` through, or have it open its own `SessionLocal`.
- Retire FAISS: delete `app/rag/rag_pipeline.py`'s FAISS code,
  `vector_store.py`, `retriever.py`, the hardcoded `LabData` path, and
  `scripts/build_rag.py` / `app/rag/preprocess.py` if nothing else uses them.
- Update `CLAUDE.md` (the `rag_pipeline.py` `LabData` gotcha) and
  `PROJECT_STATE.md` tech debt once the bug is gone.

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`.
2. `git checkout feature/phase-4-rag`; confirm `alembic current` =
   `4da268d4e51a`.
3. Implement Chunk 3; commit; sync the docs.

## Remaining Phase 4 chunks
- Chunk 4 — multi-format ingestion (URL, FAQ) + retrieval-grounded confidence.

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- The embedding model + Groq are heavy/needs-network — verify through the
  running app where practical.
