# Runbook — Mailbox encryption key (`MAILBOX_ENCRYPTION_KEY`)

## What this key protects

Each Company connects a support mailbox; its Gmail **App Password** is stored
**Fernet-encrypted** in `mailboxes.encrypted_credential` — plaintext never
touches the database (ADR-0002). `MAILBOX_ENCRYPTION_KEY` is the symmetric
Fernet key (AES-128-CBC + HMAC) used to encrypt and decrypt it.

**If this key is lost, every stored mailbox credential is permanently
unrecoverable** — affected Companies must reconnect their mailbox. Treat the key
as a top-tier secret, on par with `SECRET_KEY` and `DATABASE_URL`.

## Configuration

| Variable | Meaning |
| --- | --- |
| `MAILBOX_ENCRYPTION_KEY` | URL-safe base64 Fernet key (44 chars). |
| `MAILBOX_ENCRYPTION_REQUIRED` | `true` in any deployment that uses mailboxes — the API then refuses to start without a valid key. |

Generate a key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Fail-fast behaviour (enforced in code)

- **Invalid key** → the API **aborts at startup** (always), regardless of
  `MAILBOX_ENCRYPTION_REQUIRED`.
- **Missing key** → aborts at startup **only** when
  `MAILBOX_ENCRYPTION_REQUIRED=true`; otherwise it starts with mailbox features
  disabled and logs a warning.
- With no usable key, **mailbox features refuse**: `POST /mailbox/connect`
  returns **503**, and the worker's poll/send paths raise before touching
  `decrypt` (see `backend/crypto.py`, `backend/services/mailbox_service.py`).

## Backup & custody

1. **Store the key in a secrets manager** (GCP Secret Manager, AWS Secrets
   Manager, Vault) — not in a committed file. `.env` is git-ignored and is for
   local dev only.
2. Keep at least one **offline backup** (e.g. sealed in a password manager /
   org vault) held by ≥2 trusted operators.
3. Record **key custody**: who can read it, where it lives, when it was created.
4. **Never log the key.** It is not returned by any API
   (`serializers.mailbox_dict` excludes the credential entirely).

## Recovery — key is lost (no backup)

Encrypted credentials cannot be decrypted; you must re-collect them.

1. Provision a **new** `MAILBOX_ENCRYPTION_KEY` (see above) and deploy it.
2. Invalidate the now-undecryptable rows so the worker stops erroring:
   ```sql
   UPDATE mailboxes SET status = 'error';
   ```
   (Optionally clear `encrypted_credential` once you have a re-connect flow.)
3. Notify each Company Owner to **reconnect** their mailbox via
   `POST /mailbox/connect`, which re-encrypts the App Password with the new key.
4. Confirm `status = 'connected'` after each reconnect.

## Rotation — planned key change

The current design uses a single active key, so rotation is an **offline
re-encryption** (brief maintenance window). Do it when a key may be compromised
or on a routine schedule.

1. **Prepare.** Generate `NEW_KEY`. Keep the current `OLD_KEY` available. Back up
   the database.
2. **Pause writers.** Stop the worker (no polling) and put the API in
   maintenance / scale the connect route to zero, so no row is encrypted with
   the old key mid-rotation.
3. **Re-encrypt** every stored credential — decrypt with the old key, re-encrypt
   with the new key:
   ```bash
   OLD_KEY=... NEW_KEY=... python - <<'PY'
   import os
   from cryptography.fernet import Fernet
   from backend.database import SessionLocal
   from backend.models.mailbox import Mailbox

   old = Fernet(os.environ["OLD_KEY"].encode())
   new = Fernet(os.environ["NEW_KEY"].encode())
   db = SessionLocal()
   try:
       n = 0
       for mb in db.query(Mailbox).all():
           mb.encrypted_credential = new.encrypt(old.decrypt(bytes(mb.encrypted_credential)))
           n += 1
       db.commit()
       print(f"re-encrypted {n} mailbox credential(s)")
   finally:
       db.close()
   PY
   ```
4. **Swap the key.** Set `MAILBOX_ENCRYPTION_KEY=NEW_KEY` in the secrets manager
   and redeploy / restart the API and worker.
5. **Verify.** The startup self-check logs "key present and valid"; spot-check a
   poll/send, or reconnect one mailbox. Confirm no `decrypt` errors in logs.
6. **Retire `OLD_KEY`** from active config; keep it in the offline backup until
   step 5 is confirmed across all instances, then destroy it.

> Future enhancement (not yet implemented): support a comma-separated key list
> via `MultiFernet` (new key first for encrypt, all keys for decrypt) for
> zero-downtime rotation without a maintenance window.

## Verification checklist

- [ ] `MAILBOX_ENCRYPTION_REQUIRED=true` in staging/production.
- [ ] Key stored in a secrets manager + an offline backup held by ≥2 people.
- [ ] Startup logs "Mailbox encryption key present and valid."
- [ ] A test `POST /mailbox/connect` succeeds; the stored row is ciphertext.
