# Flyout Drill-down State Reset (G23)

When a flyout panel is **always mounted** (rendered inside the hidden drawer
`<aside>` and toggled only via a CSS `.open` class), its internal drill-down
state in `useState` survives close — because the × only removes `.open`, it
does NOT unmount. Reopening resumes at the deepest level the user left.

## Symptom
Close a 3rd-level detail tab → reopen the panel from the main tab → it opens
straight at level 3, skipping levels 1–2.

## Fix — reset on open
Pass an `open` prop from the parent (the same boolean that drives `.open`):

```jsx
function SensorsPanel({ selected, onClose, open }) {
  const [level, setLevel] = useState('cluster')
  const [groupKey, setGroupKey] = useState(null)
  const [localSensorId, setLocalSensorId] = useState(null)

  // Reset the drill-down to root every time the panel OPENS. The panel stays
  // mounted (only hidden via CSS), so without this the deepest level persists.
  useEffect(() => {
    if (open) { setLevel('cluster'); setGroupKey(null); setLocalSensorId(null) }
  }, [open])

  // ... map-pin deep-link effect, render, etc.
}
```

Render site passes the flag:
```jsx
<SensorsPanel selected={selectedSensor} open={sensorsOpen}
              onClose={() => closeRight('sensors')} />
```

Same pattern for any always-mounted panel with internal nav (e.g. `SettingsPanel`
with `view` state → `if (open) setView(null)`).

## Fix — explicit back chevron
A breadcrumb trail reads as labels, not buttons — users miss it. Add a real
one-tap `‹` that steps back EXACTLY ONE level (not straight to root):

```jsx
{level !== 'cluster' && (
  <button
    className="sensors-back"
    onClick={() => {
      if (level === 'sensor') { setLevel('group'); setLocalSensorId(null) }
      else { setLevel('cluster'); setGroupKey(null) }
    }}
    aria-label={level === 'sensor' ? 'Back to cluster group' : 'Back to sensor clusters'}
  >
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor"
            strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  </button>
)}
```

CSS (matches the glass/cyan panel theme; sits left of the title in the header):
```css
.sensors-back {
  display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 30px; margin-right: 4px;
  border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 8px;
  background: rgba(56, 189, 248, 0.06); color: var(--neon-cyan);
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, color 0.2s;
}
.sensors-back:hover {
  background: rgba(56, 189, 248, 0.14);
  border-color: rgba(56, 189, 248, 0.45); color: #bae6fd;
}
```

## Verification
This is a structural/logic fix — gate on `npm run lint` + `npm run build`
(oxlint 0/0, vite build green). Then manual QA in `npm run dev`: walk
open → L2 → L3 → close → reopen from main tab, confirm it restarts at L1;
confirm the `‹` chevron steps back one level at a time.
