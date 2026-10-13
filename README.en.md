# Suixin Shop (随心商城)

A full-stack e-commerce demo: **FastAPI + MySQL backend**, an admin console (`manager/`) and a storefront (`front/`) built with vanilla HTML/CSS/JS. The project was built with heavy AI assistance and is released under the [MIT License](./LICENSE).

> **Disclaimer**
> This is a learning / demo project. All brand names, product names, copy and images in this repository are fictional placeholders used only to demonstrate the system. They are not affiliated with, endorsed by, or related to any real brand or manufacturer. All product images are self-drawn SVG placeholders — no third-party copyrighted material is included. The site logo was drafted by the project author and produced with AI tooling; **to the best of the author's knowledge** it contains no third-party trademark or protected artwork (AI-generated content raises open copyright questions in many jurisdictions, and this project claims no exclusive rights over it). If you believe any content infringes your rights, please open an issue and it will be removed. Product names and model numbers are fictional; any resemblance to real product model numbers is coincidental and implies no affiliation.

<p align="center"><img src="front/images/logo.png" alt="Suixin Shop" width="120"></p>

## Highlights

- Backend: Python 3.10+, FastAPI, uvicorn, aiomysql (fully async), JWT + bcrypt, RBAC with permission codes
- Frontend: zero build step — native HTML/CSS/JS, 18 storefront pages + 28 admin pages
- Data: idempotent seed scripts (`base` / `demo`), decoupled from business code
- Tests: pytest suite covering RBAC, goods, orders, members, storefront flows, seed and live version fingerprint

## Architecture

| Layer | Port | Description |
|---|---|---|
| Backend API + admin console (`manager/`) | 8001 | FastAPI serves `/api/v1/*` and hosts `manager/` static pages; `/` redirects to `/manager/login.html` |
| Storefront (`front/`) | 8000 | Pure static site, calls `/api/v1/shop/*` cross-origin |

## Quick start

> Want to modify the project for your own needs? Read **[docs/开发指南.md](./docs/开发指南.md)** (Chinese) — architecture overview, conventions, step-by-step "add an endpoint / add a table / add a page" recipes and a checklist of traps. For pull requests see [CONTRIBUTING.md](./CONTRIBUTING.md).

Requirements: **Python 3.10+** and a reachable **MySQL 5.7+** (8.0 recommended). Keep the project path free of spaces and non-ASCII characters.

### 1. Database (pick one)

**Option A — Docker (easiest).** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), start it, then in the repository root:

```bash
docker compose up -d                      # MySQL 8, root / DEV_ONLY_123456, database aaashop
docker compose ps                         # wait until the state shows "healthy" (~30s after first start)
```

Use `DB_PASSWORD=DEV_ONLY_123456` in `.env` with this option. Tear down with `docker compose down` (add `-v` to also drop the data).

**Option B — local MySQL.** Install MySQL 8 and make sure the service is running (`brew services start mysql` / `sudo systemctl start mysql` / Windows Services). Leave `DB_PASSWORD` empty if your local `root` has no password.

> The database is created automatically — no manual `CREATE DATABASE` needed (see section 2).

### 2. Backend

Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`):

```bash
# Windows (PowerShell):  irm https://astral.sh/uv/install.ps1 | iex
# macOS / Linux:         curl -LsSf https://astral.sh/uv/install.sh | sh
pip install uv              # alternative installer
cd backend
uv sync                     # create .venv and install everything (including the dev group)
uv add <pkg>                # add a runtime dependency (uv add --dev for dev-only)
cp .env.example .env        # then fill in your own values
python -c "import secrets;print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET
```

Without uv, use pip instead (`requirements.txt` mirrors the same dependency set):

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements.txt     # Windows
# ./.venv/bin/python -m pip install -r requirements.txt       # macOS / Linux
```

### 3. Seed data

```bash
cd backend
uv run python -m seed.runner base     # schema + base data (roles, permissions, admin user, express, levels, configs)
uv run python -m seed.runner demo     # demo data (20 goods, 24 SKUs, 18 orders, members, reviews, coupons, ...)
```

Both create the database first (`CREATE DATABASE IF NOT EXISTS`, utf8mb4 / utf8mb4_general_ci), so no manual step is needed. MySQL < 5.7 is rejected with a readable message instead of a SQL syntax error. If the DB account lacks the CREATE privilege, the seed prints the statement to run yourself.

Both commands are idempotent: re-running only fills in what is missing. Use `clean-base` / `clean-demo` to wipe a set first. Running `python -m seed.runner` without an argument defaults to `base`.

> Run **both** — `demo` is required: without it the storefront renders empty and pytest fails.

The admin password is generated for you: leave `ADMIN_INIT_PASSWORD` empty in `.env` and the first `seed base` run prints a random one to the terminal (no usable password ships in this repo). To pin your own, set the variable before seeding. **Change it before any public deployment.**

### 4. Run

```bash
cd backend && uv run python run.py        # API + admin console on http://127.0.0.1:8001
cd front  && python -m http.server 8000   # storefront on http://127.0.0.1:8000
```

> Starting from inside `backend/` is recommended — the admin console directory is resolved from the repo root (so other directories also work), but `run.py` must be importable.

- Swagger docs: http://127.0.0.1:8001/api/docs
- Health check: http://127.0.0.1:8001/api/v1/health — `"db":"up"` means the database is connected

**Done?** You passed if: `http://127.0.0.1:8001` redirects to the login page, `admin` plus the password printed by `seed base` logs in, health shows `"db":"up"`, and `http://127.0.0.1:8000/` shows products.

If the ports are taken, change `PORT` in `backend/.env` and the `http.server` argument, then also update `CORS_ORIGINS`, re-run `seed clean-demo` + `demo` (image URLs embed the port), and set `localStorage.setItem('shop_api_base','http://127.0.0.1:<port>/api/v1')` in the browser console when the backend is not on 8001.

### 5. Tests

```bash
cd backend && uv run pytest -q tests     # requires a reachable MySQL + `seed base` AND `seed demo`
```

Some cases assert demo data scale (goods ≥ 20, orders ≥ 15, members ≥ 6) and depend on a fixed coupon id, so **running `base` only will fail**. Tests hit the real `DB_NAME` database (no separate test DB, no rollback) and leave data behind.

Current suite: **84 passed** (RBAC, goods/category/brand CRUD, members, orders, dashboard, upload, timezone, storefront flows, seed demo data, live fingerprint, static hosting and root redirect, SMS code randomness and universal-code regressions, ...). See `backend/tests/`.

### Environment variables

Copy `.env.example` to `.env` and adjust. The repository contains **no real secrets**; `.env` is git-ignored.

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` / `DB_PORT` | `127.0.0.1` / `3306` | MySQL address |
| `DB_USER` / `DB_PASSWORD` | `root` / *empty* | Database credentials — leave the password empty if local `root` has none; set it only if your MySQL requires one |
| `DB_NAME` | `aaashop` | Database name (created automatically by the seed) |
| `JWT_SECRET` | **required, no default** | JWT signing key; the service refuses to start without it |
| `MEMBER_JWT_SECRET` | empty (falls back to `JWT_SECRET`) | Separate key for storefront tokens |
| `JWT_EXPIRE_MINUTES` | `120` | Token lifetime |
| `SMS_MOCK` | `false` | Demo SMS channel. `true` = no real SMS is sent: the code is random, BCrypt-hashed into `sms_codes`, and echoed back in the `devCode` response field. `false` = channel unavailable (no SMS provider SDK ships here), so registration is disabled too. A fixed `123456` used to be accepted; that is gone |
| `ADMIN_INIT_PASSWORD` | empty (random) | Password for the `admin` account; `seed base` applies it every run (idempotent), not just on first creation. Leaving it empty prints a random one — no usable password ships in the repo. Set it consistently before running pytest |
| `GOODS_AUDIT_ENABLED` | `false` | New-product review workflow switch |
| `DB_POOL_MIN` / `DB_POOL_MAX` | `2` / `10` | Pool size; raise `DB_POOL_MAX` if requests hang under concurrency (must stay below MySQL `max_connections`) |
| `CORS_ORIGINS` | `http://127.0.0.1:8000,http://127.0.0.1:8001,http://localhost:8000,http://localhost:8001` | Cross-origin allow-list; **never use `*`** |
| `UPLOAD_PUBLIC_BASE` | empty (derived from request host) | Public URL prefix for uploaded files behind a proxy/HTTPS domain |
| `PORT` | `8001` | Backend listen port |
| `RELOAD` | `0` | Set to `1` to enable uvicorn auto-reload |
| `STATIC_MANAGER_DIR` | repo-root `manager/` | Admin console directory hosted by the backend (resolved automatically; set an absolute path only if you must) |

## Default accounts

| Side | Account | Password |
|---|---|---|
| Admin console | `admin` | Random — printed once by `seed base` (pin your own via `ADMIN_INIT_PASSWORD`) |
| Storefront demo members | `10000000001` ~ `10000000003` | `123456` |
| Storefront registration code | any phone | Random 6 digits; echoed on screen while `SMS_MOCK=true` (no real SMS is sent) |

## Security notes

Do **not** deploy this project as-is. Before any public deployment:

1. Set a strong random `JWT_SECRET` (the service refuses to start without it)
2. Change the database password and the admin password
3. Implement a real SMS provider — this repo ships none. With `SMS_MOCK=true` the code is echoed to the caller, which is fine for local demos only
4. Restrict `CORS_ORIGINS` to trusted origins (never `*`)

## Built with AI (vibe coding)

This project is a **vibe coding** sample: requirements live in `specs/*.spec.md` as the single
source of truth, AI generates code and documentation drafts, and a human owns architecture
decisions, security review and compliance cleanup.

**What AI did**
- Generated backend `routers` / `services` / `schemas` and frontend page scripts against the `specs/` contract
- Wrote pytest regression cases and first drafts of the documentation
- Generated the product placeholder SVG images

**What a human owned (not delegated to AI)**
- Security pass: fixed admin privilege-escalation paths, removed the fixed-SMS-code backdoor,
  pushed horizontal authorization down to single-row reads/writes
- Test honesty: removed empty / tautological test cases
- Precision: consolidated money math into `core/money.py` with quantisation to cents
- Compliance: removed real-brand references, fabricated claims and dead links

**Limits**: no load testing, no real payment or SMS gateway — **not production ready** (see Known limitations).

## Known limitations

This is a demo project and is **not production ready**:

| Limitation | Detail |
|---|---|
| Money precision | Amounts are quantised to cents in `core/money.py` (`Decimal` + `ROUND_HALF_UP`) and persisted in `DECIMAL(10,2)` columns; the JSON API still emits `float` for frontend compatibility |
| Stock concurrency | SKU stock uses a conditional decrement (`UPDATE ... WHERE stock >= N` in one statement, so concurrent orders cannot oversell a SKU); the goods-level total uses `GREATEST(stock-N,0)` only as a safety floor |
| SMS | Mocked; no real gateway. With `SMS_MOCK=true` a random 6-digit code is generated, BCrypt-hashed into `sms_codes` and echoed back — no fixed/universal code exists |
| Payment | WeChat / Alipay flows are simulated only |
| Database | MySQL only (aiomysql); there is no offline SQLite mode and pytest needs a real MySQL |
| Data scope | Row-level data isolation (`data_scope`) is enforced in the goods module and the admin account list only; other modules rely on permission codes without row filtering — see the Chinese README for the full model notes |
| Idempotency token | The checkout `previewToken` lives in a **process-memory** dict: fine for a single instance, but all tokens are lost on restart and multiple replicas do not share them (use Redis in production) |
| Static hosting | `/manager` and `/uploads` are served without authentication; put them behind Nginx with access control |
| Product media | Self-drawn SVG placeholders, not real product photos |

## Project layout

```
backend/    FastAPI app (app/), seed (seed/), pytest (tests/)
manager/    Admin console static pages (served by the backend)
front/      Storefront static pages
specs/      Requirement specs (single source of truth)
docs/       Project variables and front-end logic design notes
```

## Documentation

| Document | Content |
|---|---|
| [操作手册.md](./操作手册.md) | Chinese operation manual: startup, URLs, login/logout, page-by-page features, FAQ |
| [README.md](./README.md) | Chinese README — the most complete version |
| `specs/商城后台管理系统V2.spec.md` | Admin console contract: APIs, schema, RBAC, metric definitions (Chinese) |
| `specs/商城前台V1.2.spec.md` | Storefront pages and API contract (Chinese) |
| `docs/项目变量.md` | Project variables: stack, ports, branding, commands (Chinese) |
| `docs/商城前台逻辑设计说明.md` | Historical storefront design notes (Chinese; some page counts are outdated) |
| `docs/开发指南.md` | Developer pitfalls and code conventions (Chinese) |
| `后台管理系统功能.md` | Admin console requirements / planning source (Chinese) — **not** an implemented-feature list |

Spec files are the single source of truth for contracts: change the spec first, then the code.

## License

[MIT](./LICENSE) — Copyright (c) 2026 shop-open contributors
