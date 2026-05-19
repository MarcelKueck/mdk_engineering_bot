# Phase 2 — Finance Automation

Phase 2 adds eight capability modules that turn the system from a
reminder bot into a finance-aware ops platform. Every external-facing
module is behind a feature flag and a credential; with zero credentials
set, the bot/scheduler/API still come up cleanly and the new modules
log a "skipped, reason X" line at startup.

This file documents what each module does, the env vars to enable it,
and the operator commands it exposes.

---

## Quick start — turn on one module

```bash
# Example: turn on Lexware Office sync
echo 'FEATURE_LEXWARE_SYNC=true'  >> .env
echo 'LEXWARE_API_KEY=lxof_xxx'   >> .env
docker compose restart api bot scheduler
```

In Telegram: `/sync_now` triggers an immediate pull; `/finance` shows
the summary.

---

## Module reference

### 1. Lexware Office sync (`capabilities/lexware/`)

| Item | Value |
|---|---|
| Feature flag | `FEATURE_LEXWARE_SYNC` |
| Required cred | `LEXWARE_API_KEY` |
| Other env | `LEXWARE_API_BASE_URL`, `LEXWARE_SYNC_HOUR` |
| Scheduler job | daily at `LEXWARE_SYNC_HOUR:00` Europe/Berlin |
| Bot commands | `/finance`, `/sync_now` |
| Web | `/web/finance` (invoices + receipts) |

Pulls contacts → invoices → receipts → transactions from the lexoffice
REST API. Idempotent on `lexware_id`. Every upsert writes an audit-log
entry with actor `scheduler`. Disabling the flag or removing the API key
makes the daily job a no-op.

### 2. Recurring expenses (`capabilities/expenses/`) — always on

| Item | Value |
|---|---|
| Bot commands | `/expenses`, `/expense_add`, `/expense_edit`, `/expense_rm` |
| Web | `/web/expenses` |
| Helper | `monthly_burn(session, as_of)` |

Operator-managed catalog of subscriptions / fixed costs. Seeded in
migration `0002` with five real subscriptions (Claude, Lebara, Lexware
Office, Google Workspace, Hetzner) and a scheduled price change for
Lexware Office (19.57 → 32.90 from 2026-08-02). Powers the liquidity
view's monthly burn.

### 3. Time tracking (`capabilities/timetracking/`) — always on

| Item | Value |
|---|---|
| Bot commands | `/log <hours> [project] [note]`, `/hours [week\|month]`, `/unbilled` |
| Web | `/web/time` |
| Helper | `unbilled_value(session, as_of)` |

Replaces an external timer with the minimum surface: log, view by
window, list unbilled, mark billed. `unbilled_value` multiplies hours
by the project's hourly_rate and is the liquidity module's "potential,
not yet committed" figure.

### 4. UStVA Vorbereitung (`capabilities/ustva/`)

| Item | Value |
|---|---|
| Feature flag | `FEATURE_USTVA` |
| Scheduler job | Jan/Apr/Jul/Oct, day 3, 09:00 — fires when within 7 days of quarter end |
| Bot commands | `/ustva` (show), `/approve_ustva` |

Computes a quarterly UStVA preview from synced Lexware data
(output VAT from invoices − input VAT from receipts), runs the
Belegvollständigkeit check (for every active expense with a vat_rate,
flag missing receipts in the period), and notifies the operator.
`/approve_ustva` flips the period to `approved` and writes an
audit-log entry. **It does NOT submit to ELSTER** — submission stays
manual in Lexware until a dedicated capability lands.

### 5. Liquidity & runway (`capabilities/liquidity/`)

| Item | Value |
|---|---|
| Feature flag | `FEATURE_LIQUIDITY` |
| Required cred | `LIQUIDITY_OPENING_BALANCE` > 0 |
| Other env | `LIQUIDITY_RUNWAY_WARNING_DAYS`, `STEUERRUECKLAGE_RATE` |
| Scheduler job | Mondays 08:00 |
| Bot commands | `/runway` (alias `/liquidity`) |

NOT a smooth balance forecast — a runway view built from known, dated
facts: an operator-set opening balance, recurring expenses normalised
to monthly burn, the monthly Steuerrücklage applied to revenue received,
and expected inflows from open invoices at their due dates. Unbilled
time-entry value is shown SEPARATELY as "potential, not yet committed",
never blended into the committed runway. Alerts fire when the runway
falls within `LIQUIDITY_RUNWAY_WARNING_DAYS` of today.

### 6. Mahnwesen (`capabilities/dunning/`)

| Item | Value |
|---|---|
| Feature flag | `FEATURE_DUNNING` |
| Other env | `BASISZINSSATZ`, `DUNNING_B2B_MARGIN`, `DUNNING_FEE_AMOUNT` |
| Scheduler job | daily at `DAILY_CHECK_HOUR:15` |
| Bot commands | `/send_mahnung <invoice-id-prefix>` |

Scans open invoices past their `due_date` and prepares drafts at +14d
(Zahlungserinnerung), +30d (1. Mahnung), and +45d (2. Mahnung with
Verzugszinsen + Mahngebühr). Verzugszinsen = `BASISZINSSATZ +
DUNNING_B2B_MARGIN` percent on the gross, prorated by days overdue
(act/365). **The Basiszinssatz changes every January and July** — update
`BASISZINSSATZ` in `.env` each half-year.

Email transport is **stubbed in Phase 2**: `/send_mahnung` writes a
`Conversation` + `Message` representing the would-be email, marks
the run sent, and bumps the invoice's `mahnstufe`. Phase 3 swaps in
real Gmail send.

### 7. VIES VAT validation (`capabilities/vies/`)

| Item | Value |
|---|---|
| Feature flag | `FEATURE_VIES` |
| Required cred | `VIES_REQUESTER_VAT_ID` (your own VAT-ID) |
| Bot commands | `/vat <VAT-ID>` |

Sends a qualified VIES query (the requester VAT-ID is included so the
response carries a consultation/proof number). Persists the result as
`VatValidation` and generates a one-page PDF proof stored under
`./data/vies/`. Phase 2 has no automatic invoice gate — the internal
API `vies.validate_vat(session, vat_id)` is exposed for Phase 6's
invoice flow to use as a pre-send gate later.

### 8. DATEV year-end export (`capabilities/datev/`)

| Item | Value |
|---|---|
| Feature flag | `FEATURE_DATEV` |
| Other env | `DATEV_EXPORT_DIR` |
| Scheduler job | January 15th, 09:00 |
| Bot commands | `/datev_export <year>` |

Generates a DATEV "Buchungsstapel" (EXTF v700) CSV from the synced
Lexware data for the requested year, plus a JSON metadata file. SKR03
accounts are placeholders — the tax advisor needs to map them on
import. **Drive upload and tax-advisor email are deferred to Phase 3.**

---

## What Phase 2 does NOT do

- Send actual emails (Gmail integration is Phase 3 — Mahnung send is stubbed).
- Submit to ELSTER (operator approves and submits manually in Lexware).
- Upload DATEV pack to Drive or email it to the advisor.
- Block sending an invoice on a failed VIES check (no outbound invoicing yet).
- Multi-currency anything — every figure is treated as EUR.
