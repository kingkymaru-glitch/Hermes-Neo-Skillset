# Malaysian financial reporting — reading an audit pack

Topical notes for analysing a Malaysian private-entity audit submission. Distilled to
rules; read alongside the skill's procedure.

## Reporting framework: MPERS vs MFRS

- **MPERS** (Malaysian Private Entities Reporting Standard) is the framework for
  private entities that do not issue financial instruments to the public. Most SME
  audit reports state it in the auditor's opinion paragraph: "…in accordance with
  Malaysian Private Entities Reporting Standard and the requirements of the
  Companies Act 2016".
- **MFRS** is the full-IFRS-equivalent framework for entities that do public-issuance
  or are deemed public-interest. A private SME is normally **not** on MFRS.
- **Why it matters:** an internal memo or management note that justifies a
  classification "in accordance with MFRS 132" for a company reporting under MPERS
  is citing a standard that does not apply. That is worth reporting as its own
  finding — it tells you the reasoning was written for the reader, not the rules.
- MPERS financial instruments guidance is based on the older IAS 32 / IAS 39
  hierarchy, not the current MFRS 132 text. Do not quote MFRS paragraph numbers at a
  Malaysian SME.

## Preference shares: equity or liability?

This is the most common aggressive classification in a small-company audit pack.

The question is whether the instrument creates a **contractual obligation to deliver
cash**. Indicators that push it toward **liability**:

- a **cumulative** dividend (accumulates if not paid) — especially when the
  Directors' Report says holders are "entitled to a dividend of N% per annum"
- a **fixed redemption date** or a holder option to require redemption
- a **put option** or compulsory conversion

Indicators that support **equity**:

- conversion into ordinary shares at a future date
- redemption **at the issuer's discretion**, after a long period
- dividend payable **only when declared** by the directors

What to check in the pack:

1. The **Directors' Report** section "Issue of Shares and Debentures" gives the
   instrument count and issue price (e.g. 555,556 shares at RM18 = RM10,000,000).
2. The **preference-share note** states the equity/liability reasoning in the
   company's own words. Read it verbatim and compare it against the dividend and
   redemption terms stated elsewhere — they frequently contradict each other.
3. The **statement of changes in equity** shows the split, e.g. paid-up capital vs
   called-up capital vs advance for shares.
4. **An internal memo to the investor justifying a liability→equity reclassification
   is a governance finding on its own face.** Note whose stated purpose it gives —
   improving debt-to-equity, qualifying for grants, or pre-qualifying for tenders —
   and whether the cited standard applies to the framework actually used.

## Advance for shares

Money received from an investor for shares that have **not yet been allotted** and
**not yet filed** with the companies registry. It is normally a **liability** until
allotment completes.

Presenting it as equity inflates equity and understates liabilities. Check:

- Does the note say the allotment "has not been completed and not yet filed"?
- How long has the money been sitting there? Months to over a year is a long time.
- Does it appear in equity on the face of the balance sheet, or only in a note?

Cross-check against the bank statements: the received amount should appear as an
inward transfer with a description like "INVESTMENT" or "shares application",
and it may move between the company's own accounts before being spent.

## Going concern

Look for the basis-of-preparation note. Phrasing that matters:

- "…is dependent on the **continuous financial support from the director**" — the
  entity cannot meet its obligations alone. Treat it as a going-concern caveat even
  when the audit opinion itself is unqualified.
- "Material uncertainty exists" or "significant doubt" — stronger still.
- Silence is not assurance; a parent with resources may make a subsidiary's
  going concern unremarkable. Check the subsidiary's own balance sheet before
  concluding.

Correlate with: **negative equity**, near-zero cash, and reliance on director
loans. The three usually travel together.

## Audit opinion types

- **Unqualified / true and fair** — the auditor accepted the statements as presented.
  Says nothing about whether a classification is conservative or aggressive.
- **Qualified — "except for"** — names the specific balance that could not be
  verified, typically: "…are unable to obtain sufficient appropriate audit
  evidence pertaining to this balance because the detailed information was not made
  available during the audit." That is a **documented** gap: records existed but
  were withheld. Report the amount.
- **Adverse** — the statements are materially misstated.
- **Disclaimer** — the auditor could not form an opinion at all.
- Also check the **Key Audit Matters** and **Emphasis of Matter** paragraphs, and the
  auditor's report **date** versus the directors' report date — a long gap is worth
  noting.

A group report may be clean while a **subsidiary** is qualified. Check each entity
separately; subsidiaries audited by other firms are named in the notes.

## Related-party arrangements

- **Purchases from related parties** appear in their own note. A large year-on-year
  jump is a signal to trace.
- **Right-of-use assets with a matching deferred liability** from a related party,
  where the consideration "has no fixed repayment amount and term", add balance-sheet
  size without adding substance. Both sides should be found — an asset with no
  matching liability, or vice versa, is a different problem.
- **Output-sharing leases** ("commercial responsibility shared 30:70") mean the
  company books equipment it does not own. Check who insures it and who keeps the
  residual.
- **Joint development / joint operation / fully own asset** sub-accounts in the
  chart of accounts tell you how much of the asset base is genuinely the company's.
- **Amount owing by/to subsidiary and director** balances appear in the receivables
  and payables notes; they are usually unsecured and repayable on demand.

## Cash flow statement — the fastest reality check

Read it before the P&L for a sense of whether the business funds itself:

- **Net cash used in operating activities** negative while sales are large means the
  profit is not converting to cash.
- **Purchase of property, plant and equipment** is the capex line — compare it to
  the financing inflows to see what funded the asset base.
- **Proceeds from issuance of preference shares / borrowings** in financing shows
  where the money actually came from.
- Reconcile the year's **net increase/decrease in cash** against the movement in the
  bank-derived balances for the same period.

## What to check on receivables

- Gross trade receivables versus **revenue** — receivables growing faster than
  revenue, or growing while revenue falls, is a collection problem.
- The **ageing table** in the notes (not past due / 31-60 / 61-90 / over 90 days).
- The **provision for doubtful debts** held against that gross figure. A small
  provision against a large over-90-days balance is an under-provision signal.
- "Bad debt recoverable" appearing in other income means earlier provisions were
  released — check whether that is flattering the current-year profit.
