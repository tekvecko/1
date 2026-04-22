# FINAL Lunch Platform — modular v2 foundation

This package is a modularized follow-up to the hardened v2 single-file build.
It splits the app into:

- `auth`
- `orders`
- `admin`
- `billing`
- `imports`
- `core`
- `services`
- `tests`

## Run

```bash
export FLASK_ENV=development
export SECRET_KEY="replace-me-with-a-strong-key-in-production"
python app.py
```

## Test

```bash
pytest -q
```

## Notes

- Keeps the trust model server-side: session identity, CSRF, role checks.
- Uses numeric prices (`price_cents`) as source of truth.
- Preserves a compatible schema for accounts, menu, orders, audit, ratings, users.
- Includes a navy UI pass that ports the original visual language into modular Jinja templates and static assets while keeping the v2 auth/RBAC/testable architecture.

- Import pipeline now uses a preview step before DB write: recognized days, skipped lines, missing prices, suspicious rows, and a diff against the current menu.
