# Scroll-spy attribute placement (Pitfall 15)

## Symptom
A floating section nav (up/down buttons + `n/N` counter) reads `1/5`, never advances,
and the ↓ button "does nothing" — even though the page scrolls fine manually. Build
green, no console error.

## Why
The IntersectionObserver watches the inner section (`.labs-project`) but the
attribute it reads (`data-idx`) and the scroll-target `id` sit on a WRAPPER `<div>`:
```jsx
{items.map((p,i) => (
  <div data-idx={i} id={`labs-proj-${i}`}>     {/* attribute + anchor on WRAPPER */}
    <section className="labs-project">…</section>  {/* observer watches THIS */}
  </div>
))}
```
Observer: `root.querySelectorAll('.labs-project')` → reads `e.target.getAttribute('data-idx')`
from the section → null. So `active` stays 0 → counter stuck, `setActive` never fires.

## Fix
Put `data-idx` AND `id` on the SAME element the observer selects — remove the wrapper:
```jsx
{items.map((p,i) => (
  <section className="labs-project" id={`labs-proj-${i}`} data-idx={i}>…</section>
))}
```
Now `e.target` IS the section, `data-idx` reads correctly, counter advances,
`scrollIntoView` targets the right node.

## Verify at runtime (build can't catch it)
After a click/scroll, read via browser console:
```js
document.querySelector('.labs-nav-count').textContent  // expect "2/5" after one ↓
document.querySelector('.labs-main').scrollTop         // expect > 0
```
Counter advancing + non-zero scrollTop = working. Counter stuck at `1/N` = attribute
on the wrong element.
