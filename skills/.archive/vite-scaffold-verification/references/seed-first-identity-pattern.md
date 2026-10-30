# Seed-First Identity Pattern

## Why
Fast prototypes often start with fake “Super Admin / Role / Member” account buttons or hardcoded login payloads. That feels expedient, but it makes later feature work much harder.

## The trap
As soon as the app grows:
- task filtering by owner (`mine`, owner dropdown)
- task delegation / reassignment
- org-chart relationships / `reportsTo` linkage
- per-position analytics and plan-vs-actual breakdowns

…those systems need stable, trustworthy user IDs. If the login step invented ephemeral users with mutable or human-facing identifiers, you end up rewiring every downstream lookup when you switch to seeded data.

## Fix
If the mock/data layer already defines identities, make login a picker over that source of truth.

## Minimal implementation
```ts
const seed = useMemo(() => mockData(), []);
const [selectedId, setSelectedId] = useState(seed.users[0]?.id || '');

const submit = async (e) => {
  e.preventDefault();
  await new Promise(r => setTimeout(r, 400));
  const user = seed.users.find(u => u.id === selectedId) || seed.users[0];
  onLogin(user);
};
```

## Consequences
- `assignedTo` can be a user ID immediately.
- `currentUser.id` works for “mine” without a second mapping layer later.
- Org chart editing can call `upsertUser` and the result keeps existing relationships.
- Real auth migration becomes a drop-in replacement for `onLogin`, not a full rework.

## Workspace evidence
In the RIINA prototype (`~/riina`), login was changed from hand-built placeholder users to `demoUsers`-style pickers over `mockData()` users. Follow-on work then aligned `MyTasks`, task detail, and org chart wiring to real user IDs instead of human names, removing a hidden blocker for per-position analytics.
