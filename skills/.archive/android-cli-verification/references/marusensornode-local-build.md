## Direct macOS bare-metal build path

This reference covers the actual CLI steps used to bring `MARUSensorNode` from zero to a local debug APK on macOS with no prior Android toolchain.

### Setup

```bash
brew install --cask android-studio
export JAVA_HOME="/Applications/Android Studio.app/contents/jbr/Contents/Home"
export ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
mkdir -p "$ANDROID_SDK_ROOT/cmdline-tools/latest"
```

### Commandline tools + SDK

```bash
# If needed, fetch cmdline-tools zip and unzip into:
# $ANDROID_SDK_ROOT/cmdline-tools/latest/

export PATH="$JAVA_HOME/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH"

yes | sdkmanager --sdk_root="$ANDROID_SDK_ROOT" \
  "platform-tools" \
  "platforms;android-34" \
  "build-tools;34.0.0"
```

### Gradle wrapper

```bash
cd ~/Desktop/S22\ Shifu/MARUSensorNode
./gradlew wrapper --gradle-version 8.4
```

If `/opt/gradle` is not writable, install Gradle under `$HOME/gradle` and symlink the binary into a writable PATH directory.

### Build + verify artifact

```bash
./gradlew assembleDebug
ls -lh app/build/outputs/apk/debug/app-debug.apk
```

### Device install

```bash
adb devices
./gradlew installDebug
```

## Pitfalls fixed during setup

- Fresh macOS can have `java` unset; `java_home` may return nothing. Always use Studio JBR explicitly.
- Direct `/opt/gradle` install can fail under normal user shell.
- First `sdkmanager` run complained about missing Java Runtime until `JAVA_HOME` was exported.
- `mergeDebugResources` failed due to duplicate `Theme.MARUSensorNode` definition between `themes.xml` and `styles.xml`. Fix: keep one theme definition and add explicit `android:theme="@style/Theme.MARUSensorNode"` on `<activity>` in `AndroidManifest.xml`.
- Kotlin compile failed with unresolved `Context`. Fix: add `import android.content.Context`.
- `BootReceiver.kt` was duplicated under both `service/` and `receiver/`; remove the duplicate and keep the canonical `receiver/BootReceiver.kt` file.
