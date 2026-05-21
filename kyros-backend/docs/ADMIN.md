# Kyros Admin Panel

Server-rendered HTML admin panel at `/admin/`. Single-user, HTTP Basic Auth, intentionally boring.

---

## Setting the admin password

Generate a bcrypt hash and write it to `.env`. Never put a plaintext password in the env file.

```bash
poetry run python -m app.admin.cli set-password
# Prompts for a password, prints:
# ADMIN_PASSWORD_HASH=$2b$12$...
```

Add the printed hash to `.env`:

```
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$...
```

Restart the server. The change takes effect immediately on the next request.

---

## URL

- **Local dev:** http://localhost:8000/admin/
- **Production:** https://api.kyros.clinic/admin/ (once Caddy is configured)

---

## Write actions available in Phase 1

| Action | URL | Confirmation phrase |
|--------|-----|---------------------|
| Discontinue a tracked item | `POST /admin/items/{id}/discontinue` | `DISCONTINUE` |
| Toggle a reminder active/paused | `POST /admin/reminders/{id}/toggle` | `TOGGLE` |
| Update a consultation (status, meeting link, notes) | `POST /admin/consultations/{id}/status` | `UPDATE` |

Every write action requires typing the exact confirmation phrase. All write actions (and sensitive reads like user detail and consultation detail) write a row to `audit_log` with `actor_type='admin'`.

---

## Audit log

- **Retention:** forever in Phase 1. No purge job.
- **What's logged:** all admin writes + reads of user detail pages and consultation detail pages.
- **What's NOT logged:** dashboard loads, list pages, the audit log viewer itself.
- **PHI in logs:** structlog output is always PHI-redacted (`notes`, `payload`, `metadata`, `dose`, `lab_value`, `result` → `[REDACTED]`). The database `audit_log.payload` column retains the unredacted data for legal traceability.

---

## Adding a second admin (Phase 1.5 preview)

In Phase 1.5 the auth flow will switch from env-var credentials to `users.role = 'superadmin'` lookup + OTP or session-based auth. The `role` column is already on the `users` table with a check constraint allowing `'user'` and `'superadmin'`.

Until then, if you need two admins, there is one option: share the single `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH` credentials, or SSH into the EC2 box and change the env var.

---

## Blocked actions (won't be added to admin)

- SQL console — never
- User deletion — soft-delete only; use `TrackedItem.status='discontinued'` instead
- CSV export — Phase 1.5
- User impersonation — Phase 1.5
- Prescription writing — Phase 2
