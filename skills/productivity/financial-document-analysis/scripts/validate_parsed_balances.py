#!/usr/bin/env python3
"""Validate parsed bank-statement balances before reporting any of them.

Two checks that catch the failures that silently produce wrong cash curves:

  1. FOOTER-CONTAMINATION  - a statement's closing balance must not equal that
     statement's TOTAL DEBIT or TOTAL CREDIT. Footer lines look exactly like
     amounts, so a parser that falls back to "last amount in the file" adopts
     one. This check catches that bug on its own.
  2. CHAIN CONTINUITY     - opening balance of statement N+1 must equal closing
     balance of statement N for the same account.

A third, optional check reconciles the combined bank total per month against an
independent figure (audited "cash at bank" line) so you can state the residual
instead of guessing it.

Usage:
    python3 validate_parsed_balances.py parsed.csv [--expected expected.csv]

parsed.csv columns:  account,month,opening,closing,total_debit,total_credit
expected.csv columns: month,total

Blank/'-' numeric cells are ignored. Amounts may be plain or thousands-separated.
Exit code 1 if any check fails.
"""
import csv
import sys
from collections import defaultdict


def num(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if s in ("", "-", "None", "nan"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load(path, required):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    missing = [c for c in required if c not in (rows[0].keys() if rows else [])]
    if missing:
        sys.exit(f"{path}: missing columns {missing}")
    return rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    rows = load(args[0], ["account", "month", "opening", "closing"])

    failures = []
    per_month = defaultdict(float)
    per_month_has = defaultdict(bool)
    by_acct = defaultdict(list)

    for r in rows:
        acct, mo = r["account"].strip(), r["month"].strip()
        opening, closing = num(r.get("opening")), num(r.get("closing"))
        tdeb, tcred = num(r.get("total_debit")), num(r.get("total_credit"))

        # Check 1: closing balance must not be a footer total
        for label, footer in (("TOTAL DEBIT", tdeb), ("TOTAL CREDIT", tcred)):
            if closing is not None and footer is not None and abs(closing - footer) < 0.01:
                failures.append(
                    f"FOOTER CONTAMINATION: {acct} {mo} closing {closing:,.2f} "
                    f"== {label} {footer:,.2f} -- parser read a footer line as the balance"
                )

        if closing is not None:
            per_month[mo] += closing
            per_month_has[mo] = True
        by_acct[acct].append((mo, opening, closing))

    # Check 2: opening(N+1) == closing(N)
    def key(m):
        try:
            y, mm = m.split("-")
            return (int(y), int(mm))
        except Exception:
            return (0, 0)

    for acct, stmts in sorted(by_acct.items()):
        stmts.sort(key=lambda s: key(s[0]))
        for (m0, o0, c0), (m1, o1, c1) in zip(stmts, stmts[1:]):
            if c0 is not None and o1 is not None and abs(o1 - c0) >= 0.01:
                failures.append(
                    f"CHAIN BREAK: {acct} closing {m0} = {c0:,.2f} but opening {m1} "
                    f"= {o1:,.2f} (diff {o1 - c0:,.2f})"
                )

    print(f"statements checked : {len(rows)}")
    print(f"accounts           : {len(by_acct)}")
    print(f"months             : {len(per_month)}")
    print()
    print("combined closing balance per month:")
    for mo in sorted(per_month, key=key):
        print(f"  {mo}  {per_month[mo]:>18,.2f}")

    # Optional check 3: reconcile against an independent figure
    if "--expected" in sys.argv:
        exp = load(sys.argv[sys.argv.index("--expected") + 1], ["month", "total"])
        print()
        print("reconciliation vs independent figure:")
        for r in exp:
            mo = r["month"].strip()
            want = num(r["total"])
            got = per_month.get(mo)
            if got is None:
                print(f"  {mo}  no parsed data")
                continue
            diff = got - want
            flag = "OK" if abs(diff) < 1.0 else ("CHECK" if abs(diff) < 100000 else "MISMATCH")
            print(f"  {mo}  bank {got:>14,.2f}  books {want:>14,.2f}  diff {diff:>12,.2f}  {flag}")
            if flag == "MISMATCH":
                failures.append(f"RECONCILIATION MISMATCH at {mo}: diff {diff:,.2f}")

    print()
    if failures:
        print(f"FAILED - {len(failures)} problem(s):")
        for f_ in failures[:40]:
            print("  -", f_)
        if len(failures) > 40:
            print(f"  ... and {len(failures) - 40} more")
        sys.exit(1)
    print("PASSED - balances are internally consistent and free of footer contamination.")


if __name__ == "__main__":
    main()
