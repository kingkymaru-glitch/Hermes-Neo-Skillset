# <PROJECT> — Function Map & Version Check

> Purpose: single reference for the current state of <PROJECT> before the codebase
> is duplicated / handed off / modified. Everything below reflects the code as it
> exists in this repo (branch `<branch>`) at the time of writing. No API keys,
> IPs, or credentials are included — only structure and behaviour.

---

## 1. Version Check

| Field | Value | Where |
|-------|-------|-------|
| App version constant | `<APP_VERSION>` | `<file:line>` |
| `package.json` version | `<0.0.0>` | `package.json` |
| Git tag | `<vX.Y.Z>` @ `<sha>` | `git tag` |
| HEAD | `<sha>` — **<N> commits ahead** of the tag on `<branch>` | `git describe` |
| Node engine | `<range>` | `package.json` |
| Dev server | `<tool> on port <port>` | `<config>` |
| Lint / build | `<cmd>` (<status>) | verified <date> |

**Verdict:** <one-line statement of any version mismatch and the recommended fix>.

---

## 2. What <PROJECT> Is (one paragraph)

<Plain-language summary of what the app does and who it's for.>

---

## 3. Architecture at a Glance

```
<Browser/Server> 
 ├─ <major subsystem>  → <config/registry file>
 ├─ <major subsystem>  → <bridge/server> → <external store>
 └─ <persistence> (optional)
```

Key design rules baked into the code (important when modifying):
- <fail-open / graceful-degradation / registry-first etc.>

---

## 4. Function Map (by area)

### 4.1 <Area>
| Function | What it does | Status | Location |
|----------|--------------|--------|----------|
| `<name>` | <one line> | LIVE / SCAFFOLD / NOT BUILT | `<file:line>` |

(repeat 4.2, 4.3 … for each area)

---

## 5. Feature Status Summary

| Area | Live | Scaffold / Disabled | Not built |
|------|------|---------------------|-----------|
| <area> | ✅ | <gated item> | <missing> |

---

## 6. Notes for Duplication & Modification

1. **Version:** <bump advice>.
2. **Add a <feature type>:** <one-line edit location>.
3. **Swap storage/backend:** <swap path + unchanged contract>.
4. **Env vars used:** <list>.
5. **Ports:** <port> (avoid <clashing port> — <reason>).
6. **Crash history:** <technique avoided> → <error> → <workaround>.

---
*Generated <date> from the `<repo>` repo at HEAD `<sha>`. Verify against
`git log` / lint / build after any edits.*
