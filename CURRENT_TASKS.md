# Current Tasks

Active checkpoint: **Phase 4 chunk 1 COMPLETE** — the pgvector knowledge-base
schema is in. On `feature/phase-4-rag`; Phases 0–3 are merged to `main`.
Next: Phase 4 chunk 2.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 4 Chunk 1 — done (pgvector foundation)

- Enabled the `vector` extension; created `kb_documents` and `kb_chunks`
  (`embedding vector(768)`, HNSW cosine index) — migration `4da268d4e51a`.
- `KbDocument` / `KbChunk` models; `KbDocType` / `KbDocStatus` enums.
- `pgvector` added to `requirements.txt`. Additive — no behaviour change yet.

See `CHANGELOG.md` for commit-level detail.

## Next: Phase 4 — Chunk 2 (in-process KB ingestion into pgvector)

The write path — move KB uploads off FAISS/`subprocess` onto pgvector.

- `kb_service` — extract text → chunk → embed → store as `KbChunk` rows;
  create a `KbDocument` row tracking `status` (pending → processing →
  indexed / error).
- Embedding-model singleton — fix the per-call reload bug (`EmbeddingModel`
  is currently rebuilt every request). A process-level cached accessor.
- `/data/upload` runs ingestion **in-process** (FastAPI `BackgroundTasks`),
  not via `subprocess` to `preprocess.py` + `build_rag.py`.
- Reuse the existing extraction/cleaning logic in `app/rag/preprocess.py`
  where sensible; chunking via `app/rag/chunking.py`.
- The read path still uses FAISS until chunk 3 — retrieval is no worse than
  today (already broken by the `LabData` hardcode).

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`.
2. `git checkout feature/phase-4-rag`; confirm `alembic current` =
   `4da268d4e51a`.
3. Implement Chunk 2; commit; sync the docs.

## Remaining Phase 4 chunks
- Chunk 3 — read path: `rag_pipeline.get_rag_context` retrieves from
  `kb_chunks` scoped by `company_id`; retire FAISS and the `LabData` bug.
- Chunk 4 — multi-format ingestion (URL, FAQ) + retrieval-grounded confidence.

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- Embedding/LLM paths need the model download / Groq — heavy to run offline;
  verify through the running app where practical.
