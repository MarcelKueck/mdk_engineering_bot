# MDK Engineering Bot — Master Plan

> A personal operations platform for a German freelancer. Telegram-first, web-augmented, agent-driven. Single user today, productizable tomorrow.

---

## 1. Vision

Build a single system that absorbs the operational overhead of running a software freelancing business so the operator can spend more time on craft and clients. The system is:

- **Telegram-first** — the primary interface is conversational; the operator should be able to run their business from their phone
- **Web-augmented** — a minimal HTMX-based web UI exists for browsing, editing, and overview tasks that Telegram can't do well
- **Agent-driven** — Claude is the brain. It classifies, drafts, summarizes, and acts on the operator's behalf with explicit approval gates
- **Source-of-truth oriented** — Lexware remains the legal record for billing; this system is the augmentation layer holding everything Lexware can't (projects, conversations, knowledge, custom workflows)
- **Productizable** — the architecture supports multi-tenancy as a deliberate Phase-N evolution, not a retrofit

The single operator is Marcel Kück (Software Engineering & IT-Beratung, Bavaria, DE). Future tenants may be other German solo freelancers and small business owners with the same Lexware/Gmail/Telegram/Hetzner stack instincts.

---

## 2. Architecture Overview

```
                           ┌──────────────────────────┐
                           │   Hetzner Cloud VPS      │
                           │   (CX32 → CX42 later)    │
                           │   Ubuntu 24.04 LTS       │
                           └────────────┬─────────────┘
                                        │ Caddy (TLS, reverse proxy)
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
        ┌─────┴─────┐            ┌──────┴──────┐           ┌──────┴─────┐
        │ Telegram  │            │   Web UI    │           │ Scheduler  │
        │ Bot       │            │  (HTMX)     │           │ (APSched.) │
        │ (polling) │            │             │           │            │
        └─────┬─────┘            └──────┬──────┘           └──────┬─────┘
              │                         │                         │
              └─────────────┬───────────┴─────────────┬───────────┘
                            │                         │
                     ┌──────┴──────┐           ┌──────┴──────┐
                     │   Core API  │           │  Worker(s)  │
                     │  (FastAPI)  │◄──────────┤ (Playwright,│
                     │             │   RPC     │  long jobs) │
                     └──────┬──────┘           └──────┬──────┘
                            │                         │
              ┌─────────────┴─────────────┐           │
              │                           │           │
       ┌──────┴──────┐             ┌──────┴──────┐    │
       │  Postgres   │             │    Redis    │◄───┘
       │ + pgvector  │             │  (queues,   │
       │             │             │   cache)    │
       └─────────────┘             └─────────────┘

External APIs:
  Anthropic · Lexware Office · Gmail · Google Calendar
  · WhatsApp Cloud API · OpenAI Whisper (transcription)
  · Hetzner Object Storage · Toggl · Playwright targets
```

**Process layout (Docker Compose):**
- `api` — FastAPI serving REST + HTMX
- `bot` — Telegram bot (polling)
- `scheduler` — APScheduler tick process
- `worker` — Celery/RQ for long-running jobs (Playwright, large LLM calls, batch syncs)
- `postgres` — primary store with pgvector
- `redis` — queues, cache, rate limiting
- `caddy` — TLS termination, reverse proxy

All inter-service communication goes through the Core API; the bot and web UI are pure clients. This keeps domain logic in one place and makes future agent interfaces (CLI, voice device, second tenant) trivial to add.

---

## 3. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.12 | Mature async, best LLM SDK ecosystem |
| Package manager | `uv` | 10× faster than pip/poetry, single source of truth |
| Web framework | FastAPI | Async, Pydantic-native, OpenAPI auto-gen |
| ORM | SQLAlchemy 2.x + Alembic | Industry standard, async support |
| DB | Postgres 16 + pgvector | Single store for relational + vector |
| Cache/queue | Redis 7 | De-facto standard, low ops |
| Task queue | RQ or Celery | RQ for simplicity, upgrade to Celery if needed |
| Bot framework | python-telegram-bot v21+ | Most mature, async, polling-friendly |
| Scheduling | APScheduler + SQLAlchemyJobStore | Persistent jobs across restarts |
| Browser automation | Playwright | Modern, supports all required login flows |
| LLM | Anthropic API (Claude Sonnet 4.6 default, Haiku for classification, Opus for hard reasoning) | Best price/performance, structured outputs |
| Transcription | OpenAI Whisper API (later: self-hosted whisper.cpp) | Cheap, accurate, multilingual |
| Web UI | HTMX + Tailwind + Jinja2 | No build pipeline, server-rendered, fast iteration |
| Auth (web) | Token-based session, Telegram-OTP later | Single user MVP, multi-user ready |
| Deployment | Docker Compose + Caddy on Hetzner VPS | Cheap, full control, no vendor lock-in |
| Logging | structlog → stdout → Loki (later) | JSON logs, future-proof |
| Tests | pytest, pytest-asyncio, httpx, factory_boy | Standard, well-supported |
| Lint/format | ruff | Replaces black + flake8 + isort |
| Type-check | mypy (strict mode on src/) | Catches half the bugs before runtime |

---

## 4. Data Model (Core)

The core entities form a graph. Lexware data is mirrored, not duplicated — Lexware IDs are foreign keys to external state.

### Identity & Relationships

- **Person** — humans (clients, prospects, provider contacts). Fields: name, email, phone, current_org_id, linkedin_url, notes, tags, custom_fields (JSONB), created_at
- **Organization** — companies. Fields: name, legal_form, vat_id, address, lexware_id, website, notes, tags
- **Project** — your work units. Fields: name, customer_org_id, status (`lead|quote|active|paused|delivered|invoiced|paid|closed|lost`), hourly_rate, scope, start_date, end_date, description, tags

### Workflow & Activity

- **Task** — todos. Fields: title, description, due_date, status, priority, project_id, person_id, obligation_id (nullable), source, created_at, completed_at
- **Obligation** + **ObligationInstance** — recurring duties (from obligations.json) and their concrete date instances
- **Event** — calendar items. Fields: external_id (Google), start, end, title, person_ids, org_ids, project_id, prep_briefing, summary, action_items

### Communication

- **Conversation** — email/WhatsApp/meeting threads. Fields: channel, external_id, subject, snippet, last_message_at, person_id, org_id, project_id, classification, urgency_score, ai_draft, status (`inbox|drafted|sent|archived`)
- **Message** — individual messages within a Conversation. Fields: direction, from, to, cc, body, body_html, received_at, sent_at, attachments

### Documents & Money

- **Document** — every file. Fields: filename, mime, storage_key (S3 path), sha256, ocr_text, embedding (vector), doctype (`receipt|invoice|contract|medical_bill|gehaltsabrechnung|...`), entity_type, entity_id (polymorphic), tags, metadata
- **Transaction** — bank movements. Fields: account, date, amount, currency, description, counterparty, lexware_match_id, project_id, status
- **Invoice** — synced from Lexware. Fields: lexware_id, number, customer_org_id, project_id, issue_date, due_date, total_gross, total_net, status, paid_date, mahnstufe
- **Receipt** — synced from Lexware. Fields: lexware_id, vendor_org_id, project_id, date, total, vat, category, document_id, status

### Knowledge & Personal

- **KnowledgeItem** — voice notes, bookmarks, highlights. Fields: source, content, title, embedding, tags
- **ReadingItem** — links to read later. Fields: url, title, snippet, status, added_at
- **MedicalBill** — Beihilfe-trackable bills. Fields: document_id, date, total, vendor, beihilfe_status, beihilfe_submitted_at, beihilfe_reimbursed, axa_status, axa_submitted_at, axa_reimbursed
- **ProviderCredential** — encrypted vault. Fields: provider, type (`oauth|cookie|userpass|api_key`), encrypted_payload (Fernet), last_used_at, last_success_at, last_error

### Audit

- **AuditLog** — every bot/agent action on behalf of the user. Fields: actor (`user|bot|agent`), action, entity_type, entity_id, payload, created_at. Critical for trust and for future productization.

---

## 5. Capability Modules

Each capability is a self-contained module: domain logic + scheduler triggers + bot commands + web views + API endpoints. They share the core data model.

### 5.1 Reminder Engine (Phase 1)
The original Telegram reminder bot. Loads `obligations.json`, expands RRULEs, shifts for German/Bavarian holidays, sends notifications at 08:00, supports `/today`, `/week`, `/upcoming`, `/done`, `/skip`, `/anchor`, `/pause`. ObligationInstances stored in Postgres.

### 5.2 Lexware Sync (Phase 2)
- Daily pull: customers, invoices, receipts, transactions from Lexware Office API
- Reconcile with local entities (Org, Project, Invoice, Receipt)
- Webhook subscription if/when Lexware supports it; polling fallback
- Detect new/changed entities; surface in web UI dashboard

### 5.3 Lexware Agent — UStVA Vorbereitung (Phase 2)
Before each quarter end (~7 days lead):
1. Check Belegvollständigkeit: which receipts are missing for known recurring expenses?
2. Telegram-prompt for each gap: "AWS invoice for September? Forward by email or upload."
3. When complete: trigger Receipt Auto-Fetcher (Phase 4) for known providers
4. Generate UStVA preview from Lexware
5. Send preview to operator via Telegram
6. On approval (`/approve_ustva`), submit via Lexware → ELSTER

### 5.4 Receipt Auto-Fetcher (Phase 4) ⭐
- Credential vault stores OAuth tokens (Google) and session cookies / user+pass (Lebara, Hetzner, AWS, GitHub, Vercel, etc.)
- Monthly cron triggers Playwright worker for each configured provider
- Worker logs in headlessly, navigates to billing page, downloads latest invoice PDF
- Uploads PDF to Lexware via API, attempts auto-match to a known transaction
- If match ambiguous: Telegram prompt with the suggested match
- Failures (login change, MFA, etc.) reported to operator immediately

### 5.5 Cashflow Forecast (Phase 2)
Pulls from Invoice (open + expected payment date), recurring expenses (from Receipts), Steuerrücklage rules, and Toggl WIP. Projects N26 balance 90 days forward. Telegram weekly digest. Threshold alert: "If revenue stays flat, balance < 5.000 € in 47 days."

### 5.6 Mahnwesen-Automat (Phase 2)
Daily check of open Invoices. At +14 days: drafts "Zahlungserinnerung" in operator's voice. At +30: "1. Mahnung". At +45: "2. Mahnung mit Verzugszinsen + Mahngebühren". Each draft delivered to Telegram; on `/send_mahnung` the email goes out. Tracks mahnstufe; logs to Conversation.

### 5.7 VIES Auto-Check (Phase 2)
Before any EU-B2B invoice is sent: qualified VIES query via evatr.bff-online.de. PDF receipt of the validation attached to the Invoice in Lexware. Failure blocks send and asks for clarification.

### 5.8 DATEV Year-End Export (Phase 2)
January 15th cron: pull full year from Lexware as DATEV-compatible export, package with metadata, upload to a designated Drive folder, notify the operator (and optionally tax advisor) by email.

### 5.9 Email Triage — Gmail (Phase 3) ⭐
- Gmail OAuth, watch primary inbox
- New email → classification with Haiku (kunde|provider|admin|newsletter|spam|persönlich)
- For non-spam: draft response with Sonnet using context (sender history, related project, recent threads)
- Urgent classification (deadline language, escalation cues) → Telegram alert with one-tap reply
- Operator approves/edits in Telegram → bot sends from Gmail
- Inbox-Zero workflow surface in web UI

### 5.10 WhatsApp Business Bridge (Phase 8)
- Meta Cloud API integration
- Auto-replies for FAQs (loaded from knowledge base)
- Lead capture for inquiries → creates Person/Conversation/Task
- Urgent escalation to Telegram

### 5.11 Voice-First Interface (Phase 5) ⭐
- Voice note to Telegram bot → Whisper transcription
- Intent classification (Haiku): task / quote / note / question / command
- Routes to appropriate capability handler
- Replies in same channel; for tasks, creates Task with link back to source voice

### 5.12 Post-Meeting Summary (Phase 5)
- After calendar event ends OR explicit "/meeting Done" trigger
- Operator voice-records summary → Whisper
- Sonnet extracts: decisions, action items, follow-ups, named entities
- Creates Tasks linked to Project/Person; updates Event with summary
- Optional: drafts follow-up email

### 5.13 Project Lifecycle (Phase 6)
State machine: `lead → quote → contract → active → delivered → invoiced → paid → closed` (with `paused` and `lost` exits). Each transition triggers automations:
- `lead → quote`: prompt for Auto-Quote (5.14)
- `quote → contract`: send NDA/contract template, DocuSign optional
- `contract → active`: create kickoff Task, schedule weekly status check
- `delivered → invoiced`: trigger Lexware invoice creation
- `invoiced → paid`: thank-you note draft + ask for testimonial
- All transitions logged to AuditLog

### 5.14 Auto-Quote Generator (Phase 6)
- Take Conversation thread + scope notes
- Sonnet drafts: scope summary, deliverables, timeline, hourly/fixed pricing using configured rates
- Renders to PDF (WeasyPrint) with letterhead
- Operator reviews in Telegram; on approval, sent via Gmail and saved as Document on Project

### 5.15 Medical Bill Workflow — Beihilfe (Phase 7) ⭐
Most-loved feature for the operator's specific situation:
- Photo of Arztrechnung → Document → OCR → MedicalBill entity
- Drafts Beihilfe-Antrag form for Hamburg (PDF, semi-fillable) and Axa submission
- Submits via configured channel (email/portal/post)
- Tracks status; reminds at 4 weeks if no reimbursement
- Reconciles incoming reimbursement on N26 with the MedicalBill

### 5.16 Document Auto-Filing (Phase 7)
- Inbox watcher (Gmail label `Auto-File`, or upload to bot)
- OCR + classification (`gehaltsabrechnung|mietvertrag|versicherungspolice|behoerde|...`)
- Filed to Hetzner Object Storage with structured key: `{year}/{doctype}/{date}-{counterparty}.pdf`
- Indexed (embedding + metadata) for later natural-language search

### 5.17 Personal Knowledge Base (Phase 5)
- Voice notes, saved URLs, PDF highlights, manual notes all become KnowledgeItem
- Embedded via Anthropic embedding API (or sentence-transformers self-hosted)
- Telegram: `/recall <query>` → semantic search → top 5 with previews
- Weekly digest: "Topics you visited 3 times this month: …"

### 5.18 Daily Briefing — 07:30 (Phase 5)
Telegram message at 07:30:
- Top 3 Tasks for today
- Calendar highlights
- Weather (one line)
- One relevant industry news item (filtered with Sonnet from configured RSS/feeds)
- USD/EUR rate (if any open USD invoices)
- Sentence of motivation from a knowledge base of operator's own past notes (call it "yesterday-you")

### 5.19 Build-Log Helper (Phase 8) ⭐
- Voice ramble about what got built today → Whisper → Sonnet drafts Substack-ready post in operator's voice (style learned from past posts)
- Markdown delivered to Telegram for review
- On approval, pushes to a `drafts/` folder in the Substack repo via GitHub API

### 5.20 Reading List Manager (Phase 8)
- Send URL to bot → fetched, summarized, stored as ReadingItem
- Sunday evening digest: "These 7 items are unread. Pick which to read this week."
- `/read <id>` opens a stripped reader view in Telegram or web UI

---

## 6. Phasing & Roadmap

Each phase is one Claude Code session (a focused, reviewable PR). Phases build on each other.

| Phase | Scope | Duration |
|---|---|---|
| **0** | Foundation: repo scaffold, Postgres, FastAPI, web UI shell, auth, docker-compose, Hetzner deploy | 1 session |
| **1** | Reminder Engine (current obligations.json) | same session as 0 |
| 2 | Lexware Sync + UStVA Vorbereitung + Cashflow + Mahnwesen + VIES + DATEV Export | 1 session |
| 3 | Gmail Triage (no WA yet) | 1 session |
| 4 | Receipt Auto-Fetcher (Playwright + Credential Vault) | 1 session |
| 5 | Voice-First Interface + Post-Meeting + Knowledge Base + Daily Briefing | 1 session |
| 6 | Project Lifecycle + Auto-Quote Generator | 1 session |
| 7 | Medical Bill / Beihilfe Workflow + Document Auto-Filing | 1 session |
| 8 | WhatsApp Business Bridge + Build-Log Helper + Reading List | 1 session |
| 9+ | Polish, productization, multi-tenancy | TBD |

Phase 0+1 is what gets built in the first Claude Code session (see the separate prompt file).

---

## 7. Deployment — Hetzner Cloud

**Recommended setup for solo use:**
- **VPS:** CX32 (€7/month, 8GB RAM, 2 vCPU, 80GB SSD) — comfortable for Phase 0–5
- **Upgrade trigger:** Add Playwright worker (Phase 4) → CX42 (€13/month, 8GB RAM, 4 vCPU)
- **Object storage:** Hetzner Object Storage (€1.50/month for 100GB)
- **DNS:** any registrar (Cloudflare DNS for the bot subdomain is fine)
- **TLS:** Caddy auto-cert via Let's Encrypt
- **OS:** Ubuntu 24.04 LTS

**Setup outline:**
1. Provision CX32, harden (UFW, fail2ban, SSH key only, unattended-upgrades)
2. Install Docker + docker-compose plugin
3. Clone repo, copy `.env.example` → `.env`, fill secrets
4. `docker compose up -d`
5. Caddy auto-provisions TLS on the configured domain
6. Telegram bot polling starts immediately
7. Postgres data persisted to a named volume; nightly backup to Object Storage via separate cron container

**Monthly cost (Phase 0–4):**
- CX32: €7
- Object Storage: €1.50
- Anthropic API (estimated 100k tokens/day): €15–30
- OpenAI Whisper API (occasional voice): €1–5
- **Total: ~€25–45/month**

---

## 8. Security & Privacy

This system holds sensitive data: bank transactions, tax info, medical bills, client communications. Treat it accordingly.

### Secrets management
- All secrets in environment variables, loaded via Pydantic settings
- ProviderCredential payloads encrypted at rest with Fernet, key derived from `MASTER_ENCRYPTION_KEY` env var
- Master key on Hetzner VPS only, backed up offline (hardware security key, paper)
- No secrets in logs (structlog scrubs known keys)

### Network
- All traffic via Caddy/HTTPS; raw Postgres/Redis only accessible inside Docker network
- Telegram bot uses long-polling (no public webhook needed → smaller attack surface)
- Web UI behind token-based session (single user) → upgrade to OIDC for multi-tenant

### Data minimization
- Email bodies retained 90 days then archived to cold storage
- Voice notes deleted after transcription unless flagged
- Audit log retained indefinitely (necessary for trust)

### Backups
- Postgres: nightly logical backup (`pg_dump`) → Object Storage with 30-day retention
- Object Storage: weekly mirror to second region (Hetzner Storage Box)
- Telegram chat history: not relied on — all state in Postgres

### Compliance
- DSGVO: as solo user this is for personal use; productization requires AVV with each tenant
- 10-year Aufbewahrung for tax-relevant docs handled by Lexware; Document store keeps redundant copies

### Trust controls
- Every agent action goes to AuditLog
- "Action receipts" — when the bot does something (sends email, submits form), a Telegram confirmation goes to operator within 60s
- Kill switch: `/pause` halts all outbound actions immediately
- Dry-run mode for all destructive operations (e.g. `/send_mahnung <id> dry` shows preview)

---

## 9. Productization Roadmap

The codebase is built for single-user from day one but with the seams in the right places.

### Architectural seams (already in place from Phase 0)
- `tenant_id` column on every business entity (defaults to single tenant for self-hosting)
- All API routes accept a tenant context (resolved from session → `current_tenant`)
- ProviderCredential and capability config scoped per tenant
- Postgres row-level security policies on tenant_id (enable when going multi-tenant)

### Multi-tenant evolution (Phase 9+)
- Onboarding wizard: connect Lexware, Telegram, Gmail in <20 min
- Per-tenant docker-compose namespace or Kubernetes (Hetzner has affordable K8s)
- White-label: bot username, branding, custom domain
- Pricing tiers: Free (Reminders) / Pro (Lexware + Email) / Business (RPA + WA + KB)
- Stripe billing
- Customer-facing dashboard separate from operator's

### Target customer profile
- Solo software/consulting freelancer in Germany
- Already on Lexware Office or similar
- Uses Gmail + Google Calendar
- Hetzner-friendly (or okay with managed hosting at higher tier)

---

## 10. What's NOT in scope (ever)

- Multi-currency accounting beyond invoice display (Lexware handles)
- HR / payroll (no employees in target user)
- Inventory / e-commerce
- Customer-facing marketing automation (this is for the operator, not their customers)
- Mobile app (Telegram + responsive web is sufficient)

---

## Appendix A — Repo Layout (target after Phase 1)

```
mdk_engineering_bot/
├── pyproject.toml
├── uv.lock
├── docker-compose.yml
├── docker-compose.prod.yml
├── Caddyfile
├── .env.example
├── .gitignore
├── README.md
├── DEPLOYMENT.md
├── obligations.json
├── alembic.ini
├── migrations/
│   └── versions/
├── src/
│   └── mdk_bot/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.py
│       ├── core/
│       │   ├── db.py
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── auth.py
│       │   └── audit.py
│       ├── api/
│       │   ├── app.py
│       │   ├── routers/
│       │   │   ├── persons.py
│       │   │   ├── organizations.py
│       │   │   ├── projects.py
│       │   │   ├── tasks.py
│       │   │   ├── obligations.py
│       │   │   └── anchors.py
│       │   └── deps.py
│       ├── web/
│       │   ├── views.py
│       │   ├── templates/
│       │   └── static/
│       ├── bot/
│       │   ├── app.py
│       │   ├── handlers/
│       │   └── notifier.py
│       ├── scheduler/
│       │   ├── app.py
│       │   └── jobs.py
│       ├── capabilities/
│       │   └── reminders/   # Phase 1 module
│       │       ├── engine.py
│       │       ├── rrule.py
│       │       └── handlers.py
│       └── shared/
│           ├── logging.py
│           ├── llm.py       # stubs for Phase 2+
│           ├── storage.py   # stubs for Phase 2+
│           └── time.py
└── tests/
    ├── conftest.py
    ├── core/
    ├── api/
    ├── capabilities/
    └── e2e/
```

Future capability modules slot into `src/mdk_bot/capabilities/<name>/`.

---

## Appendix B — Cost & Time Estimate

Realistic estimates for solo developer review-and-iterate workflow with Claude Code doing the bulk of the writing:

| Phase | Wall-clock | Active operator time | Infra cost delta |
|---|---|---|---|
| 0+1 | ~3 days | ~6 hours | €0 |
| 2 | ~4 days | ~8 hours | €0 |
| 3 | ~3 days | ~6 hours | +€5/mo (Anthropic usage) |
| 4 | ~5 days | ~10 hours | +€5/mo (CX42 upgrade) |
| 5 | ~4 days | ~8 hours | +€3/mo (Whisper) |
| 6 | ~3 days | ~6 hours | €0 |
| 7 | ~4 days | ~8 hours | €0 |
| 8 | ~4 days | ~8 hours | +€2/mo (WA Cloud) |
| **Total to "everything working"** | **~30 days** | **~60 hours** | **~€45/mo** |

Spread across 3–4 months part-time is realistic. The system delivers value incrementally — after Phase 0+1 you already have reminders running.