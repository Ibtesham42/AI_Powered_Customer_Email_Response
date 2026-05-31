# Current Tasks

Active checkpoint: **Phase 5 chunk 1 done** on `feature/phase-5-ai-pipeline`.
Phases 0–4 are merged to `main`. Context: `PROJECT_STATE.md` ·
Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 5 Chunk 1 — done (LLM config + client hardening)

- Groq model name + generation params moved from the hardcoded
  `app/llm/llm_client.py` into `app/utils/config.py` (`MODEL_NAME`,
  `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT`), env-overridable.
- `LLMClient` reads them and applies a Groq request `timeout`.
- `get_llm_client()` process-level singleton; `ai_service.generate_draft`
  uses it instead of constructing `LLMClient()` per email. No draft-content
  change.
- `.env.example` documents the new tuning vars; CLAUDE.md gotcha updated.

See `CHANGELOG.md` for commit-level detail.

## Phase 5 — AI pipeline (chunk plan)
*Goal: structured, memory-aware, escalation-driven generation.*
1. ☑ LLM config + client hardening (model/params in config, singleton, timeout).
2. ☐ Structured Groq call → `{intent, confidence, draft, needs_human}` (JSON,
   validation + fallback) + hallucination-reduction prompt; confidence blends
   retrieval similarity + LLM self-rating.
3. ☐ Memory injection: current Ticket verbatim + past-Ticket summaries within a
   token budget; generate a Ticket `summary` on resolve/close.
4. ☐ Escalation engine: low confidence, human request, complaint, repeated
   replies, manual reject.

## Immediate next steps for the next session
1. Commit chunk 1 on `feature/phase-5-ai-pipeline`.
2. Start Phase 5 chunk 2 (structured generation call).

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- The embedding model + Groq are heavy / need network — verify through the
  running app where practical.
