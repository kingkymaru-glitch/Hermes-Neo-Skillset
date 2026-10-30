# React Context Scoping Crash — `useX() must be used within <Provider>`

## Symptom
`Uncaught Error: useEdgeData() must be used within <EdgeDataProvider>` (or any
context hook, e.g. `useContext`) thrown from the top-level component the instant
it renders. In MARU this surfaced at `App.jsx:354`.

## Root cause
The top component (`App`) BOTH:
  (a) renders `<EdgeDataProvider>` inside its own `return`, AND
  (b) calls `useEdgeData()` in its own function body (to feed the drawer /
      S22 console).

`App` is the provider's **PARENT**. React evaluates `App`'s body — including the
hook call — BEFORE the `<EdgeDataProvider>` element it returns is ever created.
So the hook runs with no provider above it. A *second* `<EdgeDataProvider>` wrap
does NOT fix this: it just nests providers while `App`'s body still executes first
and still throws.

## Fix — extract a child, make App a provider shell
1. Rename the body of `App` to `DashboardInner` (keep ALL state, the `<Viewer>`,
   and every `useEdgeData()` consumer — `AssetEntities`, `S22Console`,
   `EdgeStatusBadge`, `SensorsPanel` — inside it).
2. Remove the now-redundant `<EdgeDataProvider>` open/close that wrapped
   `DashboardInner`'s `<div className="dt-root">` return.
3. Replace `App` with a 6-line shell:
   ```jsx
   // App.jsx — App itself contains NO hooks.
   function DashboardInner() {
     const { geo, liveGeo, deviceStatus, sensorPayloads } = useEdgeData()
     // ...all state, drawers, <Viewer>, consumers...
     return <div className="dt-root">{/* ... */}</div>
   }

   export default function App() {
     return (
       <EdgeDataProvider>
         <DashboardInner />
       </EdgeDataProvider>
     )
   }
   ```
4. Now every `useEdgeData()` call lives in a component rendered *inside* the single
   provider. `App` never touches the hook.

## Verify
- `npm run lint` + `npm run build` (both modes).
- Grep: no `useEdgeData()` outside a component nested under the provider (only the
  import + comments should remain at module scope in `App.jsx`).
- No behavior change to the UI — the provider now wraps the whole inner tree.

## Anti-pattern to reject
"Just wrap `<App>`'s return in another `<EdgeDataProvider>`" — wrong. The crash is
about WHERE the hook is *called* (the parent's body), not about how many providers
exist. Move the call site inside the provider; don't multiply providers.
