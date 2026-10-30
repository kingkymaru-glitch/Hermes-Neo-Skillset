---
name: financial-document-analysis
description: "Use when reading audit packs, financial statements."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [audit, financial-statements, accounting, mpers, mfrs, due-diligence, ocr]
---

# Reading financial document packs (audit submissions, management accounts)

## When to Use

- The user points at a folder / zip of accounting documents — an audit submission,
  management accounts, chart of accounts, audited financial statements.
- You are asked to reconcile bank statements against the books.
- You are asked "read all the documents in that folder" for a company.
- You need to know what a company's real financial position is from its own paperwork.

Not for: a single P&L someone pastes into chat (answer it directly).

## Procedure

### 1. Inventory before reading anything

Large packs are 1,000+ files / hundreds of MB. Never open them file by file into
context.

1. List the archive contents (`unzip -l`, or extract to scratch first).
2. Produce counts by **file type** and by **folder**, so you can see the shape:
   primary statements vs supporting evidence (invoices, vouchers, payroll, photos).
3. Identify the **entities** in the pack (parent + subsidiaries + associates) and the
   **auditor** — both come out of the folder names and the report cover pages.
4. Build a file index JSON (`{rel, size, ext}`) once and grep it repeatedly instead of
   re-walking the tree.

### 2. Classify what is primary vs supporting

**Primary — read these in full, in this order:**

1. Independent auditor's report (opinion type, framework, date, any qualification)
2. Directors' Report (share issues, directors, remuneration, dividends)
3. Statement of comprehensive income / P&L
4. Statement of financial position / balance sheet
5. Statement of cash flows
6. Notes to the accounts — especially: investment in subsidiaries, preference
   shares, advance for shares, related party transactions, lease liability,
   basis of preparation / going concern
7. Statement of changes in equity

**Supporting — search, don't read:** invoices, payment vouchers, payroll files,
bank reconciliations, stock cards, fixed-asset photos, tenancy and loan agreements,
journal entries. Targeted `search_files` on the index for a specific question.

### 3. Extract text, OCR what has none

`pymupdf` extracts text-layer PDFs. Anything returning ~0 characters is scanned and
needs OCR. Auditor's reports, signed agreements and monthly journal-entry bundles are
very often scanned. See the `macos-tcc-protected-folder-access` skill for the
Swift + Vision OCR recipe that needs no tesseract.

Do not assume a 0-character PDF is corrupt or encrypted — distinguish the two:
scanned PDFs open fine and just have no text layer; encrypted ones raise on read.

### 4. Reconcile derived figures against the books

**The strongest verification available: bank-statement-derived balances must tie to
the audited balance sheet to the cent.** Do this before reporting any cash figure.

- Parse the explicit `ENDING BALANCE` line; never infer a closing balance from
  "the last amount in the file" (statement footers carry `TOTAL DEBIT` /
  `TOTAL CREDIT` lines that look exactly like amounts).
- Validate the chain: opening(N+1) == closing(N) per account.
- Compare the combined bank total to the audited "cash at bank" line. A residual
  equal to one small account you did not parse is a clean result — say so.
- Run `scripts/validate_parsed_balances.py` before reporting balances or cash curves.

### 5. Report coverage precisely — what was read, what was not, and why

The user asks "have you read all of it?" and means it. Answer with counts and
explicit gaps:

- Total files, and how many were read in full vs searched vs not readable.
- Anything unreadable, and the reason (password-protected, scanned, absent).
- Anything genuinely absent (no statements for a period) distinguished from anything
  you failed to parse.

Never imply completeness. "Everything readable, yes — those 3 are locked" is the
correct shape; "yes" is not.

### 6. Correct your own earlier numbers explicitly

If you find an error in figures you already sent, lead the next reply with the
correction, state what was wrong, and give the verified replacement. Do not quietly
swap in better numbers. A retracted figure costs a little trust; a silent wrong one
costs a lot.

7. **Rebuilding a broken management account (when the ECOUNT/draft is wrong)**

1. **Use the prior audited year as the classification template.** Same line items, same structure. The 2025 audited income statement is the map; every 2026 bank outflow must hit one of its lines.
2. **Extract all bank outflows for the target period.** Parse the bank statements (see `macos-tcc-protected-folder-access` skill for parsing rules). Verify balances against the audited balance sheet first.
3. **Read the actual ECOUNT P&L and Balance Sheet** (not just the draft/MA). The ECOUNT income statement has the detailed line-item breakdown (e.g., Sales - Field Service Operation, Cost of Sales - ROV Offshore Services, Payroll & Staffing Cost, Professional Fees, etc.) that the MA should mirror. The ECOUNT balance sheet has the exact receivables, payables, accruals, and cash figures. Use these as the baseline, then apply corrections on top.
4. **Read the ECOUNT journal entries** for the target period. These show how each transaction was classified in the system. Extract the unique account names to verify the chart of accounts is complete. Cross-check journal entry classifications against bank descriptions — where they don't match, that is a misclassification.
5. **Classify each outflow.** Use the description text to determine the MA line. Cross-check against WhatsApp payment request chats (date + amount match) and invoice/voucher references in the description. Cross-check against ECOUNT journal entries for the classification the system used.
6. **Build monthly columns.** Aggregate by month and MA line. Compare against the ECOUNT draft — where the bank says RM X went out but the MA shows RM Y in that line, that is the gap.
7. **Flag unverified payments.** Any bank outflow with no matching WhatsApp request or voucher reference goes into a "flagged" list. Report the total and the percentage of total outflows.
8. **Check the big expense lines for plausibility.** Depreciation should not be zero if assets exist. Tax should not be zero if profit is positive. COS should be in the same ballpark as the prior year (relative to revenue). Intercompany payments must be explicitly classified.
9. **Reconcile cash: bank-verified vs ECOUNT.** Build a per-account comparison table: bank-verified balance vs ECOUNT balance for each bank account. Any difference needs investigation. A negative bank balance in ECOUNT (e.g., Maybank Masai -RM16,343) is a red flag.
10. **Read the ERP dashboard for vendor/customer-level detail.** If the company uses an ERP (e.g., ECOUNT, AutoCount), check for an exported dashboard or report that shows vendor-level purchases and customer-level sales with monthly breakdowns. This reveals: (a) which vendors are intercompany (IRG, SCANDI, UPCON often appear in the top 5), (b) which vendor is the catch-all "unclassified" account, (c) revenue concentration by customer. The ERP income statement shows aggregate figures; the dashboard shows who the money went to and came from. Compare the dashboard total to the income statement total — a large discrepancy (e.g., dashboard RM18.39M sales vs income statement RM9.12M) usually means intercompany sales are included in the dashboard but eliminated in the income statement. This is expected but must be documented.

### 8. Building a cross-linked xlsx management account (when the deliverable is a workbook)

When the user wants a corrected management account as an Excel workbook (not a markdown report):

1. **One workbook, 5-8 sheets:** Notes & Accuracy, P&L Statement, Balance Sheet, Ledger, Flagged Items, Fixed Asset Schedule, Intercompany Recon, Cash Reconciliation.
2. **Cross-sheet formula links** — never hardcode values that exist on another sheet:
   - Balance Sheet Cash = `=SUM(Ledger!F:G)` (or the cash-account subset)
   - Balance Sheet Net Fixed Assets = `=Fixed Assets + Accumulated Depreciation`
   - Balance Sheet Total Assets = `=Net Fixed Assets + Total Current Assets`
   - P&L Total Sales = `=SUM(sales lines)`
   - P&L Gross Profit = `=Total Sales - Total COS`
   - P&L Net Income = `=Net Before Tax - Tax`
   - Flagged Items Amount = `=Ledger!F{row}` or `=Ledger!G{row}` (cell reference, not value)
   - Ledger Running Balance = `=H{prev}+IF(F{r}="",G{r},-F{r})`
3. **Traceability markers in an adjacent column** (not in the value cell, so formulas still work):
   - `*` = verified from bank statement (amount traced to the cent)
   - `!!` = known error or discrepancy (depreciation not posted, COS understated, etc.)
   - `??` = no trail found (no WhatsApp request, no PO/PR reference, no invoice)
   - Colour-code: green for *, yellow for ??, red for !!
4. **Flagged Items sheet** lists every ?? and !! transaction with: date, bank, amount (formula-linked to Ledger), description, reference, flag, reason, and ledger row number.
- **Set `fullCalcOnLoad`** so Excel/LibreOffice recompute on open (openpyxl never evaluates formulas).
- **Password-locked bank statements:** try the password before reporting them as unreadable. Common pattern: RHB statements use a password derived from account details. Ask the user if you don't have it.
- **Legends on every sheet where marks are used.** The user wants a legend row at the top of each sheet (Notes, P&L, BS, Ledger, Flagged Items) explaining *, !!, ?? — not just on the Notes sheet. An auditor reviewing any single sheet in isolation must know what the markers mean without cross-referencing.

## Pitfalls

- **A clean, unqualified audit opinion is NOT evidence the accounting is right.** It
  means the auditor accepted the treatment. Read the notes and the Directors' Report
  anyway — that is where the aggressive classifications live.
- **Framework matters.** A Malaysian private entity reports under **MPERS**, not
  MFRS. Citing the wrong standard in your analysis is itself an error — and an
  internal memo citing a standard that does not apply to the reporting framework is
  a finding in its own right.
- **Notes carry the substance; statements carry the summary.** Preference-share
  classification, advance-for-shares, going-concern dependence, related-party leases
  and output-sharing arrangements never appear in the P&L.
- **An unallotted share subscription presented as equity is a red flag, not a
  formality.** Money received for shares that have not been issued and not filed with
  the companies registry is, on the face of it, a liability until allotment completes.
- **A "DRAFT" or "INCOMPLETE" management account can show zero depreciation and
  zero tax.** Its net income is not a profit figure. Check that the main expense
  lines are actually populated before quoting it. Also check that cost-of-sales is
  plausible relative to revenue (a 19% COS ratio when the prior year was 42% is a
  red flag for missing costs).
- **Read the actual ECOUNT P&L and Balance Sheet, not just the draft/MA.** The
  ECOUNT income statement has the detailed line-item breakdown that the MA should
  mirror (Sales - Field Service Operation, Cost of Sales - ROV Offshore Services,
  Payroll & Staffing Cost, Professional Fees, etc.). The ECOUNT balance sheet has
  the exact receivables, payables, accruals, and cash figures. Use these as the
  baseline, then apply corrections on top. The draft/MA is a summary; the ECOUNT
  statements are the source of truth for line-item detail.
- **ECOUNT journal entries reveal the classification logic.** Each journal entry
  shows the account name, vendor, amount, and remark. Extracting unique account
  names from the journal entries verifies that the chart of accounts is complete
  and that transactions are classified consistently. Where the journal classification
  doesn't match the bank description, that is a misclassification to flag.
- **Confirm the depreciation gap from the fixed asset register, not just the MA.**
  If the fixed asset schedule shows ~RM103K/month depreciation but the MA shows zero,
  the gap is confirmed — not suspected. The fixed asset register is the evidence;
  the MA is the symptom. Always cross-check both before reporting the gap.
- **Retained earnings must be rolled forward.** Leaving retained earnings at a
  2-year-old figure (e.g., RM1,188,073 from 2024) when 2025 profit was RM636,999
  and 2026 is in progress is a material misstatement. An auditor will flag this
  immediately. Update it before any external reporting.
- **Intercompany payments need explicit classification.** Payments to subsidiaries
  (IRG, UPCON, SCANDI) are not automatically COS or management fee. Each must be
  mapped to: (a) cost of sales (subcontractor), (b) management fee, or (c)
  intercompany transfer (eliminated in consolidation). Leaving them unclassified
  inflates the apparent margin.
- **The "Other Non-Trade Creditors" account is a red flag.** When intercompany
  payments (RM843K in this case) sit in a catch-all "Other Non-Trade Creditors"
  account instead of being properly classified, the COS ratio is understated and
  the margin is inflated. Always check what's in the catch-all accounts — they
  often contain misclassified payments that should be in COS, management fees, or
  intercompany transfers.
- **The catch-all vendor in the ERP dashboard is the same problem at a different
  scale.** In 2025, the top "vendor" in the Ecount ERP dashboard was unclassified
  at RM8.53M — 50% of all purchases. This is the same pattern as the "Other
  Non-Trade Creditors" account in the balance sheet, just at the vendor level
  instead of the account level. When you see an unclassified vendor or account
  that is 30%+ of total purchases, that is a systemic classification failure, not
  a one-off. The fix is the same: reclassify every payment to its proper MA line.
- **Intercompany sales vs net sales discrepancy.** The ERP dashboard may show higher
  sales than the income statement because it includes intercompany sales that are
  eliminated in the consolidated income statement. This is expected but must be
  documented. Do not quote the dashboard sales figure as the company's revenue
  without noting the elimination.
- **Cash reconciliation: bank-verified vs ECOUNT.** Always build a per-account
  comparison table. ECOUNT cash (RM675,332) vs bank-verified cash (RM689,819) —
  the difference is timing. A negative balance in any account (e.g., Maybank Masai
  -RM16,343) needs immediate investigation. A dormant account (RHB, zero transactions
  since Aug 2025) should be flagged as potentially inactive.
- **A WhatsApp payment-request chat is a payment evidence layer, not just
  conversation.** Chats named "PAYMENT REQUEST" contain structured entries: date
  header, numbered request (D073, P071, etc.), entity, item, reference (PO/PR
  number), vendor, bank, account number, amount, remarks, and approval ("Proceed").
  Extract with awk by tracking the date header and collecting the
  Item/Reference/Vendor/Bank/Amount/Remarks fields. They are the "request" layer
  that links bank outflows to justifications.
- **Rebuilding a broken management account:** use the prior audited year as the
  classification template (same line items, same structure). For each bank outflow,
  determine which MA line it hits. Cross-check monthly totals against the ECOUNT
  draft. Where the bank says RM X went out but the MA shows RM Y in that line,
  that is the gap. Flag any bank outflow with no matching WhatsApp request or
  voucher reference.
- **Going-concern wording is a binary signal.** "Dependent on the continuous
  financial support from the director" means the entity cannot stand alone — treat
  it as such, and note the same entity often also has negative equity.
- **A qualified opinion names its scope.** "Except for … RM X unable to obtain
  sufficient appropriate audit evidence" tells you exactly which balance could not
  be verified. That is a documented gap, not a suspicion.
- **Related-party asset/liability pairs inflate the balance sheet symmetrically.** A
  right-of-use asset with a matching deferred liability from a related party, with
  **no fixed repayment amount or term**, adds size without adding substance.
- Do not read the whole pack into context. Extract to scratch, index, and read only
  the primaries plus whatever a targeted search turns up.

## Support files

- `references/malaysian-financial-reporting-notes.md` — MPERS vs MFRS, RCCPS
  equity-vs-liability, advance for shares, going concern, qualified opinions,
  related-party and right-of-use arrangements. Read when analysing a Malaysian pack.
- `references/audit-readiness-framework.md` — tiered checklist (Tier 1–4) for what an
  auditor needs to sign off on a broken management account. Read when the user asks
  "what would make this correct and ready for audit?" or when assessing audit readiness.
- `scripts/validate_parsed_balances.py` — checks parsed statement balances against
  the opening/closing chain and against footer totals. Run before reporting any
  balance or cash curve.
