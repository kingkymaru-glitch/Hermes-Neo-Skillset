# RINA QA checklist — Admin tab + Org Chart tab

Exercise every button; record ✅ works / ❌ broken into FINDINGS.

## Admin tab (User Management = "normal organization")
| Button | Backing function | Verify |
|---|---|---|
| + Add user | `upsert_user_profile` | row appears in roster |
| Upload .xlsx | loop `upsert_user_profile` + `set_user_hierarchy` | bulk rows + hierarchy |
| Download sample | template download | file downloads |
| Import from chart (AI) | Gemini → `upsert_user_profile`+`set_user_hierarchy` | needs API key/usage |
| Row Edit → Save | `upsert_user_profile`+`set_user_hierarchy` | edits persist |
| Remove / Restore (undo) | `delete_user_profile`/`restore_user_profile` | soft delete + undo |
| Branding edit/save | company_settings | persists |
| Company settings | autoStartHours | persists |
| Audit log | audit view | renders |

## Org Chart tab
- **Auto view**: reads `user_profiles` + `reporting_lines`; renders tree from `reports_to_ids`/`level`. Verify it auto-loads the Admin-entered data.
- **Canvas mode** (admin-gated): draw modes (box/line/connect/pan), save positions (`upsert_org_chart_position`), matrix lines, wheel zoom/fit, HUD, "Back to Auto", autosave indicator. Box moves do NOT reflect to Auto (Auto is clean tree); lines DO reflect.
