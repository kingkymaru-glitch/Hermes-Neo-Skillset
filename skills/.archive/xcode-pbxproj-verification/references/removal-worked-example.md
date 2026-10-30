# Worked example — removing a Swift file from an Xcode target

Real case: removing `StandingScreenView.swift` (the "Rankings" tab) from the AnglerGO
iOS project. Use as a copy-template when a hand-edit removal is needed and `xcodebuild`
cannot run.

## The three UUIDs (one per pbxproj layer)
| Layer            | UUID                          | How it reads in the file                                     |
|------------------|-------------------------------|--------------------------------------------------------------|
| PBXBuildFile     | `F32892DB2FEF795400A92EA7`    | `F32892DB2FEF795400A92EA7 /* StandingScreenView.swift in Sources */ = {isa = PBXBuildFile; fileRef = F32892DA2FEF794C00A92EA7 /* StandingScreenView.swift */; };` |
| PBXFileReference | `F32892DA2FEF794C00A92EA7`    | `F32892DA2FEF794C00A92EA7 /* StandingScreenView.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = StandingScreenView.swift; sourceTree = "<group>"; };` |
| PBXGroup         | `F39561082FEEDBBF006A7C95`    | `F39561082FEEDBBF006A7C95 /* Standings */ = { isa = PBXGroup; children = ( F32892DA2FEF794C00A92EA7 /* StandingScreenView.swift */, ); path = Standings; sourceTree = "<group>"; };` |

Note the BuildFile UUID (`...DB...`) is NOT the FileReference UUID (`...DA...`). The
Compile-Sources entry uses the BuildFile UUID; it points at the FileReference UUID via
`fileRef`.

## The four edits
1. **Compile Sources phase** — delete the `PBXBuildFile ... in Sources` line.
   (Fuzzy-patch collision risk here because neighbor lines repeat — use `str.replace`
   on the exact line if the patch tool reports 2 matches.)
2. **PBXFileReference section** — delete the `PBXFileReference` line.
3. **PBXGroup children** — delete `F32892DA2FEF794C00A92EA7 /* StandingScreenView.swift */,`
   from the `Standings` group's children; delete the now-empty `Standings` group itself.
4. **Disk** — optionally delete the `.swift` file (it is out of target either way).

## Verify
```
python3 verify_pbxproj.py AnglerGo.xcodeproj/project.pbxproj \
  --absent F32892DB2FEF795400A92EA7 F32892DA2FEF794C00A92EA7 F39561082FEEDBBF006A7C95
```
Expected: all Compile-Sources entries resolve, all three UUIDs absent, braces/parens
balanced, OVERALL PASS. This is static integrity only — real GREEN needs Xcode on a Mac.

## Pre-check (do this BEFORE editing)
Grep the Swift sources for the type name to confirm zero references outside the file
you are removing and the tab view. If `grep -rn "StandingScreenView" --include=*.swift .`
exits 1 (no matches beyond the file), the tab removal cannot break compilation.
