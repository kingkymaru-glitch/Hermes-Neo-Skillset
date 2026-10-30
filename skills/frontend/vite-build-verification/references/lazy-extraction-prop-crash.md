# Lazy-extraction prop-wiring crash — diagnostic + prevention (Pitfall 14)

## Symptom
After `React.lazy(() => import('./Heavy.jsx'))` + `<Suspense>`, the page renders a
blank screen (or tears the tree down) only at runtime. `lint` 0 errors, `build` green.
Browser console shows only:
`An error occurred in the <Heavy> component. Consider adding an error boundary…`
with NO message — untriageable.

## Why
Moving a sub-tree into a separate module drops every identifier that was in the
parent's scope. Any prop/setter/hook the new component uses but forgot to destructure
(or the parent forgot to pass) becomes an undefined reference → runtime ReferenceError.
Build can't see it (in-file undefined id, not an unresolved import).

## Fast diagnostic — DOM-dump the error
Wrap the lazy child in a temporary boundary that prints `error.stack`:
```jsx
class Diag extends Component {
  state = { err: null }
  static getDerivedStateFromError(e) { return { err: e } }
  render() {
    if (this.state.err) return (
      <pre style={{ color:'#fecaca', padding:24, fontFamily:'monospace', whiteSpace:'pre-wrap' }}>
        {String(this.state.err && this.state.err.stack || this.state.err)}
      </pre>
    )
    return this.props.children
  }
}
// <Diag><Suspense fallback={...}><HeavyView .../></Suspense></Diag>
```
Reload → the DOM shows e.g. `ReferenceError: onOpenLabs is not defined at HeavyView.jsx:210`.
One-line fix (destructure the prop / pass it from parent). Remove the boundary after.

## Prevention grep gate (run after any extraction)
For the new lazy file:
```bash
# every setter/handler/hook it calls
grep -oE "set[A-Z][a-zA-Z]+|on[A-Z][a-zA-Z]+|use[A-Z][a-zA-Z]+" src/HeavyView.jsx | sort -u
# confirm each appears in the destructure signature
grep -n "export default function HeavyView({" src/HeavyView.jsx
# confirm the parent actually SENDS each one
grep -n "onOpenLabs=\|setScene=\|setProjectsError=" src/App.jsx
```
Any name used-but-not-in-destructure, or passed-but-undefined in parent = incoming crash.
