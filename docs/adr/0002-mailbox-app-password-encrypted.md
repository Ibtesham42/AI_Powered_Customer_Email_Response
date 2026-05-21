# Store mailbox credentials (App Password) encrypted at rest, not OAuth

The platform must read and send from each Company's support mailbox. The brief
specified "email + app password."

Gmail OAuth is the more secure option — revocable, scoped, no stored secret —
but Gmail is a Google "restricted scope": shipping it requires a third-party
security assessment plus consent-screen verification. That is weeks of process,
impractical for a part-time solo build, and capped at 100 users with a warning
screen until verified.

Decision: each Company stores its own mailbox address and App Password,
**encrypted at rest** with a Fernet/KMS key — never plaintext in the database.
All mailbox access goes through a "mailbox connector" abstraction so a Gmail
OAuth connector can replace the App Password connector later without changing
callers.

Consequences:
- The encryption key is now a critical secret; losing it loses all stored
  mailbox access for every Company.
- App Passwords require the Company's Google account to have 2FA enabled.
- OAuth remains the intended v2 upgrade once the platform justifies Google
  verification.
