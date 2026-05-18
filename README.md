# MDK Engineering Bot

Personal operations platform for a German software freelancer. Telegram-first,
web-augmented, Postgres-backed. **Phases 0 + 1 ship here**: the foundation
(database, FastAPI Core API, HTMX UI, structured logging, Docker Compose) and
the reminder bot (RRULE engine with Bavarian/federal holiday shifting,
APScheduler daily check, polling-mode Telegram bot).

Future phases — Lexware sync, Gmail triage, receipt RPA, voice memos, medical
billing — will layer on top without changing this foundation.

---

## Architecture

```
                ┌──────────────────────────────────────────────┐
                │                Hetzner CX32                  │
                │  (or `docker compose up` locally)            │
                └──────┬───────────────────────────┬───────────┘
                       │ Caddy (TLS, /web + /api)  │
                       │                           │
                ┌──────▼──────┐             ┌──────▼──────┐
                │  Core API   │◄────────────┤   Web UI    │
                │  (FastAPI)  │             │  (HTMX)     │
                └──────┬──────┘             └─────────────┘
                       │ INTERNAL_API_TOKEN
              ┌────────┴────────┐
              │                 │
       ┌──────▼──────┐   ┌──────▼──────┐
       │  Telegram   │   │  Scheduler  │
       │  Bot        │   │  (APSched)  │
       │  (polling)  │   │  daily 08:00│
       └─────────────┘   └─────────────┘
              │
              ▼
      ┌───────────────┐       ┌──────────┐
      │   Postgres    │       │  Redis   │
      │  + pgvector   │       │          │
      └───────────────┘       └──────────┘
```

- **Core API** is the single domain layer. Bot, scheduler, and web UI all
  go through `/api/v1/*`.
- **Bot** authenticates with `INTERNAL_API_TOKEN`; users authenticate to web
  with `WEB_SESSION_TOKEN` (signed cookie session).
- **Scheduler** runs the daily reminder check at 08:00 Europe/Berlin.
  Notifications go via a shared `Notifier` protocol (Telegram in prod,
  in-memory in tests).
- Every business mutation emits an `audit_log` entry.

## Quickstart (local development)

```bash
# 1. Clone, install Python deps via uv
make install                              # uv sync --all-groups

# 2. Configure environment
cp .env.example .env
# fill in TELEGRAM_BOT_TOKEN, AUTHORIZED_TELEGRAM_USER_ID, *_TOKEN secrets

# 3. Bring up Postgres, Redis, API, bot, scheduler
docker compose up -d

# 4. Run migrations
docker compose exec api uv run alembic upgrade head

# 5. Open the web UI
open http://localhost:8000/web/login
```

The login token is whatever you set as `WEB_SESSION_TOKEN`.

## Make targets

| Command | What it does |
|---|---|
| `make install` | `uv sync --all-groups` |
| `make lint` | ruff + mypy strict |
| `make format` | ruff format & autofix |
| `make test` | pytest (in-memory SQLite) |
| `make test-cov` | pytest with HTML coverage |
| `make migrate` | `alembic upgrade head` |
| `make migrate-create` | autogenerate a new migration |
| `make dev` | `docker compose up --build` |
| `make dev-api` / `dev-bot` / `dev-scheduler` | run one service against your local env |

## Project layout

```
src/mdk_bot/
├── api/                 # FastAPI Core API
│   ├── app.py           # app factory, /healthz, /login, /api/v1
│   └── routers/         # persons, organizations, projects, tasks,
│                        # obligations, anchors, audit, health
├── bot/                 # Telegram polling-mode bot
│   ├── handlers/        # one file per /command
│   ├── auth.py          # operator-only authorization decorator
│   └── notifier.py      # TelegramNotifier + RecordingNotifier (tests)
├── capabilities/
│   └── reminders/       # loader → rrule → engine → formatter
├── scheduler/           # APScheduler with SQLAlchemyJobStore
├── web/                 # Jinja2 + HTMX UI
│   └── templates/       # base + per-entity index/_list partials
├── core/
│   ├── db.py            # async engine + Base (eager_defaults=True)
│   ├── models.py        # ORM models (PG-native types with SQLite fallbacks)
│   ├── schemas.py       # Pydantic v2 request/response models
│   ├── auth.py          # signed session cookie + internal-token guard
│   ├── audit.py         # append-only audit-log writer
│   └── time.py          # tz-aware datetime helpers
├── shared/
│   ├── logging.py       # structlog (JSON in prod, console in dev)
│   ├── api_client.py    # httpx wrapper used by the bot
│   └── llm.py / storage.py  # stubs for Phase 3+/4+
├── config.py            # pydantic-settings with safe_dump()
└── main.py              # `python -m mdk_bot {api,bot,scheduler,worker}`
```

## Reminder engine (Phase 1)

`obligations.json` describes recurring obligations. The loader upserts them
into the `obligations` table; the engine computes the next due date for each:

1. RRULE expansion via `dateutil.rrule`. The catalog's non-standard
   `FREQ=QUARTERLY` is rewritten to `FREQ=YEARLY` with the same `BYMONTH`.
2. Holiday shifting: any candidate date falling on a weekend or a
   Bavarian/federal holiday is pushed to the next business day.
3. Anchor-driven obligations (`berufshaftpflicht_verlaengerung`,
   `domain_verlaengerung`, `est_vorauszahlung`) require an `anchor_dates`
   row. Without one, the engine sends a Monday nudge instead of a notification.
4. The daily check creates `obligation_instances`, sends a Telegram
   notification once per `(instance, lead-time-label)` pair (de-duped via
   `notification_log`), and escalates overdue mandatory items.

### Setting an anchor

Either through Telegram:

```
/anchor vertragsablauf_berufshaftpflicht 2027-01-15
```

Or via the web UI at `/web/anchors`.

## Telegram commands

| Command | Effect |
|---|---|
| `/start` / `/help` | Welcome + command list |
| `/today` | Items due today |
| `/week` | Next 7 days |
| `/upcoming [N]` | Next N obligation instances (default 5) |
| `/list [category]` | Catalog, optionally filtered |
| `/details <id>` | Full obligation record incl. raw JSON |
| `/done <id>` | Mark today's instance done |
| `/skip <id>` | Skip today's instance |
| `/anchor <field> YYYY-MM-DD` | Set anchor date |
| `/anchors` | List anchors |
| `/pause [hours]` / `/resume` | Silence notifications (default 24h) |
| `/adhoc` | List ad-hoc rules |

Messages from any Telegram user other than `AUTHORIZED_TELEGRAM_USER_ID`
are dropped silently and logged.

## Web UI

Tailwind via CDN + HTMX 2.x — no build pipeline yet. Pages:

- `/web/` Dashboard (counts + upcoming + recent audit)
- `/web/persons`, `/web/organizations`, `/web/projects`, `/web/tasks`
- `/web/obligations` Catalog + upcoming instances
- `/web/anchors` Set/list anchors

Login at `/web/login` with `WEB_SESSION_TOKEN`. The cookie is HTTP-only,
signed with `SECRET_KEY`, and expires after 14 days.

## Testing

```bash
make test           # 59 tests, ~3s
make test-cov       # 79% on src/mdk_bot/api/ + src/mdk_bot/core/
```

Tests use an in-memory SQLite engine. Models use SQLAlchemy 2.0's
`with_variant()` so JSONB/ARRAY/UUID become JSON/JSON/Uuid on SQLite while
keeping native types on Postgres. The Alembic migration is Postgres-only.

## Configuration reference

See `.env.example` — every field is documented inline.

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md).

## What ships in Phase 0 + 1 (this milestone)

- ✅ Postgres + pgvector schema with stub tables for future phases
- ✅ FastAPI Core API with CRUD for persons/orgs/projects/tasks +
  obligations/anchors/audit endpoints
- ✅ Session-cookie auth + internal-service-token bypass
- ✅ Minimal HTMX-driven web UI
- ✅ Reminder loader, RRULE engine with German/Bavarian holiday shifting,
  anchor-driven obligations, APScheduler daily check
- ✅ Telegram bot (long-polling) with 14 commands
- ✅ Single-user auth (`AUTHORIZED_TELEGRAM_USER_ID`)
- ✅ Audit log on every mutation
- ✅ Tests: 59 passing, ruff + mypy strict clean
- ✅ Docker Compose for dev + prod (Caddy with TLS)

## What's intentionally not built yet

Lexware, Gmail, Playwright, voice, knowledge base/pgvector usage,
WhatsApp, medical bill workflow, quote generation, multi-tenancy
resolution, magic-link auth, frontend build pipeline. The architecture
makes each of those an additive change.
