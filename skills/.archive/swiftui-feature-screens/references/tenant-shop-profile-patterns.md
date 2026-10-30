# Tenant / Shop Profile Patterns (AnglerGo)

## AvailabilityCalendarView Pattern

A self-contained month calendar component:

```swift
struct AvailabilityCalendarView: View {
    let shop: Shop
    @Binding var selectedDate: Date?
    @State private var currentMonth: Date = Date()
    private let calendar = Calendar.current

    // Weekday headers: ["Sun", "Mon", ...]
    // Month nav: ◀ chevron.left ▶ chevron.right
    // Grid: LazyVGrid(columns: 7, spacing: 6)
    // DayCell: RoundedRectangle(cornerRadius: 8), color-coded

    // Color logic:
    //   isSelected → .blue fill, white text
    //   isPast → .systemGray6, dimmed text
    //   hasAvailable → .green.opacity(0.12)
    //   partiallyBooked → .yellow.opacity(0.12)
    //   otherwise → .systemGray6

    // Legend: 3 dots (green/yellow/gray) + labels
}
```

## Shop Model (Core/Models/Shop.swift)

```swift
enum ShopType: String, CaseIterable, Identifiable, Codable {
    case tackleShop = "🎣 Fishing Tackle"
    case boatCharter = "🛥️ Boat Charter"
    case baitTackle  = "🪱 Bait & Tackle"
    case guidingService = "🧭 Fishing Guide"
    case rental = "🚤 Equipment Rental"
    case resort = "🏝️ Fishing Resort"
    var icon: String { ... } // custom SF symbol per type
}

struct TimeSlot: Identifiable, Codable {
    let startTime: String  // "09:00"
    let endTime: String    // "12:00"
    let label: String      // "Morning Trip"
    var isAvailable: Bool
}

struct Shop: Identifiable, Codable {
    var availability: [String: [TimeSlot]]  // key: "yyyy-MM-dd"
    var googleCalendarID: String?
    var ownerUserID: String?
    static let mockShops: [Shop]  // 3+ sample shops for prototyping
}
```

## MapView (MKMapView Wrapper)

```swift
struct MapView: UIViewRepresentable {
    let shop: Shop
    func makeUIView(context:) -> MKMapView { ... }
    func updateUIView(_ map:, context:) {
        // Add MKPointAnnotation
        // Set region: MKCoordinateRegion(center: shop.coordinate, span: 0.01)
        // Add MKCircle overlay (radius 100m)
    }
    // Coordinator conforms to MKMapViewDelegate
    //   - rendererFor overlay: MKCircleRenderer
    //   - viewFor annotation: MKMarkerAnnotationView with glyphText
}
```

## Key Conventions

- **Confirm before building**: Ask 2-3 targeted design questions before writing the UI. The user prefers this to guessing.
- **Scaffold the model first** (Shop.swift), then write the view (TenantScreenView.swift). This keeps the view clean.
- **Mock data is fine** for prototyping; mark integration points with `// TODO: Firebase/Google Calendar sync` comments.
- **Availability uses ISO date keys** (`"yyyy-MM-dd"` → `[TimeSlot]`) — flexible for any calendar backend.
- **No Xcode on CLI**: Verify by hand and tell the user to build in Xcode.
- **UI work**: Hold off on linters/tests until user approves the visual result.