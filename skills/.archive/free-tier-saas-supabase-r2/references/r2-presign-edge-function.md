# R2 presign Edge Function + browser upload client (proven working)

Deployed and verified in ss-rover-cloud (July 2026). Deno Edge Function returns a
10-min presigned PUT URL; browser XHR uploads directly to R2.

## supabase/functions/r2-presign/index.ts (core)

```ts
import { createClient } from "npm:@supabase/supabase-js@2";
import { AwsClient } from "npm:aws4fetch@1.0.20";

const ALLOWED_EXT = ["glb", "gltf", "obj", "jpg", "jpeg", "png", "webp"];
const MAX_SIZE = 200 * 1024 * 1024;
const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  // 1. Auth: client built with caller's Authorization header
  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!,
    { global: { headers: { Authorization: req.headers.get("Authorization")! } } },
  );
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: "Unauthorized" }, 401);

  // 2. Validate
  const { fileName, fileSize, projectId, kind } = await req.json();
  const ext = String(fileName ?? "").split(".").pop()?.toLowerCase() ?? "";
  if (!ALLOWED_EXT.includes(ext)) return json({ error: `.${ext} not allowed` }, 400);
  if (!fileSize || fileSize > MAX_SIZE) return json({ error: "Too large" }, 400);

  // 3. Ownership via RLS: select the project as the caller
  const { data: project } = await supabase.from("projects").select("id").eq("id", projectId).single();
  if (!project) return json({ error: "Not owner" }, 403);

  // 4. Presign
  const r2 = new AwsClient({
    accessKeyId: Deno.env.get("R2_ACCESS_KEY_ID")!,
    secretAccessKey: Deno.env.get("R2_SECRET_ACCESS_KEY")!,
    region: "auto", service: "s3",
  });
  const key = `${user.id}/${projectId}/${kind === "photo" ? "photos" : "models"}/${crypto.randomUUID()}-${String(fileName).replace(/[^a-zA-Z0-9._-]/g, "_")}`;
  const target = new URL(`https://${Deno.env.get("R2_ACCOUNT_ID")}.r2.cloudflarestorage.com/${Deno.env.get("R2_BUCKET")}/${key}`);
  target.searchParams.set("X-Amz-Expires", "600");
  const signed = await r2.sign(new Request(target, { method: "PUT" }), { aws: { signQuery: true } });
  return json({ uploadUrl: signed.url, publicUrl: `${Deno.env.get("R2_PUBLIC_BASE")}/${key}`, key });
});

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });
}
```

Add a `deno.json` next to it, and exclude `supabase/functions` in the Next tsconfig.

## Browser upload client (src/lib/r2-upload.ts)

```ts
export async function uploadToR2(file: File, projectId: string, kind = "model", onProgress?: (pct: number) => void) {
  const supabase = createClient();
  const { data, error } = await supabase.functions.invoke("r2-presign", {
    body: { fileName: file.name, fileSize: file.size, projectId, kind },
  });
  if (error || data?.error) throw new Error(error?.message ?? data.error);
  const { uploadUrl, publicUrl, key } = data;
  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();          // XHR: fetch lacks upload progress
    xhr.open("PUT", uploadUrl);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress?.(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => (xhr.status < 300 ? resolve() : reject(new Error(`HTTP ${xhr.status}`)));
    xhr.onerror = () => reject(new Error("Network error (check bucket CORS)"));
    xhr.send(file);
  });
  return { publicUrl, key };
}
```

## Share-token RPC pattern (schema side)

```sql
create or replace function public.get_shared_project(share_token uuid)
returns jsonb language sql security definer set search_path = public stable
as $$ select jsonb_build_object('project', ..., 'models', coalesce((select jsonb_agg(...)), '[]'::jsonb))
      from projects p where p.client_share_token = share_token; $$;
grant execute on function public.get_shared_project(uuid) to anon, authenticated;
```
Owner-only `generate_share_token(p_project_id)` raises if `owner_id != auth.uid()`, sets `gen_random_uuid()`.

## Verification probes
- `curl .../rest/v1/projects?limit=1 -H "apikey: $ANON" -H "Authorization: Bearer $ANON"` → 200 = schema + key OK
- `curl -X POST .../functions/v1/r2-presign -d '{}'` (no auth) → 401 = function deployed + guarded
