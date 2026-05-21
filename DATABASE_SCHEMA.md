# Database Schema

Target schema. Engine: **Postgres** (SQLite locally until Phase 1, Cloud SQL
in production — ADR-0001). Vector storage via the **pgvector** extension
(ADR-0003). Managed with **Alembic** migrations.

Conventions:
- Every tenant-owned table has a non-null `company_id` FK. Every query filters
  on it.
- Timestamps `created_at` / `updated_at` are `timestamptz`, default `now()`.
- Enums are Postgres native enum types.
- Soft-sensitive columns (credentials, token hashes) never store plaintext.

## Enums

```
user_role        : owner | agent
mailbox_provider : gmail_app_password            (future: gmail_oauth)
mailbox_status   : connected | error
ticket_status    : open | pending | resolved | closed
intent           : product_inquiry | damaged_delivery | refund_request
                 | service_inquiry | complaint | general_support
message_direction: inbound | outbound
review_status    : awaiting_ai | drafted | reviewed | sent | not_applicable
kb_doc_type      : pdf | docx | csv | txt | url | faq
kb_doc_status    : uploaded | processing | indexed | failed
```

## Tables

### companies
The tenant. Holds the business address from signup.

| column | type | notes |
|---|---|---|
| id | bigint PK | |
| name | text not null | not unique — Companies are distinct by id |
| address_line | text | |
| city | text | |
| state | text | |
| country | text | |
| postal_code | text | |
| created_at / updated_at | timestamptz | |

### users
Staff with a login. The signup form's personal fields.

| column | type | notes |
|---|---|---|
| id | bigint PK | |
| company_id | bigint FK → companies | not null |
| full_name | text not null | |
| email | text not null | unique (global) |
| phone | text | |
| password_hash | text not null | bcrypt |
| role | user_role | default `agent`; the signup creator is `owner` |
| created_at / updated_at | timestamptz | |

Index: `users(email)` unique, `users(company_id)`.

### refresh_tokens
Revocable refresh tokens — one row per issued session.

| column | type | notes |
|---|---|---|
| id | bigint PK | |
| user_id | bigint FK → users | not null |
| token_hash | text not null | SHA-256 of the token; raw never stored |
| expires_at | timestamptz | not null |
| revoked_at | timestamptz | null = active |
| user_agent / ip_address | text | optional, for session listing |
| created_at | timestamptz | |

Index: `refresh_tokens(token_hash)`, `refresh_tokens(user_id)`.

### password_reset_tokens
Single-use, time-limited reset tokens.

| column | type | notes |
|---|---|---|
| id | bigint PK | |
| user_id | bigint FK → users | not null |
| token_hash | text not null | |
| expires_at | timestamptz | short (e.g. 30 min) |
| used_at | timestamptz | null = unused |
| created_at | timestamptz | |

### mailboxes
One support mailbox per Company (v1). App Password encrypted at rest.

| column | type | notes |
|---|---|---|
| id | bigint PK | |
| company_id | bigint FK → companies | unique — one per Company |
| email_address | text not null | |
| provider | mailbox_provider | |
| encrypted_credential | bytea not null | Fernet-encrypted App Password |
| imap_host / smtp_host | text | default Gmail hosts |
| status | mailbox_status | |
| last_polled_at | timestamptz | |
| created_at / updated_at | timestamptz | |

### customers
The end people emailing in. Scoped per Company.

| column | type | notes |
|---|---|---|
| id | bigint PK | |
| company_id | bigint FK → companies | not null |
| email | text not null | |
| name | text | parsed from email when available |
| created_at / updated_at | timestamptz | |

Unique: `customers(company_id, email)`.

### tickets
One support case = one email thread.

| column | type | notes |
|---|---|---|
| id | bigint PK | |
| company_id | bigint FK → companies | not null |
| customer_id | bigint FK → customers | not null |
| subject | text | |
| thread_id | text | email thread identifier |
| status | ticket_status | default `open` |
| escalated | boolean | default false |
| escalation_reason | text | e.g. low_confidence, complaint |
| intent | intent | latest detected intent |
| assigned_to | bigint FK → users | nullable |
| summary | text | generated on close — feeds Memory |
| created_at / updated_at | timestamptz | |
| resolved_at / closed_at | timestamptz | nullable |

Unique: `tickets(company_id, thread_id)`. Index: `tickets(customer_id)`,
`tickets(company_id, status)`.

### messages
Each individual email. The DB-backed AI queue = rows where
`review_status = awaiting_ai`.

| column | type | notes |
|---|---|---|
| id | bigint PK | |
| company_id | bigint FK → companies | not null (denormalised) |
| ticket_id | bigint FK → tickets | not null |
| direction | message_direction | |
| sender_email / recipient_email | text | |
| subject | text | |
| body | text | |
| message_id | text | email `Message-ID` header |
| in_reply_to | text | email `In-Reply-To` header |
| review_status | review_status | inbound-needing-reply only |
| intent | intent | nullable |
| confidence | smallint | 0–100, nullable |
| ai_draft | text | the Draft, nullable |
| final_reply | text | human-edited text actually sent |
| reviewed_by | bigint FK → users | nullable |
| created_at | timestamptz | |
| sent_at | timestamptz | nullable |

Index: `messages(ticket_id)`, partial index on
`messages(company_id) WHERE review_status = 'awaiting_ai'` (the queue).

### kb_documents
Uploaded knowledge-base sources.

| column | type | notes |
|---|---|---|
| id | bigint PK | |
| company_id | bigint FK → companies | not null |
| filename | text | |
| doc_type | kb_doc_type | |
| source_uri | text | file path or URL |
| status | kb_doc_status | |
| error | text | nullable |
| created_at / indexed_at | timestamptz | |

### kb_chunks
Chunked text + embeddings. The RAG retrieval target.

| column | type | notes |
|---|---|---|
| id | bigint PK | |
| company_id | bigint FK → companies | not null |
| document_id | bigint FK → kb_documents | not null |
| chunk_index | int | order within document |
| content | text not null | |
| embedding | vector(768) | pgvector — dim must match the model (BGE-base = 768) |
| created_at | timestamptz | |

Index: `kb_chunks(company_id)`; an HNSW (or IVFFlat) index on `embedding`.
Retrieval always filters `company_id` first, then orders by vector distance.

### audit_logs
Security-relevant actions.

| column | type | notes |
|---|---|---|
| id | bigint PK | |
| company_id | bigint FK | nullable (pre-signup events) |
| user_id | bigint FK | nullable |
| action | text not null | e.g. `login`, `mailbox.connect`, `email.send` |
| entity_type / entity_id | text / bigint | |
| metadata | jsonb | |
| ip_address | text | |
| created_at | timestamptz | |

## Migration from the current schema

The current `emails` table conflates Ticket and Message. Phase 2 migration:
1. Create `customers`, `tickets`, `messages`.
2. For each old `emails` row: upsert a Customer from `sender`; create/find a
   Ticket by `thread_id`; insert a Message carrying `body`, `ai_reply` →
   `ai_draft`, `final_reply`, `confidence`, mapped `status` → `review_status`.
3. Drop `emails` once verified.
