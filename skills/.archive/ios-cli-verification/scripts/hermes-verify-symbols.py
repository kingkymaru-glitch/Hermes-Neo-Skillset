#!/usr/bin/env python3
# hermes-verify-symbols.py — reusable Swift STATIC symbol-existence checker that
# tolerates stored(`let`)/computed(`var`) properties and `= Type` / `: Type`
# annotations, so "does this type have member X?" assertions don't self-false-FAIL.
#
# WHY: an AnglerGO WeatherService verification pass FALSE-FAILED on
#   `let tideHighs: [Date]`   (checker pinned `var`)
#   `static let defaultCoordinate = CLLocationCoordinate2D(...)`  (checker pinned `: Type`)
# The code was correct; the checker regex was wrong. A checker bug must NEVER be
# reported as a code defect — use the tolerant helpers below.
#
# This is AD-HOC STATIC analysis only (no Swift compiler / iOS SDK on CLI).
# Re-run after each edit; clean up the temp copy afterwards.

import re, sys

# ---- tolerant matchers (edit the regexes below if your naming differs) ----
def prop(name):        return rf"(?:let|var)\s+{name}\b"   # stored OR computed property
def static_prop(name): return rf"static\s+(?:let|var)\s+{name}\b"
def fn(name):          return rf"(?:func|static func)\s+{name}\b"
def decl(name, kinds=("struct", "enum", "class", "actor", "protocol")):
    return rf"(?:{'|'.join(kinds)})\s+{name}\b"

# =====================================================================
# CONFIG — EDIT PER EDIT. Each REQUIRE entry: (tolerant_regex, label).
# ABSENT  = exact substrings that MUST be gone. PRESENT = must exist.
# =====================================================================
REQUIRE = [
    (static_prop("defaultCoordinate"),           "MarineWeather.defaultCoordinate"),
    (r"static func estimate\(for date: Date\) -> MarineWeather", "estimate(for:)"),
    (decl("WeatherServiceError", ("enum",)),     "WeatherServiceError"),
    (prop("tempLabel"),        "tempLabel"),
    (prop("windLabel"),        "windLabel"),
    (prop("weatherSymbol"),    "weatherSymbol"),
    (prop("tideSummaryValue"), "tideSummaryValue"),
    (prop("moonPhaseName"),    "moonPhaseName"),
    (prop("tideHighs"),        "tideHighs"),
    (prop("tideLows"),         "tideLows"),
]
ABSENT  = ['"29°C"', '"Light Wind"', '"Flood Tide"', 'forecastData',
           'WeatherDropdown()', 'TideDropdown()']
PRESENT = ['func loadMarine() async', 'marine: marine,',
           'WeatherDropdown(forecast: forecast)', 'TideDropdown(marine: marine)',
           'MarineWeather.tideCurveHeights(for:']

def check_file(path):
    try:
        s = open(path).read()
    except OSError as e:
        return [f"cannot read {path}: {e}"]
    P = []
    for pat, label in REQUIRE:
        if not re.search(pat, s):
            P.append(f"missing {label}")
    for tok in ABSENT:
        if tok in s:
            P.append(f"should be absent: {tok}")
    for tok in PRESENT:
        if tok not in s:
            P.append(f"should be present: {tok}")
    for op, cl in [("{", "}"), ("(", ")"), ("[", "]")]:
        if s.count(op) != s.count(cl):
            P.append(f"delim {op}{s.count(op)}/{cl}{s.count(cl)}")
    return P

if __name__ == "__main__":
    files = sys.argv[1:] or []
    if not files:
        print("usage: hermes-verify-symbols.py <file1.swift> [file2.swift ...]")
        print("       (edit REQUIRE/ABSENT/PRESENT CONFIG above per edit)")
        sys.exit(2)
    allP = []
    for f in files:
        allP += check_file(f)
    print("AD-HOC STATIC RESULT:", "PASS" if not allP else f"FAIL -> {allP}")
    sys.exit(1 if allP else 0)
