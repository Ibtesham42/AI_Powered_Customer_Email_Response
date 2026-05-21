# Use Postgres (Cloud SQL), not Firestore, for the database

The brief asked for a Google-ecosystem database — Firestore or Cloud SQL. The
existing codebase is deeply relational: SQLAlchemy ORM, foreign keys, and
multi-tenant filter/JOIN queries throughout `backend/`.

We chose **Postgres**: SQLite locally during part-time development, Google
**Cloud SQL** (managed Postgres) once hosted. This satisfies the
Google-ecosystem requirement with no application rewrite.

Firestore was rejected: adopting a document store would mean rewriting every
model and every query, which contradicts the project's working principle of
incremental, never-big-bang change.

Migration path: replace the SQLite connection string with Postgres and
introduce Alembic migrations, retiring the current `Base.metadata.create_all`
auto-create on startup.
