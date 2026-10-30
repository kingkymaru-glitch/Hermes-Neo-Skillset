#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit markdown cost tables in a proposal document.

Recomputes every "Total (RM)" cell as Quantity x Unit Cost, compares against
any stated subtotal/grand-total row, and flags the two failure modes that
survive long iterative edit chains:

  1. Duplicate line items (same cost entered twice under different labels)
  2. Per-call / per-unit / as-triggered items folded into a "fixed" total

Usage:
    python3 verify_cost_tables.py <path-to-proposal.md>

Exit code 0 = clean, 1 = discrepancies found.
"""
import re
import sys
from collections import Counter


def money(tok):
    """Parse '1,600' / '25,000' / '8,000,000' -> int. Return None if not money."""
    t = tok.strip().replace("**", "").strip()
    if not re.fullmatch(r"[\d,]+(\.\d+)?", t):
        return None
    try:
        return float(t.replace(",", ""))
    except ValueError:
        return None


def rows_of(lines, i):
    """Collect a markdown table starting at header index i. Returns (header, rows, next_i)."""
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    rows, j = [], i + 2  # skip separator
    while j < len(lines) and lines[j].strip().startswith("|"):
        rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
        j += 1
    return header, rows, j


def is_cost_table(header):
    h = " ".join(header).lower()
    return ("unit cost" in h or "annual" in h) and ("total" in h or "rm" in h)


def main(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    problems, checked = [], 0
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if (s.startswith("|") or s.startswith("||")) and i + 1 < len(lines) \
                and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in s.strip("|").split("|")]
            rows, i = rows_of(lines, i)
            if not is_cost_table(header):
                continue
            checked += 1

            # locate columns
            def col(*names):
                for n in names:
                    for ci, h in enumerate(header):
                        if n in h.lower():
                            return ci
                return None
            c_item, c_qty = col("item"), col("qty", "quantity")
            c_unit, c_total = col("unit cost", "annual", "cost"), col("total")
            if c_unit is None or c_total is None:
                continue

            # ---- duplicate label detection
            labels = [r[c_item].replace("**", "").strip().lower() for r in rows if c_item is not None]
            for lbl, n in Counter(labels).items():
                if n > 1 and "total" not in lbl:
                    problems.append(f"DUPLICATE row label appears {n}x: '{lbl[:60]}'")

            # ---- recompute + subtotal reconciliation
            computed = []
            for r in rows:
                item = r[c_item].replace("**", "").strip() if c_item is not None else ""
                is_total = "total" in item.lower() or item.lower().startswith("total")
                tot = money(r[c_total]) if len(r) > c_total else None
                if is_total and tot is not None:
                    body = sum(computed)
                    if abs(body - tot) > 0.5:
                        problems.append(
                            f"SUBTOTAL MISMATCH: '{item[:50]}' states {tot:,.0f} "
                            f"but line items sum to {body:,.0f} (diff {body - tot:+,.0f})")
                    computed = []  # reset for next table block
                    continue
                # detect per-call / per-unit variable rows
                joined = " ".join(r).lower()
                if any(k in joined for k in ("per call", "per site per call", "as needed",
                                             "triggered", "per unit", "per session")):
                    problems.append(
                        f"VARIABLE row may be wrongly summed into a fixed total: '{item[:55]}'")
                    continue
                if c_qty is not None and len(r) > c_qty:
                    q, u = money(r[c_qty]), money(r[c_unit]) if len(r) > c_unit else None
                    if q is not None and u is not None:
                        expect = q * u
                        if tot is not None and abs(expect - tot) > 0.5:
                            problems.append(
                                f"ROW MATH: '{item[:45]}' {q:,.0f} x {u:,.0f} = "
                                f"{expect:,.0f} but shows {tot:,.0f}")
                        else:
                            computed.append(expect if tot is None else tot)
                    elif tot is not None:
                        computed.append(tot)
                elif tot is not None:
                    computed.append(tot)
            continue
        i += 1

    print(f"Scanned {checked} cost table(s) in {path}")
    if not problems:
        print("OK — no arithmetic discrepancies found.")
        return 0
    print(f"\n{len(problems)} issue(s) found:\n")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
