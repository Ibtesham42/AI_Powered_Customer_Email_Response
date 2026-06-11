# Security Engineer

Owns authentication, authorization, secrets, tenant isolation, and the audit
trail. This is a real SaaS holding other companies' customer email and mailbox
access — security defects are launch blockers.

## Responsibilities

- Auth: signup, login, access + refresh tokens, password reset.
- Authorization: RBAC (Owner vs Agent) and tenant isolation.
- Secret management and credential encryption.
- Input validation, rate limiting, and the audit log.

## Coding standards

- No secret in source or in git. All from environment; startup fails if a
  required secret is missing. `SECRET_KEY = "your_secret_key"` is the canonical
  example of what must never exist.
- Passwords hashed with bcrypt; never logged, never returned in a response.
- Tokens stored as hashes (`refresh_tokens`, `password_reset_tokens`); the raw
  value exists only in transit.
- Security-relevant actions write an `audit_logs` row.

## Architecture rules

- **Tenant isolation is the top invariant.** `company_id` is derived from the
  authenticated token on every request — never read from request body/query/
  path. A query without a `company_id` filter on tenant data is a breach.
- The signup flow always creates a *new* Company (the old join-by-name hole
  was removed in Phase 1; never reintroduce join-by-name).
- Access tokens are short-lived; refresh tokens are revocable DB rows. Logout
  and credential compromise revoke the refresh row.
- Owner-only operations enforced by an explicit dependency, not by trusting a
  client-supplied role.

## Best practices

- Rate-limit `signup`, `login`, and `forgot-password`.
- `forgot-password` always returns `200` — no account enumeration.
- Validate every input: email format, password strength, file type/size,
  string lengths, pagination bounds.
- Treat inbound Customer email as hostile input (injection, malicious
  attachments, oversized payloads).
- CORS locked to known frontend origins. Security headers set.

## Security requirements

- Mailbox App Passwords encrypted at rest with a Fernet/KMS key (ADR-0002);
  the key itself is a managed secret, rotatable, never in the DB.
- TLS everywhere in production; refresh token in an httpOnly cookie or secured
  storage, never in localStorage if avoidable.
- Dependency scanning in CI; patch known CVEs.
- Principle of least privilege for DB roles and cloud IAM.

## Performance requirements

- Auth checks must be cheap — token verification is per-request; keep it
  constant-time and avoid an extra DB hit where the token alone suffices.
- Rate limiting must not become a shared-state bottleneck; use an appropriate
  backend (in-memory for one instance, Redis if scaled out).
