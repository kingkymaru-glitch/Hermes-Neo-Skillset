#!/usr/bin/env python3
"""Static structural + decode-contract check for a Supabase .sql migration.

No Postgres on the CLI host, so this is NOT a real run — it validates the DDL is
well-formed and that decode-critical columns match the Swift Codable contract
(see references/supabase-swift-codable-contract.md). Usage:

  python3 verify_sql_static.py Supabase/shops.sql
  python3 verify_sql_static.py Supabase/shops.sql --must-jsonb availability --must-text shop_type

Exits 0 if balanced + all --must-* assertions pass, else 1.
"""
import re
import sys

def main(path, must_jsonb, must_text):
    sql = open(path).read()
    o, c = sql.count("("), sql.count(")")
    parens_ok = o == c
    q = sql.replace("''", "").count("'")
    quotes_ok = q % 2 == 0

    problems = []
    if not parens_ok:
        problems.append(f"UNBALANCED parens: {o} ( vs {c} )")
    if not quotes_ok:
        problems.append(f"UNBALANCED single-quotes: {q}")

    col_re = re.compile(r"^\s*([a-z_]+)\s+(text|uuid|double precision|integer|jsonb|timestamptz|boolean)", re.M)
    cols = dict(re.findall(col_re, sql))

    for name in must_jsonb:
        t = cols.get(name)
        if t != "jsonb":
            problems.append(f"column '{name}' must be jsonb (decode contract) — found {t}")
    for name in must_text:
        t = cols.get(name)
        if t != "text":
            problems.append(f"column '{name}' must be text (decode contract) — found {t}")

    blocks = re.findall(r"create policy[^\;]*\;", sql, re.S)
    n_owner = sum(1 for b in blocks if "auth.uid()" in b)

    print(f"file: {path}")
    print(f"  parens {o}/{c} -> {'OK' if parens_ok else 'BAD'}")
    print(f"  quotes -> {'OK' if quotes_ok else 'BAD'}")
    print(f"  columns ({len(cols)}): {sorted(cols)}")
    print(f"  policies: {len(blocks)}, owner-scoped: {n_owner}")
    if must_jsonb or must_text:
        print(f"  decode-contract assertions: {must_jsonb} jsonb, {must_text} text")

    if problems:
        print("RESULT: FAIL")
        for p in problems:
            print("  -", p)
        return 1
    print("RESULT: AD-HOC STRUCTURAL CHECK PASS (not a DB run)")
    return 0

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("usage: verify_sql_static.py <file.sql> [--must-jsonb c1 c2] [--must-text c1 c2]")
        sys.exit(2)
    path = args[0]
    must_jsonb, must_text = [], []
    i = 1
    while i < len(args):
        a = args[i]
        if a == "--must-jsonb":
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                must_jsonb.append(args[i]); i += 1
        elif a == "--must-text":
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                must_text.append(args[i]); i += 1
        else:
            i += 1
    sys.exit(main(path, must_jsonb, must_text))
