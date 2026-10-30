---
name: android-cli-verification
description: >
  Verify and build Android apps locally from a CLI when Android Studio is installed
  or installable, but the host lacks an existing Android toolchain. Covers macOS
  brew-based setup, using Android Studio’s bundled JBR JDK, commandline-tools
  install, SDK package install, Gradle wrapper generation, and the most common
  build breakers seen when scaffolding apps from a markdown guide. Includes an
  ad-hoc temp-script verification pattern for changed files and APK artifacts.
  Trigger: user asks to install, build, or run an Android app locally; or you
  need verification evidence after editing Android/Kotlin/XML sources without
  Studio.
---

# Android CLI Verification

## Outcome

A reproducible local debug build and an artifact at:
`app/build/outputs/apk/debug/app-debug.apk`

## Default Environment Setup

### Android Studio + JDK

```bash
brew install --cask android-studio
```

macOS-installed Android Studio bundles a JBR JDK. Use it explicitly; plain `java`/`java_home` may be unset on a fresh Mac, and `sdkmanager` will fail with “Unable to locate a Java Runtime.”

```bash
export JAVA_HOME="/Applications/Android Studio.app/contents/jbr/Contents/Home"
java -version        # expected: OpenJDK 21
javac -version
```

### Android SDK

If Studio was just installed, the SDK may not exist yet. Install commandline-tools and required packages manually.

Downloaded cmdline-tools zip paths can rot; if one URL fails, fall back to another known mac ARM zip before abandoning. Unzip into `$ANDROID_SDK_ROOT/cmdline-tools/latest` so `sdkmanager` lands at `$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager`.

```bash
export ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
mkdir -p "$ANDROID_SDK_ROOT/cmdline-tools/latest"

# Download cmdline-tools zip, unzip into $ANDROID_SDK_ROOT/cmdline-tools/latest
# then install required packages.
yes | "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" \
  --sdk_root="$ANDROID_SDK_ROOT" \
  "platform-tools" \
  "platforms;android-34" \
  "build-tools;34.0.0"
```

### Path

```bash
export PATH="$JAVA_HOME/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH"
which adb && adb version
which sdkmanager && sdkmanager --version
```

## Gradle

Use the project’s wrapper if present; otherwise generate it.

```bash
cd <project>
./gradlew wrapper --gradle-version 8.4
```

If `gradlew` cannot write, ensure the directory is writable.

Pitfall: `/opt/gradle` may not be writable in a normal user shell. Use `$HOME/gradle` for the distribution and symlink the binary into a directory on PATH, e.g. `/opt/homebrew/bin/gradle`, if that path exists and is writable.

## Common Build Fixers

### Duplicate theme/styles resources

When scaffolding from a guide, `themes.xml` and `styles.xml` may both define the app theme. Remove one explicit duplicate or unify references. Keep `android:theme` on `<activity>` in `AndroidManifest.xml`.

### Missing import in Kotlin

A class can compile with `Context` unresolved if only referenced inside a composable lambda and `import android.content.Context` is missing.

### Duplicate class files

If a class like `BootReceiver.kt` exists under both `service/` and `receiver/`, keep only the canonical path and remove the duplicate. Package and manifest declarations must match.

### AndroidManifest syntax

Ensure:
- `android:theme` references an existing style
- `<activity>`, `<service>`, and `<receiver>` declarations are self-closing or closed properly
- `tools:targetApi="34"` is allowed on the `<application>` node

### local.properties

For projects scaffolded from a guide, first-time local builds can fail even when the SDK already exists on the machine. Create `local.properties` at the project root with:

```bash
sdk.dir=/Users/kamarulhk/Library/Android/sdk
```

Pitfall: `local.properties` is machine-local and should be ignored in version control. Also add a `.gitignore` for local SDK/build artifacts so they do not clutter commits:

```bash
cat >> .gitignore <<EOF
local.properties
.gradle
/build
EOF
```

If `./gradlew assembleDebug` fails early with `SDK location not found`, this is the first missing piece to verify before changing module configs.

### Ad-Hoc Verification Script pattern

Create an OS-safe temp script under `/var/folders/.../` with `hermes-verify-` prefix. Verify:
1. APK exists and size > 1 KB
2. Manifest contains expected theme/receiver/service entries
3. Source files contain expected imports/classes
4. No duplicate canonical class files

Run, then delete the temp script.

Example shape:

```bash
TMPDIR=$(python3 -c 'import tempfile,sys; print(tempfile.gettempdir())')
VERIFY_FILE="$TMPDIR/hermes-verify-<project>.sh"
```

Do not claim verification until the script exits 0 or an actual concrete blocker exists.

## Failure Handoff

If `adb devices` returns empty, tell the user to enable USB debugging on the S22 and authorize the fingerprint. If a compile error remains, re-run `./gradlew assembleDebug` with `--stacktrace` and fix the first failure only.

## References

- `references/marusensornode-local-build.md`: concrete steps and exact paths used to bring MARUSensorNode to a local debug APK on macOS.