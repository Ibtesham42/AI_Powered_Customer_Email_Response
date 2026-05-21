# AI / RAG Engineer

Owns the retrieval-augmented generation pipeline: ingestion, embeddings,
retrieval, prompting, intent, confidence, and memory.

## Responsibilities

- KB ingestion: extract → chunk → embed → store in pgvector.
- Retrieval: semantic search scoped to one Company.
- Generation: the structured Groq call that returns intent + confidence +
  draft.
- Memory assembly and Ticket summarisation.

## Coding standards

- `app/` modules stay framework-agnostic — no FastAPI, no request objects.
- Model name and generation params (`temperature`, `max_tokens`) come from
  config, not hardcoded in `llm_client.py`.
- Prompt templates live in dedicated, reviewable modules — not inline f-strings
  scattered across services.
- LLM output that must be structured is requested and parsed as JSON, with a
  validation + fallback path for malformed responses.

## Architecture rules

- **Retrieval is always scoped by `company_id`.** The hardcoded `LabData` path
  in `rag_pipeline.py` is a tenant-isolation defect and must be removed.
- The embedding model is loaded **once** per process. Constructing a pipeline
  per email is a defect.
- The same embedding model and dimension are used for ingestion and for query —
  never mix models.
- One structured LLM call per inbound Message produces `{intent, confidence,
  draft}` together (ADR rationale: cost + intent-before-send).

## Best practices

- Chunk with overlap; keep chunks within the embedding model's token limit.
- **Hallucination reduction**: the prompt instructs the model to answer only
  from retrieved context and to defer to a human when context is insufficient.
- **Confidence** = retrieval similarity (primary) + LLM self-rating
  (secondary) + fallback-phrase detection. Never a length heuristic.
- **Memory** = current Ticket verbatim + summaries of the Customer's past
  Tickets; keep within a token budget.
- Drafts are never auto-sent in v1 — a human reviews every one.

## Security requirements

- A Company's KB, retrieval, and memory never include another Company's data.
- Do not log full Customer email bodies or full prompts at info level.
- Treat inbound email text as untrusted; guard against prompt injection
  attempting to override system instructions.
- Cap document size and chunk count per upload.

## Performance requirements

- Batch embedding generation during ingestion.
- KB indexing runs as a background task; uploads return immediately.
- Cap retrieval `k` and prompt size to control latency and token cost.
- Cache the embedding model and the Groq client at process scope.
