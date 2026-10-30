# Next.js App Router + Supabase — dev-login route (SSR Cloud)

## src/app/dev-login/page.tsx
```tsx
import { redirect } from "next/navigation";
import { headers } from "next/headers";            // Next 15: headers() is async
import { createClient } from "@/lib/supabase/server";

// DEV-ONLY. NEVER works in prod: NODE_ENV must not be "production" AND host
// must be localhost. Vercel runs production, so this route is dead there.
function isDevHost(host: string | null): boolean {
  if (!host) return false;
  return (
    host === "localhost" ||
    host === "127.0.0.1" ||
    host.endsWith(".localhost") ||
    host.endsWith(".local") ||
    host.startsWith("localhost:")
  );
}

export default async function DevLogin({
  searchParams,
}: {
  searchParams: Promise<{ as?: string }>;
}) {
  const { as } = await searchParams;
  const host = (await headers()).get("host");      // <-- await!

  const devAllowed = process.env.NODE_ENV !== "production" && isDevHost(host);
  if (!devAllowed) redirect("/login");

  const supabase = await createClient();
  const email = (as || "inventedmaru@gmail.com").trim();

  const { data: list } = await supabase.auth.admin.listUsers();
  let user = list?.users?.find((u) => u.email?.toLowerCase() === email.toLowerCase());

  if (!user) {
    const { data: created } = await supabase.auth.admin.createUser({
      email,
      password: "dev-bypass-" + Math.random().toString(36).slice(2, 10),
      email_confirm: true,
      user_metadata: { full_name: "Dev Bypass" },
    });
    user = created?.user ?? undefined;
  }

  if (user) {
    await supabase
      .from("profiles")
      .upsert({ id: user.id, full_name: "Dev Bypass", role: "inspector", approved: true },
              { onConflict: "id" });
    const { data: link } = await supabase.auth.admin.generateLink({
      type: "magiclink", email,
    });
    if (link?.properties?.hashed_token) {
      redirect(`/auth/callback?token_hash=${link.properties.hashed_token}&type=magiclink`);
    }
  }
  redirect("/dashboard");
}
```

## middleware.ts — whitelist so middleware doesn't bounce it first
```ts
const isPublic =
  path === "/" ||
  path.startsWith("/login") ||
  path.startsWith("/share") ||
  path.startsWith("/auth") ||
  path.startsWith("/dev-login");   // <-- add this
```

## Landing / login "skip" link (client, dev-only)
```tsx
{typeof window !== "undefined" && process.env.NODE_ENV !== "production" && (
  <button onClick={() => (window.location.href = "/dev-login")}
    className="..." style={{ color: "var(--txt-secondary)" }}>
    Dev: skip login (localhost only)
  </button>
)}
```

## Verify
- curl -i localhost:3210/dev-login -> 307 /dashboard, then follow -> 200.
- Prod-mode server -> 307 /login (guard refused — correct).
