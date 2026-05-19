# Freelancer Setup — Open Todos & Checklist

**Marcel Kück — Software Engineering & IT-Consulting**
Last updated: 19 May 2026

---

## Master Data

| Item | Value |
|---|---|
| Tax number (Steuernummer) | 117/241/61679 (FA Fürstenfeldbruck) |
| VAT ID (USt-IdNr) | DE462191226 (valid from 09.05.2026) |
| Economic ID (W-IdNr) | DE462191226-00001 |
| Business account | N26 Business (IBAN DE39 1001 1001 2652 8585 14) |
| Accounting software | Lexware Office XL |
| VAT filing period | Quarterly |

## Tax Registration Estimates (from Fragebogen zur steuerlichen Erfassung)

| Item | 2026 (founding year) | 2027 (following year) |
|---|---|---|
| Self-employed profit | €10,000 | €20,000 |
| Special deductions | €1,000 | €2,000 |
| Estimated turnover | €12,000 | €25,000 |
| Estimated VAT liability | €1,500 | — |

---

## Completed ✅

- [x] ELSTER account created and verified (online ID)
- [x] Tax registration form fully completed and submitted
- [x] Lexware Office XL subscription activated (with API)
- [x] N26 Business account opened
- [x] Website: www.marcelkueck.dev live
- [x] Service description: "Conception, architecture and development of individual software and system solutions. Technical consulting and scientific analysis, particularly in the fields of AI and robotics."
- [x] Opted out of Kleinunternehmer scheme (standard VAT scheme, 5-year binding)
- [x] Istversteuerung approved (VAT due when payment received)
- [x] VAT ID applied for and received: DE462191226
- [x] Profit calculation method: EÜR (income-surplus accounting)
- [x] Tax number received: 117/241/61679
- [x] Economic ID (W-IdNr) received: DE462191226-00001 (keep the BZSt letter)
- [x] Lexware Office connected to N26 (automatic transaction import active)
- [x] Invoice template created in Lexware Office
- [x] Tax number entered in Lexware: 117/241/61679
- [x] VAT ID entered in Lexware: DE462191226
- [x] SEPA direct debit mandate submitted to FA Fürstenfeldbruck (15.05.2026 via ELSTER "Sonstige Nachricht", processing ~2 weeks)
- [x] VAT ID registered with Google Workspace (Reverse Charge applies from June invoice onwards)
- [x] Lexware UStVA settings: quarterly + direct debit

---

## Still Open — This Week

### 1. Health Insurance Clarification ⚠️ URGENT

**Why urgent:** At age 27 it is unclear whether Beihilfe eligibility through Marcel's mother (civil servant teacher in Hamburg) still applies. Without clarification: the AXA supplemental policy only covers ~20–30% of costs if Beihilfe lapses.

**Call 1 — Beihilfestelle Hamburg** (HR department of mother's employer or Zentrum für Personaldienste Hamburg):
- Am I still eligible for Beihilfe as a 27-year-old child of a civil servant? Until when exactly?
- Do I lose eligibility by starting self-employed work?
- Is there an income threshold?

**Call 2 — AXA:**
- Which exact tariff am I currently on (supplemental policy or full private insurance)?
- If Beihilfe lapses: can I switch to a full private health insurance tariff at AXA? What would it cost?
- Are there deadlines for the tariff switch?
- Do I have a right to switch tariffs under §204 VVG?

**Options if Beihilfe lapses:**
- Full private insurance tariff at AXA (tariff switch) — advantage: existing claims history preserved
- New private insurance provider — possibly cheaper, but health assessment required
- Voluntary statutory health insurance (GKV) — check if switch is still possible (deadline: 3 months after end of compulsory insurance)

### 2. Professional Liability Insurance

**What:** Vermögensschadenshaftpflicht for IT freelancers. Covers financial damages caused by errors in your software or consulting work.

**Recommended coverage:** €1–3M

**Estimated cost:** ~€250–600/year

**Compare:** Hiscox, Markel, exali.de (specialised in IT freelancers)

**Must be done before first client project!**

### 3. First Invoice to May Clients

All required fields (tax number, VAT ID, bank details) are set up in Lexware. Before invoicing EU clients:
- Validate client VAT ID at https://evatr.bff-online.de (your own + the client's)

Per invoice, check where the client is located:
- **Germany:** Include 19% VAT
- **EU B2B:** Net amount without VAT, note "Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge)", include both VAT IDs, report in ZM
- **Non-EU (USA, UK, CH):** Net amount without VAT, note "Nicht steuerbare Leistung gemäß § 3a UStG"

---

## First VAT Pre-Filing: Q2 2026 → Due 10.07.2026

**Filing period: quarterly** (May + June = Q2 2026, since business started 01.05.)

Even with no revenue, filing is mandatory. Input VAT (Vorsteuer) from expenses can be reclaimed → refund from the tax office.

**Process in Lexware:**
1. Collect and book all May + June receipts (Lexware, mobile, Google Workspace, domain, etc.)
2. Early July: open "Umsatzsteuer-Voranmeldung" module → select Q2 2026
3. Review figures (turnover €X, input VAT €Y, refund/liability €Z)
4. Submit via ELSTER interface in Lexware
5. For Reverse Charge inbound services (Google Workspace from June onwards): self-assess VAT + deduct as input tax simultaneously (net zero)

With active SEPA mandate, the tax office will automatically refund any excess input VAT to N26.

**Future-proofing note:** If your actual 2026 VAT liability stays below €2,000, you can apply for a **full exemption from quarterly filing** for 2028 (§18 Abs. 2 UStG) — only annual return needed. Worth applying for once the 2026 assessment is done.

---

## Recurring Obligations Overview

### Quarterly

| Quarter | Period | Due date |
|---|---|---|
| Q2 2026 | May + Jun | **10.07.2026** |
| Q3 2026 | Jul–Sep | **12.10.2026** (10.10. = Saturday) |
| Q4 2026 | Oct–Dec | **11.01.2027** (10.01. = Sunday) |
| Q1 2027 | Jan–Mar | **12.04.2027** (10.04. = Holy Saturday) |

Recapitulative statement (ZM) is due on the 25th of the month after each quarter — only required if EU B2B revenue exists.

### Quarterly ESt Prepayments (if set by tax office)
Due: 10 March / 10 June / 10 September / 10 December. For 2026 likely €0 (profit below Grundfreibetrag ~€12,096). From 2027: probably ~€250–325/quarter based on €20k estimate.

### Annual
- **Annual tax return:** 31 July of following year (without tax advisor) or end of February of the year after (with tax advisor)
  - Components: Einkommensteuererklärung (Anlage S + Anlage EÜR) + annual VAT return
  - EÜR generated automatically by Lexware
  - Recommendation: hire a tax advisor for the first year (~€800–1,500)
- **Health insurance income proof:** Send tax assessment notice to health insurer after receiving it — premium adjusted to actual income
- **Year-end fixed assets inventory:** 31 December — check GWG (items ≤€800 net can be immediately expensed)

---

## Tool Setup

| Tool | Function | Cost |
|---|---|---|
| Lexware Office XL | Accounting, invoices, EÜR, UStVA, receipts, DATEV, API | ~€15–20/month |
| N26 Business | Business account | €0/month |
| ELSTER (Mein ELSTER) | Tax returns, UStVA submission, ZM, SEPA | €0 |
| Toggl Track (Free) | Time tracking per project/client | €0 |
| Wise (if needed) | International payments USD/GBP | €0 account |

**Total tool costs: ~€15–20/month** (plus insurance and optional tax advisor)

---

## International Invoicing — Quick Reference

### EU Clients (B2B, with VAT ID)
- Reverse Charge: net invoice without German VAT
- Invoice note: "Steuerschuldnerschaft des Leistungsempfängers"
- Include both VAT IDs (yours: DE462191226)
- Report in ZM (Recapitulative Statement)
- Before first invoice: validate client VAT ID at https://evatr.bff-online.de and save the PDF confirmation

### Non-EU Clients (USA, UK, CH etc., B2B)
- Net invoice without VAT
- Invoice note: "Nicht steuerbare Leistung gemäß § 3a UStG"
- Report in UStVA under line 45 (Kennziffer 45)
- Check double taxation treaty for withholding tax risk
- For foreign currency payments: use Wise account

### Working Physically Abroad
- Short stays (4–8 weeks/year) usually no issue
- Tax residence must remain in Germany (primary home Gröbenzell)
- For EU trips: apply for A1 certificate from health insurer
- For longer stays: consult tax advisor (183-day rule, permanent establishment risk)

---

## Notes

- **W-IdNr DE462191226-00001:** New since November 2024. Will gradually replace the Steuernummer for communication with authorities. Keep the BZSt letter. If further business activities are registered, BZSt will issue additional distinguishing marks (00002, 00003 …).
- **Oxford internship:** Separate from freelance status. If paid, declare as non-self-employed income (nichtselbständige Einkünfte) in the annual tax return. Check whether an A1 certificate is needed for UK (not an EU country post-Brexit).
- **Pension insurance:** Not mandatory for software freelancers in principle. But: if >5/6 of revenue comes from one single client, mandatory contributions may apply as "arbeitnehmerähnlicher Selbständiger". Submit DRV clarification form V0023 once the first contract is running.
- **Lexware Business Account:** The Lexware Business Account would have been a better long-term choice than N26 (native Lexware integration, smart tax reserve split). Consider switching later.

---

## Prompt: Health Insurance Clarification
(Copy into a new Claude chat)

I need help clarifying my health insurance situation. Here is my setup:

**Current insurance:**
- I am 27 years old (born 21.04.1999), living in Gröbenzell (Bavaria)
- My mother is a civil servant teacher in Hamburg
- I am covered through her via AXA private insurance (presumably Beihilfe supplement: Hamburg Beihilfe covers ~80%, AXA the remaining ~20%)
- There has been recent confusion — the Beihilfe/insurer has stopped covering some services, and it is unclear exactly how I am currently insured

**What is changing:**
- I registered as a freelancer (software development & IT consulting) in Germany on 01.05.2026
- Tax number 117/241/61679 (FA Fürstenfeldbruck), VAT ID DE462191226
- I expect earnings of approx. €10,000–20,000 profit in the first year

**What I need to clarify:**

1. **Beihilfestelle Hamburg:**
   - Am I still eligible for Beihilfe as a 27-year-old child of a civil servant? Until when?
   - Do I lose eligibility by taking up self-employed work?
   - Is there an income threshold?
   - Who is the correct contact — the HR department of my mother's school or the Zentrum für Personaldienste Hamburg?

2. **AXA:**
   - Which exact tariff am I currently on (supplemental policy or full tariff)?
   - If Beihilfe lapses: can I switch to a full private health insurance tariff at AXA, and what would it cost?
   - Are there deadlines for the tariff switch?
   - Do I have a right to switch tariffs under §204 VVG?

3. **General options if Beihilfe lapses:**
   - Full private tariff at AXA (tariff switch) vs. new private insurer vs. voluntary statutory (GKV) — what makes most sense for a 27-year-old solo freelancer with ~€20,000 annual profit?
   - What are the respective costs?
   - Can I even switch to statutory (GKV) or am I locked into private insurance?

Please help me work through this systematically, identify the right contacts, and prepare a call script for the conversations with the Beihilfestelle and AXA.
