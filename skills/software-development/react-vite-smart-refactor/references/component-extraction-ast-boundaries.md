# Splitting a monolithic component file (AST boundaries, not line ranges)

Use when a single component file has grown to thousands of lines and the user
asks to break it up. The goal is a mechanical, provably-behaviour-preserving
split: same JSX, same props, same runtime — just in more files.

## Rule 0 — NEVER slice by line range

Nested JSX makes line-range extraction silently wrong. A slice that looks right
will either swallow a **parent's** closing tag (the extracted file now has an
unbalanced tree and the build fails with `Expected corresponding JSX closing
tag`) or pull a **sibling** section in (the next section's markup ends up inside
the extracted file). Both happened repeatedly in one session before switching
to an AST.

Line arithmetic also lies about balance: `<div ... />` self-closing counts as an
open with no matching close, so a naive `count('<div') == count('</div>')` check
reports a false MISMATCH on perfectly valid JSX. Count self-closing tags out
before comparing.

### Why the naive "stop at the first `)}`" cut fails
When a replacement block ends at a nested conditional, cutting to the first
`      )}\n` stops at an INNER close and leaves the rest of the original JSX
orphaned in place — you get the new component AND a duplicate tail, so the file
no longer parses (`Expected corresponding JSX closing tag for <div>` at a `</label>`
or `</div>` deep in the leftovers). Two shapes to watch for:
- **A block whose body contains its own `{cond && (...)}`** — the inner `)}`
  matches first. Cut to the OUTER close, or better, cut by AST bounds.
- **A block with an unclosed wrapper left behind** — after replacing, the parent's
  own `</div>` is gone (swallowed) or duplicated. Symptom: build error pointing at
  a tag nowhere near your edit.

After ANY scripted replacement, before building: parse the file with the same
babel call. It names the exact line of the orphan in one shot, instead of the
bundler's slower round-trip.

### Verify by re-deriving bounds, not by trusting a saved JSON
If you write bounds to a JSON file and then make ANY earlier edit (extracting a
sibling section first), those line numbers are STALE — every later section shifts.
Re-run the babel walker against the CURRENT file before each extraction pass, or
extract strictly bottom-up so earlier bounds stay valid. A stale bounds file
extracted a 217-line tab as 796 lines and pulled the whole modal block into it.

## The recipe

`@babel/parser` ships inside `node_modules` of any Next/Vite app — use it. Walk
to the component function, find its returned JSX root, and read each child's
exact `loc.start.line` / `loc.end.line`.

```js
const parser = require('@babel/parser');
const src = fs.readFileSync('src/components/Big.tsx', 'utf8');
const ast = parser.parse(src, { sourceType: 'module', plugins: ['jsx', 'typescript'] });

function walk(n, cb) {
  if (!n || typeof n !== 'object') return;
  cb(n);
  for (const k of Object.keys(n)) {
    const v = n[k];
    if (Array.isArray(v)) v.forEach((c) => walk(c, cb));
    else if (v && typeof v === 'object' && v.type) walk(v, cb);
  }
}

// 1. locate the component function
let fn = null;
walk(ast, (n) => {
  if (n.type === 'FunctionDeclaration' && n.id?.name === 'Big') fn = n;
});

// 2. its largest returned JSXElement = the render root
let best = null;
walk(fn.body, (n) => {
  if (n.type !== 'ReturnStatement') return;
  let a = n.argument;
  while (a?.type === 'ParenthesizedExpression') a = a.expression;   // unwrap ( )
  if (a?.type === 'JSXElement') {
    const span = a.loc.end.line - a.loc.start.line;
    if (!best || span > best.span) best = { node: a, span };
  }
});

// 3. each direct child is a section you can extract, with exact bounds
for (const c of best.node.children) {
  if (c.type === 'JSXElement') {
    console.log(`<${c.openingElement.name.name}> ${c.loc.start.line}-${c.loc.end.line}`);
  } else if (c.type === 'JSXExpressionContainer' && c.expression?.type === 'JSXElement') {
    console.log(`{<${c.expression.openingElement.name.name}>} ${c.loc.start.line}-${c.loc.end.line}`);
  }
}
```

Walk **into** the render root's children when the tabs/sections are nested one
level deeper (inside a `<div>` main-stage wrapper). Feed the numbers straight into
the replacement step in the SAME pass; if you must persist them, re-derive them
against the current file before each extraction (see "Verify by re-deriving bounds"
above) rather than trusting an earlier run's line numbers.

## Order of extraction

1. **Pure helpers** (formatters, colour math, linkifiers) — zero deps, trivially
   verifiable.
2. **Self-contained modals** — they take a few props and own their form state.
3. **Tab/section bodies** — larger, but each already carries its own wrapper.
4. **The orchestrator stays.** The parent keeps the state and handlers; it shrinks
   to composition. Do not try to extract the deeply-coupled remainder in the same
   pass — it is a different (harder) job.

Extract in verifiable increments and commit between them. Keep a backup of the
pre-split file so you can diff.

## Components with many dependencies: one props object, not N arguments

A section that closes over 100+ pieces of parent state cannot take 100+
named props sanely. Pass a single object and spread it:

```tsx
// parent
const threeDTabProps = { readOnly, models, zones, setZoneFilter, /* … */ };
<ThreeDTab {...threeDTabProps} />

// child — destructure inside, so the JSX body stays verbatim
export default function ThreeDTab(props: ThreeDTabProps) {
  const { models, zones, setZoneFilter /* … */ } = props;
  return ( /* unchanged JSX */ );
}
```

TypeScript still verifies every key at the call site. Declare the interface with
an index signature (`[k: string]: any`) only as a first pass, then tighten.

## Verifying the split is behaviour-preserving

1. **Parse every extracted file** with the same babel call — catches unbalanced
   JSX before the bundler does.
2. **Check div balance per file**, discounting self-closing `<div ... />`.
3. **Token-compare against the original.** Strip leading indentation and the
   type annotations you added, then compare the token stream:

   ```python
   def toks(s):
       s = re.sub(r":\s*any\b", "", s)                          # added annotations
       s = re.sub(r"\s+as\s+Record<string,\s*string>", "", s)
       s = re.sub(r"\s+as\s+MarkerStatus", "", s)
       return re.sub(r"\s+", " ", s).strip()
   ```

   Equal token counts and no divergence = runtime-identical. A diff that is ONLY
   `: any` / `as X` additions is a pass; anything else is a real change.
4. `npx tsc --noEmit`, then a full production build.
5. Serve the production build locally and grep the emitted chunk for a string
   only the moved code contains — proves the code actually shipped into the
   bundle, not just that it compiled.

## Type errors that always follow a split (and their fixes)

- **`Parameter 'x' implicitly has an 'any' type`** — the loose `any[]` props make
  callback params untyped. Annotate them. Automate it: loop `tsc --noEmit`, read
  the first `TS7006`, annotate that param `: any`, repeat until clean. (`timeout`
  is not on macOS — run the loop in the background instead of wrapping it.)
- **Union setters rejected.** A real setter is `Dispatch<SetStateAction<"a"|"b">>`,
  not `(v: string) => void`. Widen the prop to
  `React.Dispatch<React.SetStateAction<any>>`.
- **`Cannot find name 'X'`** — the body referenced imports the parent had
  (`SeverityBars`, `formatDate`, `CERT_STATUS_COLOR`, a `dynamic()`-loaded
  viewer). Grep the extracted file for every capitalised identifier that is not
  declared locally and add the import.
- **Duplicate identifier** — adding an import the file already had. Remove one.
- **A blanket `replace("FOO[", ...)` mangles a longer name.** Replacing
  `STATUS_COLOR[` also hits `CERT_STATUS_COLOR[`, producing `CERT_(STATUS_COLOR…`.
  Anchor such replaces or re-check the line after.

## Gotchas

- **A file returning JSX must be `.tsx`.** Naming it `.ts` fails the bundler with
  `Expected '>', got 'ident'` at the first JSX tag. Turbopack rejects JSX in `.ts`.
- **De-indent the extracted body by the exact nesting depth** (e.g. 6 or 8
  spaces) so the moved code reads naturally; the token comparison ignores
  indentation, so this is cosmetic and safe.
- **Do not hand-retype moved code.** Script the slice; retyping is where subtle
  edits sneak in.
