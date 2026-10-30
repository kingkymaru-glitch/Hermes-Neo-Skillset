# AnglerGO CalendarScreenView rework — punch-list (Task 7) — real example

Source: `Features/Calendar/CalendarScreenView.swift` (~630 lines). Status at review:
NOT STARTED on rework; the screen already exists with all four sections but every data
source is mock/hardcoded.

## Current reality (grounded in the code)
- `shopCalendarSection` reads `Shop.mockShops`. Horizontal shop chips are DEAD buttons
  (`// Select a shop? Future: jump to shop tab`). No nav, no highlight.
- `weatherTideSection` hardcoded strings ("31°C", "Rising", "High 14:32",
  "Waxing Gibbous", "8 km/h NE"). Zero API.
- `eventsSection` shop slots from mock + personal trips from `@State trips`. Share works
  (UIActivityViewController bridge already present).
- Create-trip sheet saves to `@State` only → lost on relaunch.
- `AppState` already has a working Firestore pattern (`loadCatchesFromCloud` snapshot
  listener + `addCatch`) that trip persistence can mirror.
- `Shop` model already has `availability`, `googleCalendarID`, `ownerUserID` fields.
  Owner dashboard (Task 6) saves in-memory only — blocks real shop-calendar sync.
- `AppState.loadCatchesFromCloud` still builds `CatchItem` with the OLD 5-arg init →
  catches vanish on reload (pre-existing gap, fix opportunistically).

## Verification constraint
No Xcode on the CLI host. Every change is STATIC-VERIFIED ONLY (syntax + pbxproj
integrity). Real compile/run is the user's ⌘B in Xcode.

## Punch-list (one item per turn)
A. Dead-code / navigation fix (local-only, no deps)
   A1. Make shop chips navigate (focus calendar on shop's next-available date, OR jump
       to the shop tab via shared `AppState.selectedShopID` + MainTabView switch). Pick ONE.
   A2. Highlight active shop chip so surfaced availability is unambiguous.
B. Trip persistence (mirror existing Firestore pattern)
   B3. `AppState`: add `myTrips`, `loadTripsFromCloud()` listener, `saveTrip`/`deleteTrip`.
   B4. Make `FishingTrip` `Codable`.
   B5. `CalendarScreenView` uses `appState.myTrips` instead of `@State trips`.
   B6. Sign-in-aware empty state when logged out (don't crash on `anonymous` writes).
C. Real weather + tide (Open-Meteo = no API key)
   C7. `WeatherService` (async URLSession) → Open-Meteo forecast for selected date/location.
       Replace hardcoded "31°C".
   C8. Tide: Open-Meteo marine is thin → keep a clearly-labeled *estimated* note until a
       tide API key exists.
   C9. Loading/error states; graceful fallback to mock string on failure, clearly marked.
D. Shop calendar backend sync (needs Firestore schema + owner write path)
   D10. `shops` collection mirroring `Shop`; make owner dashboard (Task 6) actually save,
        not in-memory only.
   D11. `CalendarScreenView` reads shops from a listener instead of `Shop.mockShops`.
E. Google Calendar sync — DEFER (external OAuth, undecided).

## Lesson encoded
When asked "what should the rework focus on first?" the user picked the review/punch-list
option. Lead with the review, never with edits, on ambiguous rework.
