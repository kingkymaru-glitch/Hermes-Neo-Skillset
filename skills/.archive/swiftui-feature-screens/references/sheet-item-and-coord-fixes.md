# Calendar Screen Compile Fixes (AnglerGO, 2026-07)

Two distinct Xcode errors appeared on Run of `Features/Calendar/CalendarScreenView.swift`. Both are canonical SwiftUI issues; the fixes are reproduced here verbatim so they can be applied without re-deriving.

## Fix 1 — `Cannot find type 'CLLocationCoordinate2D' in scope`

**Root cause:** the file imports only `SwiftUI` but uses `CLLocationCoordinate2D` (in `activeCoordinate`, returning `shop.coordinate` and `MarineWeather.defaultCoordinate`). SwiftUI does NOT re-export CoreLocation, so the type is out of scope.

**Fix:** add the import at the top of the file.

```swift
import SwiftUI
import CoreLocation   // <-- added
```

**General rule:** any framework-defined type needs its own explicit import. If Xcode reports "cannot find type 'X' in scope" for a framework type, suspect a missing import before assuming a typo. Candidates in this project: `UIKit` (`UIActivityViewController`), `MapKit` (`MKCoordinateRegion`), `CoreLocation` (`CLLocationCoordinate2D`), `PhotosUI`, `CoreBluetooth`.

## Fix 2 — `.sheet(item:onDismiss:content:)` requires `String` conform to `Identifiable`

(Xcode misspells the param as `onDismis` in the error text — that is Apple's typo, not your code.)

**Root cause:** the share sheet was driven by a bare optional `String`:

```swift
@State private var shareText: String?
// ...
.sheet(item: $shareText) { text in          // item: needs an Identifiable value
    ActivityView(activityItems: [text])
}
// ...
shareText = shareMessage
```

The `item:` overload of `.sheet` binds an `Identifiable` value (it is NOT the `isPresented:` Bool overload). A plain `String` is not `Identifiable`, hence the error.

**Fix:** wrap the payload in a tiny `Identifiable` struct and switch the state + usages to it.

```swift
// New wrapper (place near the top of the file, after the model section):
private struct ShareItem: Identifiable {
    let id = UUID()
    let text: String
}

// State:
@State private var shareItem: ShareItem?   // was: String?
```

```swift
.sheet(item: $shareItem) { item in         // item is ShareItem (Identifiable)
    ActivityView(activityItems: [item.text])
}
```

```swift
// At the call site (the share Button):
shareItem = ShareItem(text: shareMessage)  // was: shareText = shareMessage
```

This pattern is reusable whenever a sheet is keyed by an arbitrary payload (detail/inspector sheets, share text, selected-entity drill-down). Keep the wrapper `private` to the file if it is not reused app-wide.

## Verification note (this environment cannot run a true iOS build)

The project target uses UIKit/SwiftUI, which the macOS CLI `swift` compiler cannot compile, so a green `xcodebuild` must run in Xcode itself. For fast static consistency checks in the CLI, grep with `-F` (fixed string), NOT `-E`, because `.sheet(item: ...)` contains regex metachars (`.`, `(`, `)`) that cause false-negative "FAIL" lines on correct code. Confirm the real lines with a `read_file` of the surrounding region.
