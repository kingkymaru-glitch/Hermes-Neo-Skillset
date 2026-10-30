---
name: flutter-supabase-ar-app
description: Build Flutter+Supabase AR apps with world-anchored pins.
---

# Flutter + Supabase + AR app build

Class-level skill for building Flutter apps backed by Supabase with camera/AR
world-anchored objects (friend-finder pins, navigation arrows, location markers).
Born from the SkyPin build; reusable for any Flutter+Supabase+AR project.

## When to use
- Scaffolding or fixing a Flutter app that needs Supabase auth + Realtime + Storage.
- Any AR task that places objects at real-world GPS coordinates.
- Executing a "build it" on a Flutter project after the design doc is locked.

## Hard product rule (SkyPin, founder-enforced — verify it survives)
- **Summoning a room / creating the AR pin requires the INSTALLED, email-authenticated
  native app.** A browser-opened room link is VIEW-ONLY: live roster + compass arrow +
  mini-map, but NO AR pin, NO broadcast, NO room creation.
- Enforce it BOTH ways: (a) server-side RPCs reject anon (see templates/supabase_creator_gate.sql),
  and (b) the browser/web build hides the "Summon" UI entirely.

## Build sequence
1. **Toolchain (macOS)** — see references/flutter_toolchain_macos.md. Essentials:
   JDK 17 for Gradle 8, reinstall NDK if `source.properties` is missing, and run
   `flutter create . --platforms=android,ios` to generate clean native wrappers AFTER
   writing `lib/`.
2. **Scaffold** — write `lib/` first, then `flutter create .` (keeps your lib/ + pubspec,
   regenerates android/ios). Screen files under `lib/screens/` import siblings with `../`
   (e.g. `import '../models.dart'`).
3. **Supabase** — run the full schema (repo: `supabase_schema.sql`), then paste the gate
   snippet from templates/supabase_creator_gate.sql into any RPC that must be app-only.
4. **AR world-anchoring** — see references/ar_flutter_plugin_api.md. CRITICAL:
   `ARLocationManager.startLocationUpdates()` only updates the DEVICE gps; it does NOT
   anchor nodes at lat/lng. You compute the ENU offset (east, north) from my GPS to each
   target's GPS and place an `ARNode` at `Vector3(east, 0, -north)`, repositioning on every
   GPS tick. That is what produces a stable "big arrow in the field".
5. **Live loop** — `Geolocator.getPositionStream()` → upsert `participants` row →
   Realtime subscription → rebuild ARNodes. Mesh model: everyone sees everyone.
6. **Build** — `flutter build apk --release` (side-load APK), `flutter build ios` (needs
   Apple Dev account + real device), `flutter build web` (browser view-only viewer).

## Pitfalls (hit and fixed in the SkyPin build)
- `ar_flutter_plugin`'s barrel (`ar_flutter_plugin.dart`) exports ONLY `ARView`. The
  manager classes are NOT re-exported — import each manager file directly or you get
  `undefined_class` (`ARAnchorManager`, `ARObjectManager`, etc.).
- Without manual ENU placement, pins render at the world origin (under your feet), not at
  the friend's location. The location manager does not do this for you.
- Don't hand-write `lib/` AND the native wrappers together — `flutter create .` after
  writing lib/ regenerates android/ios cleanly and avoids missing gradle/MainActivity errors.
- `flutter_compass` import must be `package:flutter_compass/flutter_compass.dart`.
- `geolocator` import must be `package:geolocator/geolocator.dart` (not a bare `geolocator`).
- `analyze` clean ≠ `build` clean. APK build additionally needs JDK 17 + a valid NDK.
- `auth_flow_type` / `anonKey` are deprecated in supabase_flutter 2.x — use `publishableKey`.
- Inside `StatefulBuilder`, the `setState` param is name-scoped; a sibling widget outside the
  builder can't call it — wrap both consumers in the same builder.

## Built-in pin skins — OFFLINE, not from Storage (SkyPin skin task)
- `ARNode(type: ...)`: `NodeType.localGLTF2` loads a **bundled `.gltf`+`.bin`** from the
  Flutter **asset folder** (offline). `NodeType.webGLB` loads a **`.glb` from a URL**
  (network). `localGLTF2` does NOT accept a `.glb` and does NOT fetch a URL.
  => Bundle the built-in skins as `.gltf`+`.bin`; branch in code:
  `isBundledSkin(key) ? localGLTF2 : webGLB` (custom user uploads use `webGLB` from Storage).
- Generator: `scripts/gen_skins.py` (no deps) writes arrow/thunder/cyclone/beam as
  `.glb` AND splits them to `.gltf`+`.bin` for offline load. Declare `assets/skins/`
  in `pubspec.yaml` (recursive glob pulls in `.gltf`+`.bin`).
- glTF BIN chunk must be 4-byte aligned; when parsing a `.glb` by hand:
  `off += 8+clen; off = (off+3)&~3` before reading the `BIN\0` header, or the marker
  mis-reads. See references/procedural_skin_generation.md.

## Supabase Storage gotcha (anon insert)
- The **anon key CANNOT INSERT to Storage** — `storage.objects` INSERT requires
  `auth.uid()`. A `curl -H "apikey:<anon>"` upload returns HTTP 400. So never rely on
  anon uploads; built-in skins bundle locally (above), and custom uploads go only from
  the authenticated app client. Buckets themselves can't be created by schema SQL —
  note them as a manual dashboard step.

## Verification
- `flutter analyze` must report 0 errors before attempting a build.
- `flutter build apk --release` must emit an installable `.apk` (path printed at end).
- For the creator gate: call `create_room` with an anon client → expect `auth_required`.

## References
- references/ar_flutter_plugin_api.md — verified 0.7.3 API (managers, ARView callback shape,
  ARNode construction, ENU placement math).
- references/flutter_toolchain_macos.md — JDK17 + NDK reinstall + flutter create recipe.
- references/procedural_skin_generation.md — offline bundled `.gltf`+`.bin` skins,
  localGLTF2 vs webGLB, glTF BIN-chunk 4-byte alignment parsing pitfall.
- scripts/gen_skins.py — no-dep generator for the 4 procedural pin skins (.glb + split).
- templates/supabase_creator_gate.sql — the anon-rejecting RPC guard + RLS summary.
