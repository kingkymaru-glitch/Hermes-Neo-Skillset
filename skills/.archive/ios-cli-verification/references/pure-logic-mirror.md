# Pure-Logic Mirror Test (CLI, no Xcode)

When you edit a pure Swift function (scoring, tide extrema, state machine, date math)
in an iOS target, you can verify its logic on the macOS `swift` CLI without UIKit/iOS SDK.

The executable mirror test = copy the function into a standalone `.swift`, drive it with
assertions, run `swift file.swift`. NO iOS imports, so it links and executes on the host.

## The trap this session hit (READ FIRST)
A compact one-liner like:

    let windS:Int = wind<15?100:(wind<25?60:20)

FAILS TO COMPILE with "consecutive statements on a line must be separated by ';'" and
"cannot use optional chaining on non-optional value". Swift's parser reads `15?` as
OPTIONAL CHAINING (`b?`), not the ternary `?`. The app code was fine — only the
throwaway test was malformed. This is a FALSE FAIL.

FIX: always space the operators (or use `if/else`):

    let windS: Int = wind < 15 ? 100 : (wind < 25 ? 60 : 20)

And write the harness as clean MULTI-LINE Swift — never one-liners. If the mirror won't
compile, confirm the REAL file still parses (`swiftc -parse RealFile.swift`); if green,
the harness is the bug, not the app.

## Clean template (AnglerGO "Suasana" readiness — verified 5/5)
Paste the real function(s) minus iOS-only imports; drive with hand-built inputs + `assert`.

```swift
import Foundation

// --- paste the REAL pure function(s) here (no UIKit/SwiftUI) ---
func score(code: Int, wind: Double, wave: Double?, daylight: Bool) -> (Int, String) {
    let ws: Int
    switch code {
    case 0...3:   ws = 100
    case 45, 48:  ws = 60
    case 51...67: ws = 30
    case 71...86: ws = 20
    case 80...99: ws = 25
    default:      ws = 50
    }
    let windS: Int = wind < 15 ? 100 : (wind < 25 ? 60 : 20)
    let wv = wave ?? max(0.1, wind / 25.0)
    let waveS: Int = wv < 1.0 ? 100 : (wv < 2.0 ? 60 : 20)
    let dayS: Int = daylight ? 100 : 40
    let t = Int(Double(ws) * 0.4 + Double(windS) * 0.3 + Double(waveS) * 0.2 + Double(dayS) * 0.1)
    let l: String
    switch t {
    case 85...100: l = "Optimal"
    case 65..<85:  l = "Good"
    case 40..<65:  l = "Fair"
    default:       l = "Poor"
    }
    return (t, l)
}

func resolveTide(times: [Date], heights: [Double]) -> (Date?, Date?, Double?) {
    let now = Date()
    guard times.count == heights.count, !times.isEmpty else { return (nil, nil, 0.5) }
    var best = 0, bestD = Double.infinity
    for i in 0..<times.count {
        let d = abs(times[i].timeIntervalSince(now))
        if d < bestD { bestD = d; best = i }
    }
    let cur = heights[best]
    var hi: [Date] = [], lo: [Date] = []
    for i in 1..<times.count - 1 {
        if heights[i] > heights[i - 1] && heights[i] >= heights[i + 1] { hi.append(times[i]) }
        if heights[i] < heights[i - 1] && heights[i] <= heights[i + 1] { lo.append(times[i]) }
    }
    return (hi.filter { $0 >= now }.sorted().first,
            lo.filter { $0 >= now }.sorted().first, cur)
}

// --- assertions (exit non-zero on any failure) ---
let (s1, l1) = score(code: 0, wind: 8, wave: 0.4, daylight: true)
assert(l1 == "Optimal" && s1 == 100, "perfect should be Optimal/100")

let (_, l2) = score(code: 95, wind: 40, wave: 3.0, daylight: true)
assert(l2 == "Poor", "storm should be Poor")

let (_, l3) = score(code: 2, wind: 8, wave: nil, daylight: true)
assert(l3 == "Optimal", "marine-down wave estimate should still score")

let base = Date()
let t = [base.addingTimeInterval(-3600),
        base.addingTimeInterval(1800),
        base.addingTimeInterval(7200),
        base.addingTimeInterval(10800)]
let r = resolveTide(times: t, heights: [0.1, 1.2, 0.2, 1.3])
assert(r.0 == t[1] && r.1 == t[2] && abs((r.2 ?? -1) - 1.2) < 0.001, "tide extrema")

let r5 = resolveTide(times: [], heights: [])
assert(r5.0 == nil && r5.1 == nil && r5.2 == 0.5, "empty tide graceful fallback")

print("MIRROR PASS")
```

Run: `swift /tmp/hermes-verify-readiness.swift` (or via `mktemp -t hermes-verify-XXXXXX.swift`).
Non-zero exit = genuine logic defect.
