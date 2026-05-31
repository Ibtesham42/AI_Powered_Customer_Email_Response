# Current Tasks

Active checkpoint: **Phase 5 chunk 3 done** on `feature/phase-5-ai-pipeline`.
Phases 0–4 are merged to `main`. Context: `PROJECT_STATE.md` ·
Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 5 Chunk 3 — done (memory injection + Ticket summaries)

- `ai_service.build_memory` — prompt input = past-Ticket summaries (budgeted to
  1500 chars) + current Ticket conversation + current email.
- `ticket_service.list_resolved_ticket_summaries` — tenant-scoped past-summary
  query (newest first, capped, excludes the current Ticket).
- `ai_service.summarize_ticket` + `build_summary_prompt` — 1-3 sentence internal
  summary, no greetings/sign-offs/sensitive data.
- `transition_ticket` generates the summary on RESOLVED/CLOSED (once,
  best-effort; LLM failure never breaks the transition).
- No migration — `tickets.summary` already exists.
- Verified: memory/budget/summary unit tests, transition-hook gating + error
  tests, and a live Groq summary smoke test.

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

See `CHANGELOG.md` for commit-level detail.

## Phase 5 — AI pipeline (chunk plan)
*Goal: structured, memory-aware, escalation-driven generation.*
1. ☑ LLM config + client hardening (model/params in config, singleton, timeout).
2. ☑ Structured Groq call → `{intent, confidence, needs_human, draft}` (JSON,
   validation + fallback) + hallucination-reduction prompt; confidence blends
   retrieval similarity + LLM self-rating.
3. ☑ Memory injection: current Ticket verbatim + past-Ticket summaries within a
   token budget; generate a Ticket `summary` on resolve/close.
4. ☐ Escalation engine: low confidence, human request, complaint, repeated
   replies, manual reject (consumes `needs_human`).

## Immediate next steps for the next session
1. Commit chunk 3 on `feature/phase-5-ai-pipeline`.
2. Start Phase 5 chunk 4 (escalation engine) — the last Phase 5 chunk.

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- The embedding model + Groq are heavy / need network — verify through the
  running app where practical.
