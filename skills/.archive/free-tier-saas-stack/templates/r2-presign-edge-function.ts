// Supabase Edge Function: r2-presign
// Presigned PUT for direct browser->R2 upload. Deploy: supabase functions deploy r2-presign
// Secrets: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID (32-hex S3 key, NOT cfat_ token!),
//          R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_BASE (https://pub-xxx.r2.dev)
import { createClient } from "npm:@supabase/supabase-js@2";
import { AwsClient } from "npm:aws4fetch@1.0.20";

const ALLOWED_EXT = ["glb", "gltf", "obj", "jpg", "jpeg", "png", "webp", "gif"];
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
    const { data: { user }, error: authErr } = await supabase.auth.getUser();
    if (authErr || !user) return json({ error: "Unauthorized" }, 401);

    const { fileName, fileSize, projectId, kind } = await req.json();
    const ext = String(fileName ?? "").split(".").pop()?.toLowerCase() ?? "";
    if (!ALLOWED_EXT.includes(ext)) return json({ error: `Extension .${ext} not allowed` }, 400);
    if (!fileSize || fileSize > MAX_SIZE) return json({ error: "File too large" }, 400);
    if (!projectId) return json({ error: "projectId required" }, 400);

    // Ownership check via RLS
    const { data: project } = await supabase.from("projects").select("id").eq("id", projectId).single();
    if (!project) return json({ error: "Project not found or not owned" }, 403);

    const r2 = new AwsClient({
      accessKeyId: Deno.env.get("R2_ACCESS_KEY_ID")!,
      secretAccessKey: Deno.env.get("R2_SECRET_ACCESS_KEY")!,
      region: "auto",
      service: "s3",
    });
    const safeName = String(fileName).replace(/[^a-zA-Z0-9._-]/g, "_");
    const prefix = kind === "photo" ? "photos" : "models";
    const key = `${user.id}/${projectId}/${prefix}/${crypto.randomUUID()}-${safeName}`;
    const target = new URL(
      `https://${Deno.env.get("R2_ACCOUNT_ID")}.r2.cloudflarestorage.com/${Deno.env.get("R2_BUCKET")}/${key}`,
    );
    target.searchParams.set("X-Amz-Expires", "600");
    const signed = await r2.sign(new Request(target, { method: "PUT" }), { aws: { signQuery: true } });

    return json({ uploadUrl: signed.url, publicUrl: `${Deno.env.get("R2_PUBLIC_BASE")}/${key}`, key, expiresIn: 600 });
  } catch (e) {
    return json({ error: String(e?.message ?? e) }, 500);
  }
});

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });
}
