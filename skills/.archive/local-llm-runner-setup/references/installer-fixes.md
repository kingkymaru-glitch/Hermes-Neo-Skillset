## Bonsai-demo / MLX on macOS
- `The 'metal' compiler is present but cannot execute.`
  - Run: `sudo xcodebuild -license accept && xcodebuild -runFirstLaunch && xcodebuild -downloadComponent MetalToolchain`
  - Then rerun the installer.

## Generic macOS toolchain preflight
- Before long MLX/metal builds, prefer confirming:
  - `xcode-select -p` returns a path
  - `xcrun -find metal` returns `/usr/bin/metal`
  - If not, the same 3-command sequence above usually fixes it.
