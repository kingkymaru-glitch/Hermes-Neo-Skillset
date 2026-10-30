# Cost Table Integrity

Reference for the numeric-audit step of proposal work. Companion script:
`scripts/verify_cost_tables.py`.

## Why this matters

Cost tables in these proposals are edited dozens of times in one sitting. The user issues a long
sequence of small corrections — "change RasPi5 to ROVER-KIT", "add solar", "split integration",
"reduce sensor unit price to RM1000", "increase Mac Mini to 4". Each edit touches one row. The
column total is almost never revisited. The result is a document whose line items no longer sum
to its own stated total.

Two independent totals were wrong in the ARRAS session alone. Both were introduced by edits, not
by the original drafting.

## The three failure modes

### 1. Duplicate line items

After several revisions the same cost exists twice under two names.

Real example:

    | Integration cost            | 10 sites | 5,000 | 50,000 |
    | Integration and commissioning | 10 sites | 5,000 | 50,000 |

One RM50,000 charge, entered twice. The printed total had been computed before the second row
appeared, so the table silently over-stated CAPEX by RM50,000.

Detection: compare normalised row labels for repeats. Near-miss labels ("Integration cost" vs
"Integration and commissioning") share a keyword and a value — check value collisions too, not
just exact string equality.

### 2. Variable items folded into a "fixed" total

A per-call or as-triggered line is summed into a subtotal that its own note says to exclude.

Real example:

    | Calibration service (per site per call) | 3,000 | Excluding claimable costs; triggered per site as needed |
    | **Total OPEX (fixed)**                  | **817,000** | Excluding per-site calibration calls |

The line items actually summed to RM814,000. The RM3,000 per-call row had been added into the
fixed subtotal, contradicting the note printed on the very next line.

Detection: if a row's text contains "per call", "per site per call", "as needed", "triggered",
"per unit", or "per session", it is variable and must be excluded from any total labelled
"fixed".

### 3. Schema mismatch on pasted rows

A row copied from a cost table (Item | Quantity | Unit Cost | Total) into the equipment datasheet
table (Item | Purpose | Key Specifications | Integration) puts "1" into Purpose and "[tbd]" into
Specs. The row renders but is meaningless.

Detection: verify the row's cell count and column semantics against the header before inserting.

## Procedure

1. Run `scripts/verify_cost_tables.py <proposal.md>` before declaring the document done.
2. Fix every discrepancy it reports, re-running until clean.
3. Re-verify after ANY subsequent user edit to a cost figure, however small.

## Rule of thumb

If the user changes a number, recompute the total. Do not defer it. A wrong figure in a client
proposal is worse than a missing feature — it discredits every other number in the document.
