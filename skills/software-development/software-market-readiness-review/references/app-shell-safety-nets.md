# App-shell safety nets — the missing convention pages + companion form fixes

An audit that flags "no `not-found.tsx` / `error.tsx` / `loading.tsx`" is only half
useful; this is the implementation. All three live in the App Router app dir
(`src/app/`), are tiny, and each removes a whole class of dead-end.

## not-found.tsx — a 404 that offers a way out
Next's default 404 is a black-and-white page with no route back. Render the brand mark
plus TWO exits (the app's main screen + home):

```tsx
import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="dash-panel fade-up w-full max-w-md p-10 text-center">
        <img src="/favicon.svg" alt="<Brand>" className="mx-auto mb-5 h-16 w-16 object-contain" />
        <div className="dash-panel-header mb-2 justify-center">404 — Not Found</div>
        <h1 className="mb-3 text-2xl font-bold">This page doesn&apos;t exist</h1>
        <p className="mb-7 text-sm">The link may be broken, or the item was removed.</p>
        <Link href="/dashboard" className="mb-btn mb-btn-primary px-5 py-2.5">Go to dashboard</Link>
      </div>
    </main>
  );
}
```

## error.tsx — recover instead of blanking the app
Without a route error boundary a render error in a large component blanks the entire
app with no way back. `error.tsx` MUST be a client component, and should offer `reset()`
plus a support handle:

```tsx
"use client";
import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error("[app] route error:", error); }, [error]);
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="dash-panel w-full max-w-md p-10 text-center">
        <div className="dash-panel-header mb-2 justify-center">Something went wrong</div>
        <h1 className="mb-3 text-2xl font-bold">This page couldn&apos;t load</h1>
        <p className="mb-2 text-sm">Your data is safe. This is a display error.</p>
        {error.digest && <p className="mb-6 text-[11px]">Reference: {error.digest}</p>}
        <button onClick={reset} className="mb-btn mb-btn-primary px-5 py-2.5">Try again</button>
      </div>
    </main>
  );
}
```
Two rules: say "your data is safe" (the user's first fear is lost work), and surface
`error.digest` so a support report is actionable.

## loading.tsx — a skeleton, not a white screen
A route-level `loading.tsx` covers the gap while a heavy route resolves. Keep it to the
brand mark on a pulse; no layout that would shift when real content arrives.

```tsx
export default function Loading() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <img src="/favicon.svg" alt="" className="h-12 w-12 animate-pulse object-contain" />
    </main>
  );
}
```

## Verify
- `npm run build` now lists a `_not-found` route; exit 0.
- Curl a path UNDER an already-public route (e.g. `/privacy/nonexistent`) so middleware
  doesn't 307 you away, then grep the body for your custom copy:
  `curl -s https://<host>/privacy/nonexistent | grep -o "doesn't exist"` → a hit proves the
  custom 404 renders. A bare 404 status with default HTML means the file isn't picked up.
- An unauthenticated 404 on a PROTECTED path still 307s to /login — that is the middleware
  working as designed, not a failed 404 page. Probe under a public prefix.

## Companion fix — the `confirm` state-name collision
Naming a React state variable `confirm` (e.g. while adding a confirm-password field)
shadows `window.confirm` and breaks BOTH the state and any `window.confirm()` call in the
same module — the type checker reports the state as the function type. Name it `confirmPw`
(or similar). Cheap to hit, cheap to avoid.
