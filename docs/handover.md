# Project Handover Document — Marcel Kück
## For New Claude Project (Pro Account)

This document contains the complete context needed to continue without interruption.
Upload all four files into the new Claude project as **project knowledge** (not just in chat):
- `handover.md` — this file
- `mdk-engineering-bot-plan.md` — full technical master plan
- `freelancer-obligations-calendar.md` — complete obligations calendar + JSON schema
- `freelancer-setup-todos.md` — current freelancer admin status

---

## PART 1: Personal Context

**Name:** Marcel Kück
**Business:** Freelancer — Software Engineering & IT-Consulting
**Location:** Gröbenzell, Bavaria, Germany (82194)
**Website:** www.marcelkueck.dev
**Service description:** Conception, architecture and development of individual software and system solutions. Technical consulting and scientific analysis, particularly in the fields of AI and robotics.
**Freelancing since:** 01 May 2026
**Tax office:** Finanzamt Fürstenfeldbruck (Bavaria)
**Communication language:** German (unless working on technical/code tasks)

---

## PART 2: Freelancer Master Data (Germany)

| Item | Value |
|---|---|
| Tax number (Steuernummer) | 117/241/61679 (FA Fürstenfeldbruck) |
| VAT ID (USt-IdNr) | DE462191226 (valid from 09.05.2026) |
| Economic ID (W-IdNr) | DE462191226-00001 |
| Business account | N26 Business (IBAN DE39 1001 1001 2652 8585 14) |
| Accounting software | Lexware Office XL (with API) |
| Profit calculation method | EÜR (Einnahmenüberschussrechnung — simple income-surplus accounting) |
| VAT scheme | Standard taxation (not Kleinunternehmer), 5-year binding |
| VAT accounting method | Istversteuerung (VAT due when payment received, not when invoiced) |

---

## PART 3: German Tax Obligations & Status

### VAT Pre-Filing (UStVA) Frequency
**Quarterly** — based on estimated annual VAT liability of €1,500 (from tax registration form). Below the €9,000 threshold for monthly filing. The mandatory-monthly rule for new businesses (§18 Abs. 2 Satz 6 UStG) is suspended for 2021–2026.

### Estimates from Tax Registration Form
| Item | 2026 (founding year) | 2027 (following year) |
|---|---|---|
| Estimated profit (self-employed) | €10,000 | €20,000 |
| Estimated special deductions | €1,000 | €2,000 |
| Estimated turnover (Umsätze) | €12,000 | €25,000 |
| Estimated VAT liability (Zahllast) | €1,500 | — |

### Key Upcoming Deadlines 2026
| Date | What |
|---|---|
| **10.07.2026** | First VAT pre-filing: Q2 2026 (May + June) |
| 25.07.2026 | Recapitulative statement (ZM) for Q2 — only if EU B2B revenue |
| 12.10.2026 | VAT Q3 (10.10. = Saturday → shifted to Monday) |
| 11.01.2027 | VAT Q4 (10.01. = Sunday → shifted) |
| 31.07.2027 | Annual tax return 2026 |

### Completed ✅
- [x] ELSTER account created + tax registration form submitted
- [x] Lexware Office XL set up + N26 connected
- [x] Invoice template created, all master data entered
- [x] Tax number, VAT ID, and Economic ID received and entered in Lexware
- [x] VAT ID registered with Google Workspace (Reverse Charge from June)
- [x] SEPA direct debit mandate submitted to FA Fürstenfeldbruck (15.05.2026 via ELSTER)
- [x] UStVA settings in Lexware: quarterly + direct debit

### Still Open ⚠️
1. **Health insurance clarification** — URGENT. Marcel is covered through his mother (civil servant teacher, Hamburg) via AXA private insurance (Beihilfe supplement: ~80% Beihilfe + ~20% AXA). Unclear whether Beihilfe eligibility continues at age 27 (born 21.04.1999) with self-employed income. Full call script in `freelancer-setup-todos.md`.
2. **Professional liability insurance** — Must be done before first client project. Vermögensschadenhaftpflicht for IT freelancers, €1–3M coverage. Compare: Hiscox / Markel / exali.de.
3. **First invoice to May clients** — All required details are in Lexware. For EU B2B: validate client VAT ID at evatr.bff-online.de before sending.

### EU Invoice Rules (Quick Reference)
- **Germany:** Add 19% VAT
- **EU B2B (with VAT ID):** Net invoice, note "Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge)", include both VAT IDs, report in ZM
- **Non-EU (USA, UK, CH):** Net invoice, note "Nicht steuerbare Leistung gemäß § 3a UStG", report in UStVA line 45

---

## PART 4: mdk_engineering_bot — Project Context

### Vision
Marcel's personal operations platform. Telegram-first AI assistant that handles the full operational overhead of running a freelance business: reminders → Lexware agent → email triage → receipt fetching → Beihilfe medical billing → knowledge base → project lifecycle. Long-term goal: productize for other German freelancers and small business owners.

### Architecture
```
Hetzner CX22 (bot.marcelkueck.dev)
├── Caddy (TLS, reverse proxy)
├── FastAPI Core API  ← single domain logic layer
│   ├── Telegram Bot (polling)     ← API client
│   ├── APScheduler (08:00 daily)  ← API client
│   └── HTMX Web UI                ← API client
├── Postgres 16 + pgvector
└── Redis
```

All future capabilities (Lexware, Gmail, Playwright, LLM) plug into the Core API as modules.

### Repository
GitHub: `mdk_engineering_bot` (Marcel's private repo)

### Phase 0+1 — What Was Built ✅
- Postgres schema: core entities (Person, Org, Project, Task, Obligation, AuditLog) + stub tables for future phases, all with `tenant_id` for future multi-tenancy
- FastAPI Core API: full CRUD for all core entities
- Session-cookie auth (web) + internal token auth (bot → API)
- HTMX web UI: Dashboard, Persons, Orgs, Projects, Tasks, Obligations, Anchors
- Reminder engine: RRULE expansion, Bavarian + federal holidays (python-holidays), anchor dates
- Telegram bot: 14 commands (/today, /week, /upcoming, /list, /details, /done, /skip, /anchor, /anchors, /pause, /resume, /adhoc, /start, /help)
- APScheduler daily at 08:00 Europe/Berlin, Postgres-backed persistent jobs
- 59 tests, ruff + mypy strict clean
- Docker Compose dev + prod, Caddyfile with auto-TLS

### Planned Phases (full detail in `mdk-engineering-bot-plan.md`)
| Phase | Content | Status |
|---|---|---|
| 0+1 | Foundation + Reminder Bot | ✅ Built, deployed |
| 2 | Lexware sync + UStVA agent + cashflow forecast + dunning automation + VIES + DATEV export | 🔜 Next |
| 3 | Gmail triage (inbox-zero via Telegram) | — |
| 4 | Receipt auto-fetcher (Playwright: Google, Lebara, AWS, Hetzner, GitHub, Vercel) | — |
| 5 | Voice-first interface + post-meeting summary + knowledge base + daily briefing | — |
| 6 | Project lifecycle + auto-quote generator | — |
| 7 | Medical bill / Beihilfe workflow + document auto-filing | — |
| 8 | WhatsApp Business + build-log helper + reading list | — |
| 9+ | Multi-tenancy, productization | — |

---

## PART 5: Current Deployment State (as of 19.05.2026)

### Server
- **Provider:** Hetzner Cloud CX22, Falkenstein (Germany)
- **Domain:** bot.marcelkueck.dev (Namecheap A record set)
- **TLS:** Caddy + Let's Encrypt — certificate successfully issued ✅

### Container Status
| Container | Status |
|---|---|
| postgres | ✅ Healthy |
| redis | ✅ Healthy |
| caddy | ✅ TLS active |
| api | ✅ /healthz 200 OK |
| bot | 🔧 Fix just applied — needs deploy |
| scheduler | 🔧 Fix just applied — needs deploy |

### What Was Just Fixed
`src/mdk_bot/__main__.py` was missing — Claude Code didn't generate it in the initial session. Bot and scheduler crashed with `No module named mdk_bot.__main__`. A second Claude Code session created the file and merged the fix to main.

### IMMEDIATE NEXT STEPS on the server
```bash
ssh root@<server-ip>
cd /opt/mdk_engineering_bot

# Pull the fix
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build

# Run migrations (NOT YET RUN — must do this now)
docker compose -f docker-compose.prod.yml exec api uv run alembic upgrade head

# Verify
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs bot --tail=30
curl https://bot.marcelkueck.dev/healthz
```

Expected healthz response: `{"status":"ok","database":"ok","redis":"ok"}`

### Verification checklist
- [ ] Web UI: https://bot.marcelkueck.dev/web/login → enter WEB_SESSION_TOKEN → dashboard loads
- [ ] Telegram: send `/start` → bot replies with welcome
- [ ] Telegram: send `/upcoming 5` → shows next 5 obligations with correct dates
- [ ] Telegram: send `/anchor vertragsablauf_berufshaftpflicht 2027-01-15` → confirmation reply

### Known Minor Issue
API logs `db_unreachable_at_startup` warning on every boot — this is a timing issue where the API checks DB connectivity before the connection pool resolves the Docker hostname. `/healthz` returns 200 shortly after, so it's working correctly. Low priority fix.

### Environment Variables (on server at /opt/mdk_engineering_bot/.env)
```
AUTHORIZED_TELEGRAM_USER_ID = 5491994107
BOT_DOMAIN                  = bot.marcelkueck.dev
DEFAULT_TENANT_ID           = 0651590c-4719-4c41-a6fd-51851b8fdf37
TIMEZONE                    = Europe/Berlin
DAILY_CHECK_HOUR            = 8
POSTGRES_USER               = mdk
POSTGRES_DB                 = mdk_bot
```
All secrets (passwords, tokens, keys) are only on the server, never in Git.

---

## PART 6: How to Work Together

### Two workstreams
1. **Freelancer admin** — questions about German tax, UStVA, invoicing, health insurance, Lexware, etc. Use `freelancer-setup-todos.md` and `freelancer-obligations-calendar.md` as the living reference. Update them as things get done.
2. **mdk_engineering_bot development** — technical work. Use `mdk-engineering-bot-plan.md` as the architectural reference. Each phase gets its own Claude Code prompt.

### For the next Claude Code phase prompt
When ready to start Phase 2 (Lexware sync + UStVA agent + cashflow + dunning), ask Claude to generate a Phase 2 Claude Code prompt based on sections 5.2–5.8 of `mdk-engineering-bot-plan.md`. You will need a Lexware API key first (Lexware Office → Settings → API → Create API key).

### Notes
- **Oxford internship:** Separate from freelance status. If paid, declare as non-self-employed income (nichtselbständige Einkünfte) in the annual tax return. Check whether an A1 certificate is needed for UK (not an EU country post-Brexit).
- **Pension insurance (Rentenversicherung):** Not mandatory for software freelancers in principle. But if >5/6 of revenue comes from one client, mandatory pension contributions may apply as "arbeitnehmerähnlicher Selbständiger". Submit DRV clarification form V0023 once the first contract is running.
- **Backup cron job:** Set up nightly pg_dump → /opt/backups on the server (see previous session notes).
