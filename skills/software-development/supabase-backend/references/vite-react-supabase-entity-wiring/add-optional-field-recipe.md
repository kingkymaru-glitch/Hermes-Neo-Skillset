# Add-an-optional-field recipe (R-Tessera, portal_url example)

Concrete, reproduce-with-modifications walkthrough for adding an OPTIONAL
external URL to node groups. Swap `portal_url` / `portalUrl` / default for the
next field.

## 1. Migration — idempotent column add
File: `supabase/migrations/<yyyymmddhhmmss>_add_portal_url_to_nodes.sql`
```sql
-- nodes: add external LuNav digital-twin portal link (optional)
ALTER TABLE public.nodes ADD COLUMN IF NOT EXISTS portal_url text;
```
Note: committed file is NOT auto-applied to live DB. Apply manually via Supabase
dashboard SQL Editor if the column must exist on the running project.

## 2. Context — map in + map out
`src/context/EdgeDataContext.jsx`
- load map (row -> object): add `portal_url: r.portal_url || null`
- save payload (object -> row): add `portal_url: node.portal_url || null`

## 3. New Node Group modal — `NewNodeGroupModal` (App.jsx)
- `useState` seed: `portalUrl: draft?.portal_url || 'https://lunavsolution.vercel.app'`
- labeled input: `placeholder="https://lunavsolution.vercel.app"`, value=`form.portalUrl`,
  onChange `set('portalUrl', e.target.value)`
- in `handleSave`: `const portalUrl = (form.portalUrl||'').trim() || 'https://lunavsolution.vercel.app'`
  then `portal_url: portalUrl` in the `onCreate` payload; append to `body` markdown.

## 4. Inspection drawer — `NodeEditorModal` (App.jsx)
- `useState` seed: `portalUrl: node?.portal_url || 'https://lunavsolution.vercel.app'`
- same labeled input
- in `buildPayload`: `portal_url: (form.portalUrl||'').trim() || 'https://lunavsolution.vercel.app'`
- footer launch button:
  ```jsx
  <button
    type="button"
    className="modal-foot-btn portal"
    onClick={() => window.open(node?.portal_url || 'https://lunavsolution.vercel.app', '_blank')}
  >
    Launch LuNav Twin Portal ↗
  </button>
  ```

## 5. CSS — `.modal-foot-btn.portal`
`src/App.css`, next to `.modal-foot-btn.danger`:
```css
.modal-foot-btn.portal {
  background: linear-gradient(135deg, #2bd0ff, #5ad1ff);
  color: #04121a;
  font-weight: 700;
  border: 0;
}
```

## 6. Verify + ship
```bash
npm run build   # exit 0, ignore the >500kB chunk-size warning (pre-existing)
git add -A
git commit -m "Add external LuNav Twin Portal URL to Node Group modal + drawer"
git push origin main   # Vercel auto-builds + promotes
```
