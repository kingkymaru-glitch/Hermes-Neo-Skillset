# Generic Identity Text Pattern in React Prototypes

Problem: AppShell and footer embed customer/product names as literal strings.
Fix: Lift identity text into shared state and props.

## Shape
- `AppShell` takes `headerTitle`/`footerBranding` props with neutral defaults.
- `App.tsx` owns state, reads/writes `localStorage`, and wires into `AppShell`.
- Admin surface owns edit UI and restricts it to SuperAdmin.

## Guardrails
- Default to neutral phrases like "Office Task Management".
- Preserve user-specified office/tagline/unit names instead of overriding.
- If the product name has an acronym meaning, default the footer to include that explanation in generic form.
