# Current Tasks

Active checkpoint: **Phase 5 chunk 2 done** on `feature/phase-5-ai-pipeline`.
Phases 0–4 are merged to `main`. Context: `PROJECT_STATE.md` ·
Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 5 Chunk 2 — done (structured generation call)

- `build_structured_prompt` — one prompt (hallucination-reduction rules) asking
  for a single JSON object `{intent, confidence, needs_human, draft}`; allowed
  intents passed in so `app/` stays framework-agnostic.
- `LLMClient.generate_structured` — Groq JSON mode (`response_format=json_object`).
- `ai_service.generate_draft` returns `{reply, confidence, intent, needs_human}`;
  malformed/empty output → safe defer-to-human (confidence 0, `needs_human=True`).
- `calculate_confidence` blends retrieval similarity (0.7) + LLM self-rating
  (0.3), halved on non-answer phrases.
- `intent` persisted via worker + `/messages/{id}/regenerate`. `needs_human`
  logged now; chunk 4's escalation engine consumes it.
- Verified: helper unit tests + a live Groq JSON-mode smoke test.

See `CHANGELOG.md` for commit-level detail.

## Phase 5 — AI pipeline (chunk plan)
*Goal: structured, memory-aware, escalation-driven generation.*
1. ☑ LLM config + client hardening (model/params in config, singleton, timeout).
2. ☑ Structured Groq call → `{intent, confidence, needs_human, draft}` (JSON,
   validation + fallback) + hallucination-reduction prompt; confidence blends
   retrieval similarity + LLM self-rating.
3. ☐ Memory injection: current Ticket verbatim + past-Ticket summaries within a
   token budget; generate a Ticket `summary` on resolve/close.
4. ☐ Escalation engine: low confidence, human request, complaint, repeated
   replies, manual reject (consumes `needs_human`).

## Immediate next steps for the next session
1. Commit chunk 2 on `feature/phase-5-ai-pipeline`.
2. Start Phase 5 chunk 3 (memory injection + Ticket summaries).

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- The embedding model + Groq are heavy / need network — verify through the
  running app where practical.
