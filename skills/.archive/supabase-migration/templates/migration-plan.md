# MIGRATION.md — <App> → Supabase

## Decision (topology)
- New Supabase project: `<app>-<env>` (e.g. `anglergo-dev`). Region: <region, e.g. ap-southeast-2>.
- Own project per app (isolation); same region + patterns as RINA/LUNAV.
- Auth: Supabase Auth (email/password). Storage-URL pattern kept (no blobs in DB rows).

## Swap surface (file-by-file)
| Existing (Firebase) | New (Supabase) | Notes |
|---|---|---|
| `AppState` (Auth + Firestore) | `AppState` (supabase-swift client) | collections → tables; listeners → realtime/`.select()` |
| `ShopsService` (Firestore + Storage) | `ShopsService` (Postgres + Storage) | `saveShop` → upsert + Storage upload |
| `LoginView` / `ShopOwnerLoginView` | Supabase Auth session | inject session; same UI |
| `AnglerGoApp` | Supabase client init | `SupabaseClient(url:anonKey)` from config |

## RLS (the rules layer — design early)
- [ ] User sees only own rows (`catches.user_id = auth.uid()`).
- [ ] Shop owner edits only their shop (`shops.owner_user_id = auth.uid()`).
- [ ] Public read where needed (e.g. published shops) via separate policy.

## SQL migrations
- `create table catches (...)`, `shops (...)` + RLS policies.
- `supabase db push --dry-run` before applying; then `supabase db push`.

## Verification
- iOS: `swiftc -parse` on touched .swift (no Xcode on CLI host).
- Backend: exercise from app / supabase CLI after deploy.
- Keep CodingKeys excluding binary fields (proved via encoding harness).
