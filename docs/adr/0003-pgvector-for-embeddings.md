# Store vector embeddings in Postgres via pgvector

The RAG layer needs a multi-tenant vector store. The original code used
per-company FAISS index files on local disk, which had two fatal flaws: the
path was hardcoded to one shared `LabData` directory (breaking tenant
isolation), and local-disk indexes cannot survive horizontally-scaled or
ephemeral-disk deployments such as Cloud Run.

Decision: use the **pgvector** extension on the same Postgres database chosen
in ADR-0001. Embeddings become ordinary rows carrying a `company_id` column;
tenant isolation is a `WHERE company_id = ?` filter, identical to every other
table. No separate vector service to run, transactional with application data,
and covered by the same backup.

Rejected: managed vector databases (Pinecone, Vertex AI Vector Search) — each
adds a paid service and a second place tenant isolation can be misconfigured,
unjustified at current scale.
