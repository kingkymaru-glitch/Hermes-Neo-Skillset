# Build patterns — Vite + React + Cesium/Resium + Supabase SHM SPA

Concrete, non-obvious fixes discovered while building the MARU `my-digital-twin`
dashboard. Apply when extending the canvas or HUD.

## 1. Full-bleed the Cesium viewer
Vite's default `index.css` constrains layout:
```css
#root { max-width: 1126px; margin: 0 auto; display: flex; flex-direction: column; }
```
This shrinks / letterboxes the Cesium `<Viewer>`. Fix in `App.css`:
```css
html, body, #root { margin: 0; height: 100%; }
.dashboard { position: fixed; inset: 0; }   /* full-bleed container */
```
Then **import it in `main.jsx`** — Vite does not auto-load `App.css`:
```js
import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import './App.css'          // <-- required for full-bleed to apply
createRoot(document.getElementById('root')).render(<App />)
```

## 2. ErrorBoundary around `<Viewer>`
Cesium init failures throw and white-screen the SPA. Wrap the viewer in a
class component (React requires class for `componentDidCatch`):
```jsx
class ErrorBoundary extends React.Component {
  state = { error: null }
  static getDerivedStateFromError(error) { return { error } }
  render() {
    if (this.state.error) return <div className="fallback">Map failed to load</div>
    return this.props.children
  }
}
// usage: <ErrorBoundary><Viewer>...</Viewer></ErrorBoundary>
```

## 3. Supabase client — env-driven with demo fallback
`src/supabaseClient.js`:
```js
import { createClient } from '@supabase/supabase-js'
const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_ANON_KEY
export const isSupabaseConfigured = Boolean(url && key)
export const supabase = isSupabaseConfigured ? createClient(url, key) : null
```
App reads `isSupabaseConfigured`; when false it seeds demo pins and the HUD
shows "Demo". Never `createClient(null, null)` — it throws on import.

## 4. Fetch with safe fallback (useEffect)
```jsx
useEffect(() => {
  if (!supabase) { setAssets(DEMO); return }
  ;(async () => {
    try {
      const { data, error } = await supabase.from('assets')
        .select('id,name,latitude,longitude')
      if (error) throw error
      setAssets(data ?? [])
    } catch (e) {
      setWarning(e.message); setAssets(DEMO)   // map never empty
    }
  })()
}, [])
```

## 5. Verify after edits
`npm run build` is runnable here. After ANY source change (even an unused-
import removal), re-run it before reporting "green" — a post-build edit can
break a previously-passing build.

## 6. Secrets-safe first commit
Before `git add .`, confirm exclusions:
```bash
git check-ignore node_modules .env dist .env.local
# prints each ignored path; if silent, it is NOT ignored — fix .gitignore first
```
Never commit `.env`. Anon keys are browser-exposed by design (VITE_ prefix) but
the file itself stays out of git.

## 7. GitHub repo from a fresh macOS (overlaps github:github-repo-management)
`gh` is not preinstalled on this machine:
```bash
brew install gh
export GH_TOKEN="<pat>"                # keep in session env only, never log it
echo "$GH_TOKEN" | gh auth login --with-token
gh repo create my-digital-twin --private --description "..."
git init -b main
git add . && git commit -m "Initial commit"
git remote add origin https://github.com/<user>/my-digital-twin.git
git push -u origin main
```
SECURITY: a PAT pasted into a command line lands in the transcript/log. Prefer
`gh auth login` (interactive browser) when the user is at the keyboard; if a
token is supplied, store it only in the session env and redact it from all
output. Recommend rotating the token after use.
