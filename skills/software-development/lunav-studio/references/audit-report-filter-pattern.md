# Audit Report — severity filter + timestamps

Implementation checklist for adding severity filtering and per-defect
timestamps to the Audit Report tab in `ProjectWorkspace.tsx`.

## 1. Add filter state (near other useState calls, ~line 264)

```tsx
/* Severity filter on the Audit Report — inspector filters findings by status */
const [reportFilter, setReportFilter] = useState<"ALL" | MarkerStatus>("ALL");
```

## 2. Add filtered markers useMemo (after `counts` useMemo)

```tsx
const filteredMarkers = useMemo(
  () => reportFilter === "ALL" ? allMarkers : allMarkers.filter((m) => m.status === reportFilter),
  [allMarkers, reportFilter],
);
```

## 3. Add filter pill bar (between executive summary block and the table)

```tsx
{/* ── Severity Filter Pills ── */}
<div className="mb-5 flex items-center gap-2">
  <span className="mr-1 text-[0.62rem] font-bold uppercase tracking-[0.18em]" style={{ color: "var(--txt-tertiary)" }}>Filter:</span>
  {(["ALL", "PASS", "WARNING", "FAIL"] as const).map((f) => (
    <button
      key={f}
      onClick={() => setReportFilter(f)}
      className={`mb-btn flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold transition-colors ${
        reportFilter === f ? "mb-btn-primary" : ""
      }`}
    >
      {f !== "ALL" && (
        <span className="inline-block h-2 w-2 rounded-full" style={{ background: STATUS_COLOR[f] }} />
      )}
      {f}
    </button>
  ))}
</div>
```

## 4. Add "Time" column to table

**Colgroup** — add a `<col>` for the Time column (adjust widths by shrinking others proportionally):

```tsx
<colgroup>
  <col style={{ width: "4%" }} />
  <col style={{ width: "10%" }} />   {/* Model — was 12% */}
  <col style={{ width: "12%" }} />   {/* Component — was 14% */}
  <col style={{ width: "10%" }} />   {/* Severity — was 11% */}
  <col style={{ width: "9%" }} />    {/* NEW: Time */}
  <col style={{ width: "19%" }} />   {/* Findings — was 22% */}
  <col style={{ width: "9%" }} />    {/* Evidence — was 10% */}
  {readOnly && <col style={{ width: "16%" }} />}  {/* was 18% */}
  <col style={{ width: readOnly ? "11%" : "17%" }} />
</colgroup>
```

**Heads** — insert "Time" in the header arrays at position 5 (after Severity):

```tsx
{readOnly
  ? ["#", "Model", "Component", "Severity", "Time", "Findings", "Evidence", "Client Feedback", "Actions"]
  : ["#", "Model", "Component", "Severity", "Time", "Findings", "Evidence", "Actions"]
}
```

**Cell** — add the timestamp `<td>` after the status chip `<td>`:

```tsx
<td className="px-5 py-4 text-[0.68rem]" style={{ color: "var(--txt-tertiary)" }}>
  {new Date(m.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
</td>
```

## 5. Switch table data source + fix colSpan

Replace `allMarkers.length === 0` → `filteredMarkers.length === 0` and
`allMarkers.map(...)` → `filteredMarkers.map(...)`.

Update empty-state `colSpan` to match new column count:
- readOnly: 9 columns (was 8)
- inspector: 8 columns (was 7)

## Pitfalls

- **Escaped quotes in patch tool**: When patching strings containing `<"ALL">`, the patch tool may inject literal backslashes (`\"ALL\"`). Verify with `od -c <line>` after patching and redo the patch if needed.
- **colSpan mismatch**: After adding a column, the empty-state `<td colSpan>` must be updated or the row won't span the full table width.
- **Column widths must still total ~100%**: When inserting a new column, shrink adjacent columns proportionally so the sum approximates 100%. Exact % doesn't matter (browser handles fractional), but severe overflow causes wrapping.