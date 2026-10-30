# Mobile optimization — copy-paste snippets

Verified in the ss-rover-cloud (LunaV Solutions) 3D inspection app, Next.js App
Router + Tailwind. Adapt class names to your design system. Every mobile rule is
`sm:`-gated so desktop is unchanged.

## Next.js App Router viewport (src/app/layout.tsx)
```ts
export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",          // MUST have this or safe-area insets read 0
  themeColor: "#0b0e12",
};
```

## Bottom-sheet drawer (mobile) → side panel (sm+)
One conditional className on the `<aside>`:
```
absolute inset-x-0 bottom-0 top-auto z-20 w-full rounded-t-2xl rounded-b-none p-6
  pb-[max(1.5rem,env(safe-area-inset-bottom))]
  max-h-[82vh] overflow-y-auto
  sm:inset-auto sm:right-4 sm:top-4 sm:w-[calc(100vw-2rem)] sm:max-w-96 sm:rounded-2xl
```
Apply to finding/proxy/settings drawers over a canvas stage.

## Collapsible left side panel (models/layers)
State: `const [open, setOpen] = useState(true);`
- Open (mobile): `left-2 right-2 top-2 max-h-[60vh] overflow-y-auto`
- Collapsed (mobile) edge tab:
  `left-0 top-1/2 w-9 -translate-y-1/2 overflow-hidden rounded-r-2xl`
  with a button whose label is `<span style={{writingMode:"vertical-rl"}}>Models ›</span>`
- Desktop (`sm+`, unchanged): `sm:left-4 sm:right-auto sm:top-4 sm:w-80 sm:max-h-[calc(100%-32px)] sm:translate-y-0 sm:rounded-2xl`
- Hide the collapse chevron on desktop: add `sm:hidden` to it.

## Touch-target media query (globals.css)
```css
@media (max-width: 640px) {
  .mb-btn, .mb-input, .mb-select, .mb-textarea { min-height: 44px; }
  .mb-btn { padding-top: .65rem; padding-bottom: .65rem; }
  input[type="range"] { height: 28px; }
  button, [role="button"] { touch-action: manipulation; }
}
```

## Responsive top nav
- Nav container: `flex h-auto min-h-16 flex-wrap items-center justify-between gap-y-2
  border-b px-4 py-2 pt-[max(0.5rem,env(safe-area-inset-top))] sm:px-6 sm:py-0`
- Tab/group row: `flex gap-2 overflow-x-auto` (scrolls instead of squishing)
