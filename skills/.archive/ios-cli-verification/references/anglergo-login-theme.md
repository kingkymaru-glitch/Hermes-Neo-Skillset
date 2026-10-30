# AnglerGO — Login background & theme note

Condensed from the session where a theme-based `LinearGradient` on `LoginView`
crashed and was reverted to a solid color.

## Fast lesson
- `LoginView` background lives in `AnglerGo/App/Auth/LoginView.swift`, inside the
  `ZStack` of the `NavigationView`. Replacing the gradient with a solid
  `Color(red: 0.07, green: 0.12, blue: 0.20).ignoresSafeArea()` is the safe,
  non-crashing baseline. White logo/text/cards stay legible on it.
- `ThemeManager.gradient` (in `Features/Theme/ThemeManager.swift`) exists and
  returns a `Gradient` from the active `AppTheme`. Using a *theme gradient* as a
  `LinearGradient(colors:)` background is what crashed — if the user later wants a
  gradient back, drive it from a verified, non-optional color array, not a loosely
  typed theme property.

## User workflow preference (carried in SKILL.md Pitfalls)
The user builds in Xcode themselves (Cmd+B) and pastes compiler errors back. They
explicitly do NOT want the "I can't run/test this, only Xcode can" disclaimer
repeated every turn. Lead with the static check result; attach at most one short
"real build runs in Xcode" sentence on a turn that introduces a fresh edit.

## Verification done for the revert
- Brace depth 0 (string-aware scan) — balanced.
- `LinearGradient` absent; `ThemeManager.gradient` / `ThemeManager` refs = 0.
- Solid `Color(red:...)` background present in the ZStack.
- Ad-hoc static only; not a green build.
