# Escape-drift real example (RINA AdminPanel.tsx)

## Failing call
Goal: change the empty-users row `colSpan` from 5 to 6 after adding a new
"Job Description" table column. The row line was:

```
<tr><td colSpan={5} className="px-3 py-6 text-center text-[rgba(30,18,48,0.55)]\">No users yet. Add the first team member above.</td></tr>
```

Patch attempt (FAILED):
```
old: <tr><td colSpan={5} className="px-3 py-6 text-center text-[rgba(30,18,48,0.55)]\">No users yet. Add the first team member above.</td></tr>
new: <tr><td colSpan={6} className="px-3 py-6 text-center text-[rgba(30,18,48,0.55)]\">No users yet. Add the first team member above.</td></tr>
```
Error: `Escape-drift detected: old_string and new_string contain the literal
sequence '\\"' but the matched region of the file does not. ...`

Root cause: the `">` at the end of the `text-[rgba(30,18,48,0.55)]\"` token was
serialized as `\"`, so the tool saw a quote that doesn't exist in the file.

## Working fix
Patch only the unique ASCII anchor inside the line:
```
old: colSpan={5}
new: colSpan={6}
```
Applied cleanly. (The long className string was left untouched.)

## Same session, same class of bug
- The locked-state message edit worked as a plain ASCII substring:
  `Only Super Admin or Department Head can manage users.` ->
  `Only the Super Admin can manage users and job descriptions.`
- A `<th>` insertion worked when the surrounding context lines did NOT end in
  `">` (inserted the Job Description header before the empty `<th></th>`).
- A second batch patch in the same turn that repeated an identical add-user
  block returned "Duplicate tool output — same content as a more recent call",
  confirming an earlier call had already applied it.

## Takeaway
Whenever a patch fails with "Escape-drift detected" on JSX/TSX/HTML, the
trigger is a `">` terminator in your old/new string. Drop the long class string
and patch the minimal unique ASCII anchor instead.
