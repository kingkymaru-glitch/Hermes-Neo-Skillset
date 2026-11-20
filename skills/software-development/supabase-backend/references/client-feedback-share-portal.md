# Client feedback in a view-only share portal — durable patterns

## 1. ReadOnly gating for new columns
Do NOT put client-input columns into inspector edit mode.
Render `Client Feedback` + `Actions` columns only when `readOnly=true`.
Otherwise editor layout shifts and you duplicate state paths.

Pattern:
```tsx
{readOnly && (<td><textarea onChange={...} /></td>)}
```
Keep `colSpan` of the empty-state row conditional too:
```tsx
<td colSpan={readOnly ? 8 : 7}>...</td>
```

## 2. Debounced per-marker autosave
Use one `Record<id, NodeJS.Timeout>` ref + one `Record<id, boolean>` saving ref.
Centralize updates through `updateFeedback(id, patch)`:
- merges patch into `markerFeedback[id]`
- schedules a debounced single-row `.update({ client_comment, action_needed })` by marker id

Do not fire a save-per-keystroke. 500–800ms debounce is enough.

## 3. Set-state-in-effect lint noise for init effects
`react-hooks/set-state-in-effect` is overly aggressive for bootstrap
initializers like "hydrate local state from `allMarkers` once".
Prefer inline suppression over refactoring the effect into a reducer,
because reducers here just move noise around:

```tsx
useEffect(() => {
  const init: ...
  setMarkerFeedback(init);
  // eslint-disable-next-line react-hooks/set-state-in-effect
}, [allMarkers]);
```

Same applies to one-time window-read setup like `setShareUrlBase(...)`.

## 4. share RPC must return the new columns or they are null
When adding postgres columns for client-facing data, upgrade any
`get_shared_project`-style RPC that builds JSONB marker objects to
include them via `coalesce(...)`:
```sql
'client_comment', coalesce(k.client_comment, ''),
'action_needed', coalesce(k.action_needed, false),
```
Otherwise the share portal gets `null` regardless of the migration.

## 5. Live DB migration trap
Vercel builds never run Supabase migrations. Any new column/RPC change
must be delivered as one idempotent SQL script the user pastes into
Supabase Dashboard → SQL Editor. Never skip writing that script or
assuming an existing SQL file will land in prod.
