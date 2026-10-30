# LunaV theme reskin reference (iframe / standalone HTML)

When a self-contained `.html` (e.g. `public/studio/lunav_studio_safe.html`, loaded via
`<iframe>`) must match the LunaV app shell, remember it is a SEPARATE document and cannot
inherit the parent's CSS variables. Mirror the tokens as hardcoded values.

## Source of truth
`src/app/globals.css` defines the palette (MBUX-style dark + turquoise accent). Key tokens:
- `--mb-turquoise: #2f9bff` (accent / primary)
- `--mb-turquoise-dim: #2b93f0`
- panel `#1b1f26`, void/base `#14171c`, canvas `#0e1116`
- hairline `rgba(150,175,205,0.14)`, inset bg `rgba(15,18,22,0.6)`
- text primary `#e6ebf0`, secondary `#8fa1b3`, tertiary `#55677a`
- danger `#e5484d`, warning `#f5a623`, success `#3fb950`

## Tailwind class -> arbitrary-value remap (CDN JIT supports `[]`)
| Old (Standalone HTML)        | New (LunaV)                          |
|------------------------------|--------------------------------------|
| `text-cyan-400`              | `text-[#2f9bff]`                     |
| `text-cyan-300`              | `text-[#7db4ff]`                     |
| `text-slate-400`             | `text-[#8fa1b3]`                     |
| `text-slate-500`             | `text-[#55677a]`                     |
| `text-slate-900`             | `text-[#0e1116]`                     |
| `border-slate-700`           | `border-[rgba(150,175,205,0.14)]`    |
| `bg-slate-900/50`            | `bg-[rgba(15,18,22,0.6)]`            |
| `bg-cyan-500/10`             | `bg-[rgba(47,155,255,0.10)]`         |
| `border-cyan-500/40`         | `border-[rgba(47,155,255,0.40)]`     |
| `bg-cyan-500`                | `bg-[#2f9bff]`                       |
| `file:bg-slate-700`          | `file:bg-[#232831]`                  |
| `hover:file:bg-slate-600`    | `hover:file:bg-[#2b323c]`            |

Use `replace_all=true` for the high-frequency ones (`text-cyan-400`, `text-slate-400`,
`border-slate-700`, `bg-slate-900/50`, `bg-cyan-500`).

## JS-side THREE.js colors the class pass DOES NOT touch
Rewrite these by exact substring (also `replace_all` where repeated):
- `scene.background = new THREE.Color(0x0f172a)` -> `0x14171c`
- `scene.fog = new THREE.Fog(0x0f172a, ...)` -> `0x14171c`
- `const DEFAULT_COLOR = 0x0ea5e9` -> `0x2f9bff`
- sphere/extrude material `color: 0x0ea5e9` -> `0x2f9bff`
- `<input type="color" id="color-picker" value="#0ea5e9">` -> `value="#2f9bff"`
- grid helper `new THREE.GridHelper(50,50,0x334155,0x1e293b)` -> `0x2a313c,0x1b1f26`
- fallback `new THREE.Color('#0ea5e9')` in curve/helper builders -> `'#2f9bff'`

## Verify (no browser needed)
`search_files` the file for: `cyan`, `slate`, `#0ea5e9`, `#0f172a`, `0x0ea5e9`, `0x0f172a`,
`0x334155`, `0x1e293b`. Allowed survivors: `translateX`/`translateY` (substring "slate" only).
Any other hit = missed a remap.
