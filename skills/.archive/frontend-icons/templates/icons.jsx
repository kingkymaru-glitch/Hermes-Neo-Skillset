// Reusable SF-Symbols-style icon components. 24x24 grid, 1.6 stroke, round
// caps/joins, currentColor (theme-aware). Copy the ones you need into the app.
// Verified build-green as inline SVGs in my-digital-twin/src/App.jsx.

export function RadioTower({ size = 22 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
      <path d="M12 7V3M8.5 8.5 6 4M15.5 8.5 18 4M7 13a5 5 0 0 1 10 0"
        fill="none" stroke="currentColor" strokeWidth="1.6"
        strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4.5 13a7.5 7.5 0 0 1 15 0"
        fill="none" stroke="currentColor" strokeWidth="1.6"
        strokeLinecap="round" opacity="0.55" />
      <circle cx="12" cy="18" r="2.2" fill="currentColor" />
    </svg>
  )
}

export function FoldedMap({ size = 22 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
      <path d="M9 4h6a1 1 0 0 1 1 1v15l-4-2.5L8 20V5a1 1 0 0 1 1-1Z"
        fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M16 5h2a1 1 0 0 1 1 1v13l-3-2"
        fill="none" stroke="currentColor" strokeWidth="1.6"
        strokeLinejoin="round" opacity="0.55" />
    </svg>
  )
}

export function Link({ size = 22 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
      <path d="M9.5 14.5 14.5 9.5M8 11.5l-2 2a2.8 2.8 0 0 0 4 4l2-2M16 12.5l2-2a2.8 2.8 0 0 0-4-4l-2 2"
        fill="none" stroke="currentColor" strokeWidth="1.6"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function CpuChip({ size = 22 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
      <rect x="7" y="7" width="10" height="10" rx="2"
        fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M10 4v3M14 4v3M10 17v3M14 17v3M4 10h3M4 14h3M17 10h3M17 14h3"
        fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <rect x="10.5" y="10.5" width="3" height="3" rx="0.6" fill="currentColor" />
    </svg>
  )
}
