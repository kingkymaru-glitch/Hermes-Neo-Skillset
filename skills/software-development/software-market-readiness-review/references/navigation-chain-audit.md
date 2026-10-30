# Navigation-chain audit — counting the hops from entry point to action

A product family (marketing site + product landing page + the app) accumulates
cross-links over time and nobody ever walks the chain end to end. The defects are
invisible from inside a logged-in session and from any single repo.

## The probe

List every external link in every repo of the family, with its `target`:

```bash
# per repo — filter to your own domains, drop fonts/CDNs/APIs
grep -rhoE 'https?://[a-zA-Z0-9./?=&_%-]+' src/ \
  | grep -vE 'fonts|w3\.org|schema|arcgisonline|cesium|openstreetmap|supabase\.co' \
  | sort -u
```

Then follow the chain by hand from each entry point to the first real action
(sign-in, dashboard, primary CTA). Write the hops out as a diagram — the shape is
the finding.

**In a client-rendered SPA the served HTML has no links.** `curl` the page and you
get a `<div id="root">` and a title. Read the SOURCE repo (`src/App.jsx`,
`src/GlobeView.jsx`), not the page, or you will report "no links found" on a page
full of them.

## The four defects this surfaces

### 1. A hop that adds nothing
A product landing page whose only real action is "sign in" is a full page load
between the user and the app. If the family sites link to the *brochure* instead
of the *app*, the user takes four hops to reach a login form:

```
marketing site ──"Explore the Platform"──► product landing ──"Sign in"──► /login
```

Decision to put to the user: does the product landing page belong on the critical
path at all, or should the family CTAs point straight at the app (`/dashboard`,
which redirects to `/login` when signed out)? A marketing page is fine as a
marketing surface — the problem is only that it sits on the path to the action.

### 2. `target="_blank"` on family links
Every cross-link opening a new tab strands the user in a tab pile and breaks Back.
Same-family navigation belongs in the same tab; reserve new-tab for genuinely
external destinations (or for the "back to marketing site" exit from inside the
app, where leaving the app context is the point).

### 3. A loop with no door
Family cross-links commonly form a cycle — A links to B, B links back to A, and
both link to C — with no single "enter the product" edge. Trace it as a graph,
name the missing edge, and propose the one link that should point at the app.

### 4. The auth redirect forgets the destination
Middleware that rewrites the path to `/login` without carrying the original
destination loses it. The user signs in, lands on a generic dashboard, and has to
re-navigate to what they actually wanted.

```ts
// middleware — carry the destination
const url = request.nextUrl.clone();
const from = url.pathname + url.search;
url.pathname = "/login";
url.search = "";
url.searchParams.set("next", from);
return NextResponse.redirect(url);
```

```ts
// login page — honour it after auth, but ONLY a same-origin relative path
const next = params.get("next");
const redirectTo = next && next.startsWith("/") && !next.startsWith("//")
  ? next
  : "/dashboard";
router.push(redirectTo);
```

**Never redirect to an unvalidated `next`.** Accepting an absolute URL is an open
redirect — an attacker crafts a login link that lands the user on their own site
after auth. Require a single leading `/` and reject `//` (protocol-relative).

A single hardcoded special case (`?project=`) is not the general fix; it just
means one flow happens to work while every other deep link loses its destination.

### 4b. The other half: bounce SIGNED-IN users OFF `/login`
Carrying `next` is only half the fix. Once users enter the app through
`/dashboard`, an already-authenticated visitor who lands on `/login` (from a stale
bookmark, a marketing CTA, or a family cross-link) should not be shown a login
form. Add the mirror rule:

```ts
// middleware — authenticated + approved users never need the login form
if (user && path.startsWith("/login")) {
  const { data: prof } = await supabase
    .from("profiles").select("approved").eq("id", user.id).single();
  if (prof?.approved) {
    const url = request.nextUrl.clone();
    const nextParam = request.nextUrl.searchParams.get("next");
    url.pathname = nextParam && nextParam.startsWith("/") ? nextParam.split("?")[0] : "/dashboard";
    url.search = nextParam && nextParam.includes("?") ? "?" + nextParam.split("?")[1] : "";
    return NextResponse.redirect(url);
  }
}
```

Gate this on `approved` as well as `user` — an authenticated-but-pending account
must still SEE the login page (that is where the "awaiting approval" notice
renders). Bouncing a pending user to `/dashboard` sends them straight back into
the approval gate, an infinite loop.

### 4c. Point every CTA at `/dashboard`, not at the marketing root
Once the middleware carries `next` and bounces signed-in users, `/dashboard` is
the correct target for EVERY entry link — family CTAs, marketing buttons, product
links. It resolves correctly in both states with no branching in the link itself:

| visitor state | `/dashboard` resolves to |
|---|---|
| signed out | `302 → /login?next=%2Fdashboard` |
| signed in + approved | the app |
| signed in + pending | `/login?reason=pending` |

Linking the bare origin (`https://app.vercel.app/`) instead forces every visitor
through the marketing page first — the extra hop the whole audit was about.

**Reset `url.search = ""` before setting a param.** `nextUrl.clone()` carries the
ORIGINAL query string, so a stale `?reason=pending` survives and stacks with the
newly-set `next`.

**Verify all of it with curl, no session required:**
```bash
for p in /dashboard /project/abc123 "/admin?tab=x"; do
  echo "$p -> $(curl -s -o /dev/null -w '%{redirect_url}' "https://<domain>$p")"
done
# expect: .../login?next=%2Fdashboard  |  ...next=%2Fproject%2Fabc123  |  ...next=%2Fadmin%3Ftab%3Dx
```
The third case proves the query string survived the encode/decode round-trip — a
`next` that drops its query still "works" for the simple cases and fails exactly
where it matters.

## Reporting shape

Present the chain as a diagram, then the defects as numbered findings, then ask
which scope the user wants (full fix / links only / different flow) — and ask the
one question that changes the answer: should the CTA land on the login form
directly, or still show the marketing page first?
