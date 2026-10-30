# Xcode build-failure triage (non-pbxproj-corruption)

When Cmd+B fails and it's NOT "project is damaged", check these three first.
All three are Xcode-state / wiring issues, NOT code bugs — but they mask
real downstream errors until cleared.

## 1. "Cannot find 'XService' in scope" (N identical errors)
- **Cause:** a Swift file exists on disk but is NOT registered in
  `project.pbxproj`'s 4 sections (PBXBuildFile, PBXFileReference, group
  `children`, PBXSourcesBuildPhase). Common when the file was created via a CLI
  `write_file` / `execute_code` — those do NOT touch pbxproj. Every file that
  references `XService` then errors once, so you see N copies of the same message.
- **Fix:** add the 4 wires (see "Safe workflow for adding a new .swift file's
  wiring"). Use a consistent invented UUID prefix. Run the verify block after.
- **Telltale:** the error count == number of files importing/using the missing
  type, and exactly ONE file is absent from the pbxproj. This is the inverse of
  the corruption failure mode — it's a MISSING registration, not a broken one.
- **Verify from CLI before handing back:** `grep -c "XService" project.pbxproj`
  should be >=4 (fileRef, group child, buildFile, sources). If 0, it was never
  registered. Confirm the file is physically on disk at the resolved group path.

## 2. "Build service could not create build operation: MsgHandlingError(message: \"unable to initiate PIF transfer session (operation in progress?)\")"
- **Cause:** Xcode's build service is wedged — usually mid-indexing or a previous
  build session is still locked. It has NOT re-read the .xcodeproj, so any pbxproj
  edits you made are invisible; it keeps using the stale project graph (which is
  why the "Cannot find" errors above can persist even after you fixed the pbxproj).
- **Fix:** stop the build (square or Cmd+.), then **Cmd+Shift+K** (Clean Build Folder).
  If the error persists, fully **QUIT Xcode (Cmd+Q)** and reopen the .xcodeproj —
  reopening forces a fresh PIF transfer and picks up your pbxproj changes.
- This is an Xcode-infra error. Clear it FIRST, then re-evaluate remaining errors
  (the "Cannot find" ones may then resolve once the project graph reloads).

## 3. "Received invalid response at https://github.com/... Make sure it is a package collection URL."
- **Cause:** pasted a GitHub repo URL into the **Add Package Collection** dialog
  (for curated JSON index feeds) instead of **Add Package Dependency**.
- **Fix:** cancel that dialog; use Xcode menu **File -> Add Package Dependencies...**,
  paste the repo URL there, pick the products, Add Package. (A raw GitHub repo URL
  is a *dependency*, not a *collection* — the collection box expects a JSON index.)
