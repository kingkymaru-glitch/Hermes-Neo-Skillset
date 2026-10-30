// Supabase Edge Function: R2 presigned PUT (template — set secrets, deploy)
// supabase functions deploy r2-presign
// supabase secrets set R2_ACCOUNT_ID=... R2_ACCESS_KEY_ID=... R2_SECRET_ACCESS_KEY=... R2_BUCKET=... R2_PUBLIC_BASE=https://pub-xxxx.r2.dev
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
  try {
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_ANON_KEY")!,
      { global: { headers: { Authorization: req.headers.get("Authorization")! } } },
    );
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return json({ error: "Unauthorized" }, 401);

    const { fileName, fileSize, projectId, kind } = await req.json();
    const ext = String(fileName ?? "").split(".").pop()?.toLowerCase() ?? "";
    if (!ALLOWED_EXT.includes(ext)) return json({ error: `.${ext} not allowed` }, 400);
    if (!fileSize || fileSize > MAX_SIZE) return json({ error: "File too large" }, 400);

    // Ownership check rides on RLS
    const { data: project } = await supabase.from("projects").select("id").eq("id", projectId).single();
    if (!project) return json({ error: "Not owner" }, 403);

    const r2 = new AwsClient({
      accessKeyId: Deno.env.get("R2_ACCESS_KEY_ID")!,
      secretAccessKey: Deno.env.get("R2_SECRET_ACCESS_KEY")!,
      region: "auto",
      service: "s3",
    });
    const safeName = String(fileName).replace(/[^a-zA-Z0-9._-]/g, "_");
    const key = `${user.id}/${projectId}/${kind === "photo" ? "photos" : "models"}/${crypto.randomUUID()}-${safeName}`;
    const target = new URL(
      `https://${Deno.env.get("R2_ACCOUNT_ID")}.r2.cloudflarestorage.com/${Deno.env.get("R2_BUCKET")}/${key}`,
    );
    target.searchParams.set("X-Amz-Expires", "600");
    const signed = await r2.sign(new Request(target, { method: "PUT" }), { aws: { signQuery: true } });

    return json({ uploadUrl: signed.url, publicUrl: `${Deno.env.get("R2_PUBLIC_BASE")}/${key}`, key });
  } catch (e) {
    return json({ error: String((e as Error)?.message ?? e) }, 500);
  }
});

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });
}
