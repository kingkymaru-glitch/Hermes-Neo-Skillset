---
name: flutter-ar-supabase-app
description: Build Flutter AR app on Supabase; pass MARU's review.
---

# Flutter AR app on Supabase

Use when asked to build/debug/ship a Flutter app using camera + world-anchored
AR pins + live GPS, with Supabase (Postgres+Realtime) as the only backend.
SkyPin (`~/skypin/app`) is the reference build.

## Hard founder rule
The room CREATOR (anyone broadcasting the AR big arrow) MUST be an installed,
authenticated app user. Browser/link users are view-only (no AR, no create).
Enforce on BOTH the client UI and server RPCs — never trust one layer.

## Build pipeline (macOS, Flutter 3.29.x verified)
1. `flutter pub get`.
2. ar_flutter_plugin 0.7.3 needs patching — full recipe in
   `references/toolchain_patches.md`: plugin `namespace`/AGP8/Kotlin,
   `jcenter`->`mavenCentral`, drop `package=` from its manifest,
   `permission_handler_android` v1 `registerWith` removal, pubspec real dep
   `permission_handler: ^11` + override pin, app `minSdk 24`, NDK 27, JDK17,
   release `minifyEnabled false` + `shrinkResources false` (R8 kills
   com.google.ar.sceneform.*).
3. `flutter analyze` -> 0 errors, then `flutter build apk --release`.

## Creator-gate pattern (SQL in `references/creator_gate_rpc.md`)
`create_room` / `join_room` as `security definer`, `raise exception 'auth_required'`
for anonymous callers. Client hides the "Summon" button from anon/web viewers.

## Three-hat pass — MANDATORY before "done"
ENGINEER: cancel GPS/Realtime streams on end (battery); request Location+Camera
at Summon/Join with battery-saver fallback; feed compass heading into arrow;
anchor AR to LIVE device GPS (not DB snapshot); add `skypin://` deep-link for
magic-link re-entry; wipe positions on close.
DESIGNER: one giant CTA + pitch (not a settings wall); tap-to-focus a friend;
distance color cool->hot + "Arrived" <5m; no dead buttons.
USER: cut steps-to-value; plain-language toggles; visible TTL + count +
battery-saver; visible Report/Safety affordance.

## Verify
`flutter analyze` 0 errors AND `flutter build apk --release` succeeds; state the
APK path. Real run needs Supabase URL+anon in `lib/config.dart`, the schema
`.sql` run in Supabase, and the skins Storage bucket seeded.

## Pitfalls
- ar_flutter_plugin tracks only the device; reposition ARNodes from an ENU
  offset each GPS tick yourself.
- Realtime `stream()` includes `me` — filter `user_id != me`.
- Compass widget must compute relative bearing from `FlutterCompass.events`.
