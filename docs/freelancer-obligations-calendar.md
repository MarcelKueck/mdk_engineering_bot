# Freelancer Obligations — Calendar & Reminder System

**Marcel Kück — Software Engineering & IT-Consulting**
Last updated: 19 May 2026

All recurring obligations, grouped by frequency. At the end: JSON structure for the Telegram reminder bot.

---

## Weekly

### Receipt capture (every Friday)
- Photograph/scan incoming invoices and receipts → Lexware app → automatic categorisation
- Review automatic assignments
- **Why weekly:** Avoids pile-up. Receipts from 4 weeks ago are harder to assign than yesterday's.
- **Effort:** ~5–10 minutes

### Invoice outbox (every Friday)
- Review Toggl hours → create invoices for completed milestones
- For hourly projects: weekly billing; for milestone projects: per delivery
- **Effort:** ~15–30 minutes depending on number of clients

### Dunning check (every Friday)
- In Lexware under "Offene Posten" check for overdue invoices
- Payment reminder at +14 days, 1st notice at +30 days, 2nd notice at +45 days
- **Effort:** ~5 minutes

---

## Monthly

### Tax reserve transfer (1st of each month)
- Rule of thumb: **30% of monthly revenue** to a separate savings account
  - ~19% for VAT (if not auto-debited by tax office)
  - ~10–15% for income tax reserve
- **Effort:** 2 minutes

### Bank reconciliation (1st of each month)
- Match N26 transactions in Lexware
- Resolve any unmatched bookings
- **Effort:** ~10 minutes (mostly automatic)

### Cash flow review (1st of each month)
- Incoming vs. outgoing payments for the previous month
- Outstanding receivables, planned expenses
- **Effort:** ~15 minutes

---

## Quarterly

### VAT Pre-Filing (UStVA)

| Quarter | Period | Due date | Reminder 7 days before |
|---|---|---|---|
| Q1 | Jan–Mar | 10 April | 3 April |
| Q2 | Apr–Jun | 10 July | 3 July |
| Q3 | Jul–Sep | 10 October | 3 October |
| Q4 | Oct–Dec | 10 January | 3 January |

Note: If the 10th falls on a weekend or public holiday, the deadline shifts to the next business day.

- Process: Lexware calculates → review → submit via ELSTER
- With active SEPA mandate: payment automatic
- **Effort:** ~15 minutes

### Recapitulative Statement — ZM (only for EU B2B revenue)

| Quarter | Due (25th after quarter end) |
|---|---|
| Q1 | 25 April |
| Q2 | 25 July |
| Q3 | 25 October |
| Q4 | 25 January |

- ELSTER → Zusammenfassende Meldung
- List all EU B2B clients' VAT IDs + net amounts invoiced
- **Effort:** ~10 minutes

### Income Tax Prepayments (ESt-Vorauszahlungen) — if set by tax office

| Quarter | Due date |
|---|---|
| Q1 | 10 March |
| Q2 | 10 June |
| Q3 | 10 September |
| Q4 | 10 December |

- 2026: likely €0 (profit below Grundfreibetrag ~€12,096)
- From 2027: ~€250–325/quarter based on €20k estimate
- With active SEPA mandate: auto-debited, just check liquidity
- **Effort:** 0 (passive if SEPA active)

### Estimate Review
- Does the estimated VAT liability from the tax registration form (~€1,500/year) still hold?
- If actual liability deviates >20%: inform tax office
- Hourly rate and capacity review
- **Effort:** ~20 minutes

---

## Semi-Annual

### Hourly rate and pricing review (January + July)
- Are rates still market-competitive?
- Which clients are unprofitable? Which deserve upselling?
- Pipeline review

### GDPR (DSGVO) — update records of processing activities
- When tools or data processing change: update VVT (Verzeichnis von Verarbeitungstätigkeiten)
- Check data processing agreements (AVV) with new tools (Lexware, N26, Google Workspace all have their own)

---

## Annual

### Annual Tax Return (due 31 July of following year)
- **Reminder:** 1 May of following year → book tax advisor or start yourself
- Extended deadline with tax advisor: end of February of the year after that
- Components:
  - Income tax return (Mantelbogen + Anlage S + Anlage EÜR)
  - Annual VAT return (Umsatzsteuer-Jahreserklärung)
  - Anlage Vorsorgeaufwand (health insurance premiums etc.)
- EÜR generated automatically by Lexware
- **Effort:** 2–4 hours self, ~1 hour with tax advisor

### Professional liability insurance renewal
- Reminder 60 days before contract expiry
- Cancellation deadline usually 3 months before expiry
- Review policy: coverage amount still sufficient? Service description up to date?

### Health insurance income proof
- After receiving the tax assessment notice (Steuerbescheid): send it to health insurer
- Premium adjusted to actual income
- **Effort:** ~15 minutes

### Fixed assets inventory (31 December)
- Low-value assets (GWG ≤€800 net): immediately expensible
- Pooled items €250–€1,000 net: 5-year pooled depreciation
- Over €1,000 net: standard depreciation over useful life
- **Effort:** ~30 minutes (managed in Lexware)

### IT hygiene and backups (January)
- Export accounting data backups (Lexware → DATEV export)
- Check receipt archive (10-year retention obligation!)
- Password hygiene, 2FA review

### Domain and hosting renewals
- marcelkueck.dev — when does the domain expire?
- Vercel, GitHub, other services — annual vs. monthly billing
- Reminder 30 days before expiry

---

## Event-Triggered (not time-based)

### Before every EU client invoice
- Qualified VAT ID validation at https://evatr.bff-online.de (your VAT ID + client's)
- Save PDF confirmation in Lexware under the client
- Reverse Charge note on invoice

### Before every non-EU client invoice (USA, UK, CH)
- Note "Nicht steuerbare Leistung gemäß § 3a UStG" on invoice
- Check double taxation treaty (withholding tax risk)
- For USD/GBP: ensure Wise account receives payment

### Before every EU work trip
- Apply for A1 certificate from health insurer at least 2 weeks before departure
- If >4 weeks: consult tax advisor

### When a single client exceeds 5/6 of revenue
- Submit DRV clarification form V0023 (check for quasi-employment status)
- Review contract for employment indicators

### Quarterly validation of recurring EU clients' VAT IDs
- Re-validate VAT ID once per quarter for each recurring EU client
- Protects against disputes with the tax office if client loses their VAT ID

### When adding new SaaS tools
- Sign data processing agreement (AVV) if personal data is processed
- Add to GDPR records of processing activities (VVT)

---

## Concrete Dates 2026 (Chronological)

| Date | What |
|---|---|
| Late May 2026 | SEPA mandate should be activated by FA |
| 01.06.2026 | Bank reconciliation May, tax reserve transfer |
| 03.07.2026 | Reminder: UStVA Q2 in one week |
| **10.07.2026** | **UStVA Q2 2026 (May + June) due** |
| 25.07.2026 | ZM Q2 (if EU B2B revenue) |
| 03.10.2026 | Reminder: UStVA Q3 in one week |
| **12.10.2026** | **UStVA Q3 2026 due** (10.10. = Saturday) |
| 26.10.2026 | ZM Q3 (if EU B2B; 25.10. = Sunday) |
| 31.12.2026 | Fixed assets inventory, last chance for GWG purchases |
| 04.01.2027 | Reminder: UStVA Q4 in one week |
| **11.01.2027** | **UStVA Q4 2026 due** (10.01. = Sunday) |
| 25.01.2027 | ZM Q4 |
| 01.05.2027 | Reminder: prepare 2026 annual tax return |
| **31.07.2027** | **Annual tax return 2026 due** (without tax advisor) |

---

## JSON Schema for Telegram Bot

Directly parseable. Each obligation has: `id`, `title`, `category`, `recurrence` (RRULE-style), `lead_time_days` (when to send reminder before due date), `action` (what to do), `tool` (where it happens), `mandatory`, `estimated_minutes`.

```json
{
  "obligations": [
    {
      "id": "belege_woechentlich",
      "title": "Capture receipts",
      "category": "bookkeeping",
      "recurrence": "FREQ=WEEKLY;BYDAY=FR",
      "lead_time_days": 0,
      "action": "Photograph receipts, assign in Lexware app",
      "tool": "Lexware Office App",
      "mandatory": false,
      "estimated_minutes": 10
    },
    {
      "id": "rechnungen_versenden",
      "title": "Send invoices for the week",
      "category": "revenue",
      "recurrence": "FREQ=WEEKLY;BYDAY=FR",
      "lead_time_days": 0,
      "action": "Review Toggl hours, create invoices in Lexware",
      "tool": "Toggl + Lexware",
      "mandatory": false,
      "estimated_minutes": 20
    },
    {
      "id": "mahnwesen",
      "title": "Check overdue invoices",
      "category": "liquidity",
      "recurrence": "FREQ=WEEKLY;BYDAY=FR",
      "lead_time_days": 0,
      "action": "Check open receivables in Lexware, send payment reminders if overdue",
      "tool": "Lexware Office",
      "mandatory": false,
      "estimated_minutes": 5
    },
    {
      "id": "steuerruecklage_monatlich",
      "title": "Transfer 30% tax reserve",
      "category": "liquidity",
      "recurrence": "FREQ=MONTHLY;BYMONTHDAY=1",
      "lead_time_days": 0,
      "action": "Transfer 30% of previous month revenue to tax savings account",
      "tool": "N26",
      "mandatory": false,
      "estimated_minutes": 5
    },
    {
      "id": "ustva_quartal",
      "title": "VAT pre-filing (UStVA) — quarterly",
      "category": "tax",
      "recurrence": "FREQ=YEARLY;BYMONTH=1,4,7,10;BYMONTHDAY=10",
      "lead_time_days": 7,
      "action": "In Lexware: calculate UStVA for completed quarter, review, submit via ELSTER interface",
      "tool": "Lexware → ELSTER",
      "mandatory": true,
      "estimated_minutes": 15,
      "penalty": "Late surcharge up to 10% of liability, max €25,000"
    },
    {
      "id": "zm_quartal",
      "title": "Recapitulative Statement (ZM) — quarterly",
      "category": "tax",
      "recurrence": "FREQ=YEARLY;BYMONTH=1,4,7,10;BYMONTHDAY=25",
      "lead_time_days": 5,
      "action": "For EU B2B revenue in the quarter: enter client VAT IDs + net amounts in ELSTER ZM form",
      "tool": "ELSTER",
      "mandatory": "if EU B2B revenue",
      "estimated_minutes": 10,
      "skip_if": "no EU B2B revenue in the quarter"
    },
    {
      "id": "est_vorauszahlung",
      "title": "Income tax prepayment (ESt-Vorauszahlung)",
      "category": "tax",
      "recurrence": "FREQ=YEARLY;BYMONTH=3,6,9,12;BYMONTHDAY=10",
      "lead_time_days": 3,
      "action": "Check liquidity — SEPA auto-debit if set by tax office",
      "tool": "passive (SEPA direct debit)",
      "mandatory": "if set by tax office",
      "estimated_minutes": 2,
      "skip_if": "no prepayment set by FA"
    },
    {
      "id": "schaetzung_review",
      "title": "Quarterly estimate review",
      "category": "planning",
      "recurrence": "FREQ=YEARLY;BYMONTH=1,4,7,10;BYMONTHDAY=15",
      "lead_time_days": 0,
      "action": "Compare actual VAT liability vs. registered estimate (€1,500/year) — inform FA if >20% deviation",
      "tool": "Lexware reporting",
      "mandatory": false,
      "estimated_minutes": 20
    },
    {
      "id": "stundensatz_review",
      "title": "Hourly rate and pricing review",
      "category": "business",
      "recurrence": "FREQ=YEARLY;BYMONTH=1,7;BYMONTHDAY=15",
      "lead_time_days": 0,
      "action": "Check rates vs. market, review client profitability, pipeline review",
      "tool": "Lexware + Toggl",
      "mandatory": false,
      "estimated_minutes": 60
    },
    {
      "id": "berufshaftpflicht_verlaengerung",
      "title": "Professional liability insurance renewal",
      "category": "insurance",
      "recurrence": "FREQ=YEARLY",
      "lead_time_days": 60,
      "action": "Review policy: coverage still adequate? Service description current? Compare providers if needed.",
      "tool": "Insurer portal",
      "mandatory": true,
      "estimated_minutes": 30,
      "anchor_date_field": "vertragsablauf_berufshaftpflicht"
    },
    {
      "id": "krankenkasse_einkommensnachweis",
      "title": "Health insurance income proof",
      "category": "insurance",
      "recurrence": "FREQ=YEARLY",
      "lead_time_days": 14,
      "action": "Send current tax assessment notice to health insurer",
      "tool": "Email/Post",
      "mandatory": true,
      "estimated_minutes": 15,
      "trigger": "after_receiving_tax_assessment"
    },
    {
      "id": "inventur_jahresende",
      "title": "Year-end fixed assets inventory",
      "category": "bookkeeping",
      "recurrence": "FREQ=YEARLY;BYMONTH=12;BYMONTHDAY=31",
      "lead_time_days": 14,
      "action": "Review asset register, complete any GWG purchases by year-end for immediate write-off",
      "tool": "Lexware asset register",
      "mandatory": true,
      "estimated_minutes": 30
    },
    {
      "id": "jahreserklaerung",
      "title": "Annual tax return",
      "category": "tax",
      "recurrence": "FREQ=YEARLY;BYMONTH=7;BYMONTHDAY=31",
      "lead_time_days": 90,
      "action": "Book tax advisor appointment OR start yourself: Anlage S, EÜR, annual VAT return, Vorsorgeaufwand",
      "tool": "Tax advisor or ELSTER + Lexware",
      "mandatory": true,
      "estimated_minutes": 180,
      "penalty": "Late surcharge from 10th day: 0.25% of tax liability per month, min €25/month"
    },
    {
      "id": "domain_verlaengerung",
      "title": "Domain renewal check (marcelkueck.dev)",
      "category": "infrastructure",
      "recurrence": "FREQ=YEARLY",
      "lead_time_days": 30,
      "action": "Check domain renewal, consider multi-year purchase",
      "tool": "Namecheap",
      "mandatory": true,
      "estimated_minutes": 10,
      "anchor_date_field": "domain_ablauf"
    },
    {
      "id": "backups_buchhaltung",
      "title": "Accounting backups export",
      "category": "infrastructure",
      "recurrence": "FREQ=YEARLY;BYMONTH=1;BYMONTHDAY=15",
      "lead_time_days": 0,
      "action": "DATEV export from Lexware, save locally and to cloud backup",
      "tool": "Lexware Office",
      "mandatory": true,
      "estimated_minutes": 20
    }
  ],
  "ad_hoc_rules": [
    {
      "id": "eu_kunde_vies_check",
      "title": "Validate VAT ID before EU invoice",
      "trigger": "new_invoice AND client.country != 'DE' AND client.country IN eu_countries",
      "action": "VIES query at evatr.bff-online.de, archive PDF confirmation in Lexware under client",
      "tool": "https://evatr.bff-online.de"
    },
    {
      "id": "drittland_rechnung",
      "title": "Non-EU invoice — check notes",
      "trigger": "new_invoice AND client.country NOT IN eu_countries AND client.country != 'DE'",
      "action": "Add '§ 3a UStG' note to invoice, check DTA, use Wise for foreign currency",
      "tool": "Lexware invoice template (non-EU)"
    },
    {
      "id": "a1_bescheinigung",
      "title": "Apply for A1 certificate",
      "trigger": "eu_trip AND duration_days > 1",
      "lead_time_days": 14,
      "action": "Request A1 certificate from health insurer for the travel period",
      "tool": "Health insurer"
    },
    {
      "id": "scheinselbst_check",
      "title": "DRV clarification form for main client",
      "trigger": "client.share_of_revenue > 0.83",
      "action": "Submit DRV clarification form V0023 (quasi-employment status check)",
      "tool": "Deutsche Rentenversicherung"
    },
    {
      "id": "kunde_zahlt_nicht",
      "title": "Send payment reminder",
      "trigger": "invoice.due_date + 14 days exceeded",
      "action": "Create payment reminder (Lexware template), after further 14 days: 1st formal notice",
      "tool": "Lexware"
    },
    {
      "id": "neues_saas_tool",
      "title": "Sign GDPR data processing agreement",
      "trigger": "new_tool WITH personal_data_processing",
      "action": "Sign AVV (Auftragsverarbeitungsvertrag), update GDPR records of processing (VVT)",
      "tool": "GDPR documentation"
    }
  ]
}
```

---

## Bot Architecture Notes

For Marcel's `mdk_engineering_bot` Telegram reminder bot:

1. **Storage:** PostgreSQL with `obligation_instances` table (obligation_id, due_date, status, notified_at, acknowledged_at)
2. **Scheduler:** APScheduler with SQLAlchemyJobStore — daily check at 08:00 Europe/Berlin
3. **Notification logic:** For each obligation with `lead_time_days = X`: if today == due_date - X → send notification
4. **Dynamic anchor dates:** Professional liability and domain have individual expiry dates → set via `/anchor` Telegram command
5. **Acknowledge flow:** Bot asks "Done? /done" → marks in DB, next reminder only at next cycle
6. **Escalation:** For `mandatory: true` and not acknowledged after due date → re-notify daily
7. **Holiday shifting:** Any computed due date falling on a Saturday, Sunday, or German federal/Bavarian holiday is shifted to the next business day (python-holidays, country='DE', subdiv='BY')
