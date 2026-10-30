---
name: flutter-ar-dev
description: Flutter AR apps with ar_flutter_plugin + Supabase GPS pins.
---

# Flutter AR dev (ar_flutter_plugin + Supabase)

## When to use
- Building a Flutter app that needs camera + AR with objects anchored at real-world GPS coordinates.
- Specifically when using `ar_flutter_plugin` (the de-facto Flutter AR package; last real release 0.7.3).
- Reference product: a friend-finder that renders a giant world-anchored pin at each friend's GPS, with a screen compass + mini-map fallback for battery-saver / browser viewers.

## Setup (macOS arm64) — see Pitfalls for version pins
- Flutter SDK: download `flutter_macos_arm64_*_stable.zip` from storage.googleapis.com, unzip to `~/development/flutter`, add `~/development/flutter/flutter/bin` to PATH.
- JDK: Gradle 8 needs Java 17. `brew install openjdk@17`; export `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`.
- Android NDK: the preinstalled NDK dir is frequently corrupt (missing `source.properties`) → `CXX1101` build error. Fix: `~/Library/Android/sdk/cmdline-tools/latest/bin/sdkmanager "ndk;<ver>"` (use the version `flutter.ndkVersion` expects) to reinstall.
- First `flutter build apk --release` is slow (Gradle + NDK toolchain). Run in background with `notify_on_complete=true`.

## CRITICAL: ar_flutter_plugin 0.7.3 is NOT AGP 8 compatible
The current Flutter template uses AGP 8.7.0. The plugin pins AGP 4.1.0, Kotlin 1.3.50, `jcenter()` (dead), and declares no `namespace`. Build fails with: `Namespace not specified ... ar_flutter_plugin-0.7.3/android/build.gradle`. AGP 8 requires `namespace` and refuses `jcenter()`.

FIX: patch the cached plugin build file directly. Exact patched file + path in `references/ar_flutter_plugin_agp8_patch.md`. After editing, re-run `flutter build apk`. This is a pub-cache edit (not committed) — re-apply if you clear the pub cache.

## AR pin placement: ar_flutter_plugin does NOT auto-anchor at lat/lng
`ARLocationManager` only tracks the device's OWN GPS — it does NOT place nodes at a target's coordinates. To render a world-anchored pin at a friend's GPS:
1. Stream device GPS (`geolocator` `getPositionStream`).
2. Compute the ENU (East-North-Up) vector from device GPS → target GPS.
3. Create an `ARNode` with `positionVector = Vector3(east, up_cosmetic, -north)` (plugin uses OpenGL coords: +Y up, +Z toward viewer, so north → -Z).
4. Add via `arObjectManager.addNode`.
5. On every GPS tick, recompute and `arObjectManager.updateNode` (or remove+re-add).

GPS altitude is unreliable — treat vertical as cosmetic (fixed tower height). Math + working `ar_view.dart` skeleton in `references/enu_ar_pin_placement.md`.

## Supabase backend pattern (creator-gate)
- Realtime mesh: one `rooms` row (token, TTL, creator_id) + `participants` (lat, lng, pin_skin) + `skins`. Everyone subscribes; no central broadcaster.
- HARD RULE (product): only an installed, email-verified app user may create a room / generate the AR pin. A browser link = anonymous view-only (map + compass only), never a creator.
- Enforce server-side: room creation as an RPC (`create_room`) that does `if auth.uid() is null then raise exception 'auth_required'`. An anon client (browser) cannot call it.
- Auth v1 = email magic-link only (free Supabase plan, no SMS). Phone OTP deferred.
- Full paste-ready v1 schema (RLS + RPCs + TTL cleanup cron) lives at `~/skypin/supabase_schema.sql` — adapt, don't copy blindly.

## Supabase through GitHub (Git-driven deploy) — PITFALL
"Access Supabase through GitHub" is often read as "push the repo and the DB is live." It is NOT fully automatic. Real behavior + caveats:
- Use a `supabase/` folder with `supabase/migrations/0001_init.sql` and a `supabase/config.toml`. Wire it via Supabase dashboard → Integrations → GitHub (connects repo → runs migrations on push), OR `supabase link --project-ref <REF>` + `supabase db push` from a logged-in machine.
- **CRITICAL caveat:** Git-based Supabase deploy applies SQL migrations only. It does NOT (a) create Storage buckets, (b) upload storage files (.glb skins, etc.), or (c) inject app-side config (URL/anon key in config.dart, redirect URLs in Auth settings). Those three remain MANUAL steps even when "GitHub deploy" is on. State this honestly to the user — don't imply a repo push alone produces a runnable app.
- `supabase projects list` / `supabase db push` need a logged-in CLI (`supabase login`). If the agent's machine has the CLI but no access token, it CANNOT push schema to the live project — it can only lay out `supabase/` for the user to connect/deploy. Don't claim the schema was applied in that case.
- App config (supabaseUrl/anonKey) is a client public key — safe to commit to a PRIVATE repo, but keep it `[REDACTED]`/placeholder in the committed source and let the user paste real values, OR read from `--dart-define` at build time.
- Full runbook + the exact config.toml/Site-URL values: `references/supabase_git_deploy.md`.

## Pipeline checklist
1. `flutter pub get` (compat pins: ar_flutter_plugin ^0.7.3, geolocator ^9.0.0, flutter_compass ^0.8.1, supabase_flutter ^2.6.0).
2. `flutter analyze` — most errors are import-path bugs: files in `lib/screens/` import siblings as `'foo.dart'` but must use `'../foo.dart'`.
3. Patch ar_flutter_plugin `build.gradle` (above).
4. `flutter create --platforms=android,ios .` to generate native wrappers (hand-scaffolded projects lack gradle/MainActivity). Re-apply AndroidManifest/Info.plist perms afterward.
5. AndroidManifest: INTERNET, ACCESS_FINE_LOCATION, CAMERA. iOS Info.plist: NSCameraUsageDescription, NSLocationWhenInUseUsageDescription.
6. `flutter build apk --release` (background).

## Pitfalls
- Don't expect `ARLocationManager` to auto lat/lng-anchor — it doesn't. Use ENU vectors (above).
- **Live-GPS drift bug (found in SkyPin review):** the ENU vector MUST be recomputed from the
  DEVICE's OWN live `geolocator` GPS stream on every tick (`widget.room.myLat/myLng`), NOT from a
  one-shot DB snapshot (`me.lat/me.lng` read once at join). Anchoring from a stale snapshot makes
  every pin drift as the user walks — the arrow points at where THEY were at join time, not where
  they are now. Fix: feed the GPS stream into both the AR node placement AND the compass; the node
  offset = device_live - target. If you only have a single shared "me" row, keep it updated each
  tick too, but prefer the live stream for the math.
- `flutter_compass` <0.8.0 isn't null-safe; use ^0.8.1. For the on-screen CompassArrow, feed the
  live heading (`FlutterCompass.events`) into the bearing math — a static `0` makes the arrow wrong.
- `supabase_flutter` >=2.x uses `Supabase.initialize(url:, publishableKey:)` (NOT `anonKey`/`authFlowType`).
- Custom .glb uploads: cap ≤5MB, ≤10k tris, bbox ≤30m, tex ≤2MB/1024px; fallback to a procedural pin on bad file (never crash the session).
- Browser viewer is a SEPARATE entry (`web/main.dart`) — no app, no auth, no AR.
- Old transitive deps in the patched plugin (sceneform 1.15, play-services-auth 16+) are ancient; if Maven resolution fails, bump them in the same patched build.gradle.
- **Known-good build env (SkyPin, 2026-08):** Flutter 3.29.3, JDK 17, Android NDK 27.0.12077973
  (pin `flutter.ndkVersion` + set `ANDROID_NDK_HOME`), R8/minify OFF for v1 dev APK, `minSdk 24`.
  `dependency_overrides` needed for `permission_handler` (plugin expects a ^11 compat shim) + the
  patched `ar_flutter_plugin`. Re-apply the pub-cache `build.gradle` patch after any
  `flutter pub cache clean` — it is NOT committed.
