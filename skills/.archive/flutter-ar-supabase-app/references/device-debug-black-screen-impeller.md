# On-device debugging + the Impeller black screen (SkyPin, 2026-08-31)

Durable lessons from the hardest debugging stretch: an AR app showing a black
screen + "GPS unavailable" on a physical S22 when permissions were fine and the
server was verified working. Covers release-build diagnostics, logcat capture,
and the real black-screen root cause (Impeller vs ar_flutter_plugin).

## debugPrint is stripped in RELEASE builds — the diagnostics-vanished trap
When you add `debugPrint('[SKYPIN] ...')` for diagnostics and then run
`flutter build apk --release`, those prints NEVER appear in logcat. `debugPrint`
is a no-op in release/AOT builds. This silently eats an entire debugging loop
("I added logging, nothing shows").

Fixes (pick per need):
- Use `print()` instead of `debugPrint()` if you need it to survive a release
  APK. `print()` emits to logcat in both debug and release.
- OR build a DEBUG APK to capture diagnostics: `flutter build apk --debug`,
  install that, capture logs. Confirm it's the debug build via
  `adb shell dumpsys package <pkg>` showing `DEBUGGABLE` in flags.
The release APK is what you ship/test by default, so this bites even on the
"latest build you just installed." Verify the installed version with
`aapt dump badging <apk>` -> `versionName`/`versionCode`.

## Reading real device state (stop guessing, read the logs)
A pro connects the phone and reads logcat instead of inferring. The flow:
```bash
adb devices -l                                   # confirm device
adb install -r ~/Desktop/SkyPin-V0.xx.apk        # install
adb logcat -c                                    # clear buffer
adb shell am start -n <pkg>/.MainActivity        # launch (monkey -p <pkg> -c LAUNCHER 1 if activity name unknown)
# capture to a file for a window while the user interacts:
adb logcat -v time > /tmp/logs.txt               # run as background=true, then kill
```
Then grep for your tag, `flutter`, `LocationManager`, `FusedLocation`, `GmsCore`,
`Gralloc`, `AHardwareBuffer`, `libpenguin`, `Error`/`Exception`. Ground truth
from the device (permission status, whether the location service is on, whether
GPS events fire, the exact renderer in use) beats any amount of code-reading
guessing.

Note: `libpenguin.so not found` in logcat is BENIGN noise (some Samsung/Android
component probing), NOT your AR lib — the real AR native libs present in the APK
are `libarsceneview_jni.so`, `libarcore_sdk_*.so`, `libfilament-jni.so`. Don't
chase it.

## The Impeller black screen — ar_flutter_plugin's Sceneform vs Vulkan
Root cause of a persistent AR black screen on newer devices/Android (S22, A16):
Flutter's new default renderer Impeller (Vulkan) conflicts with ar_flutter_plugin
0.7.x's Sceneform engine, which needs OpenGL ES. The log shows the smoking gun:
```
I/flutter: Using the Impeller rendering backend (Vulkan).
E/Gralloc4: isSupported(1, 1, 56, 1, ...) failed with 5
E/qdgralloc: gralloc failed to allocate err=Invalid argument format 56 size 0 WxH 4x4
E/AHardwareBuffer: GraphicBuffer(w=4, h=4) failed (Unknown error -5)
```
The GPU can't allocate buffers for the AR/Sceneform surface -> black camera feed.
Permissions and GPS are fine (that's why "GPS unavailable" was a red herring).

Fix: disable Impeller so Flutter falls back to the Skia/OpenGL ES renderer that
ar_flutter_plugin's Sceneform can share. Add to `AndroidManifest.xml` inside
`<application>`:
```xml
<meta-data
    android:name="io.flutter.embedding.android.EnableImpeller"
    android:value="false"/>
```
Confirm it took effect in logcat — you should see an OpenGL renderer (e.g.
`AdrenoGLES-0: OpenGL ES Shader Compiler`) and NO more Gralloc/AHardwareBuffer
allocation failures.

## PostgREST caches function bodies by OID — DROP + CREATE to force refresh
When a Supabase RPC (`create_room` etc.) body changes but the app STILL gets the
old error (`function gen_random_bytes ... does not exist` code 42883), `CREATE OR
REPLACE FUNCTION` keeps the SAME function OID and PostgREST caches by OID — so
`notify pgrst,'reload schema'` alone does NOT pick up the new body. The DB
`pg_proc.prosrc` shows the new body (so it looks "fixed"), yet the API serves the
old one. Fix: DROP the function, then CREATE it (new OID), then `notify pgrst,
'reload schema'`. Diagnose with:
```sql
-- confirm the ONE real body (should be a single row):
select oid, pg_get_function_identity_arguments(oid), prosrc
from pg_proc where proname='create_room' and pronamespace='public'::regnamespace;
```
And reproduce the app's exact API call to see the REAL live error, e.g. via
curl/Python against `POST /rest/v1/rpc/create_room` with a real anon session
token — the app path, not just running SQL. (Chain bugs surfaced this way: first
`gen_random_bytes` -> pgcrypto, then `encode(md5(),'hex')` -> text/bytea, then
`returning id, expires_at` -> ambiguous vs the PL/pgSQL var; qualify as
`rooms.expires_at`.)
