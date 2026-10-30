# Remediating silent failure — the fix for the audit's top finding

The highest-impact finding in an internal-tool-turned-product audit is almost
always: N database writes, 1 error branch, 0 notifications. The user cannot tell
a slow network from a permission error from a server fault, so they retry and
create duplicates or give up. This is the repair.

## 1. A toast helper whose ERRORS are never dropped
Copy the pattern the app already uses where it works (a workspace usually has
one) rather than inventing a second system. Two rules matter:

- Errors must never be evicted by a burst. `setToasts(t => [...t, x].slice(-5))`
  — NOT `.slice(-2)`. A cap of 2 during a multi-file upload discards exactly the
  errors you need.
- Error lifetime > info lifetime (e.g. 7000ms vs 3500ms).

```ts
const toastId = useRef(0);
const toast = useCallback((msg: string, type: "success"|"error"|"info" = "info") => {
  const id = ++toastId.current;
  setToasts(t => [...t, { id, msg, type }].slice(-5));
  setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), type === "error" ? 7000 : 3500);
}, []);
```
Render with the app's EXISTING toast classes (e.g. `mb-toast show <type>`) so no
new CSS is needed. Put the container at the end of the page root.

## 2. Translate the error — never surface the raw PostgREST string
A user cannot act on `new row violates row-level security policy`. Map the
message families to plain language, and append the raw text only when nothing
matches so nothing is hidden:

```ts
function friendlyError(e: unknown, fallback: string): string {
  const raw = (e as { message?: string })?.message ?? "";
  if (!raw) return fallback;
  if (/row-level security|permission denied|not authorized|JWT/i.test(raw))
    return `${fallback} — you don't have permission for this.`;
  if (/duplicate key/i.test(raw)) return `${fallback} — that already exists.`;
  if (/failed to fetch|network|timeout/i.test(raw))
    return `${fallback} — network problem. Check your connection and try again.`;
  if (/JWT expired|session/i.test(raw))
    return `${fallback} — your session expired. Please sign in again.`;
  return `${fallback} — ${raw}`;
}
```
The `fallback` is the verb + object ("Couldn't create the project") so every
call site reads as a complete sentence.

## 3. Every mutation gets an error branch
`if (error) { toast(friendlyError(error, "Couldn't <verb> the <noun>"), "error"); return; }`
on EVERY write — create, rename, delete — AND on the initial load. A failed
fetch that renders as an empty list is the same silent bug wearing a different
hat. For delete: report failure, remove optimistically only on success.

## 4. Guard the session non-null assertion
`userData.user!.id` throws a raw TypeError when the session expired between page
load and submit — a dead button with no message. Check first and say so:

```ts
const { data: userData, error: authErr } = await supabase.auth.getUser();
if (authErr || !userData?.user) {
  toast("Your session expired. Please sign in again.", "error");
  return;
}
```

## 5. Verify the fix on an AUTH-GATED route (you cannot curl the page)
An authenticated route 307s a logged-out `curl` to `/login`, so grepping the page
HTML proves nothing. Verify the deployed bundle instead:

```bash
# 1. the local build output carries the new strings
grep -rl "you don't have permission for this" .next/static/chunks/
# 2. fetch THAT chunk from the live origin: HTTP 200 + the strings present
curl -s -o /tmp/c.js -w "%{http_code}\n" "https://<host>/_next/static/chunks/<file>.js"
grep -q "Project renamed" /tmp/c.js && echo "live OK"
```

Chunk filenames are content-hashed, so a 404 means the local `.next` is from a
different build than production — rebuild and re-read the filename. Also confirm
the version string on a PUBLIC page, to prove the deploy actually promoted.
