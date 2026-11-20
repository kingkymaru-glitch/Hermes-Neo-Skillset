# RINA activityType feature chunk — resume pattern

This note captures the exact resume/continue behavior seen when cleanup was done
in `src/types.ts` and the queued feature remained unfinished.

## Context
- Project: `/Users/kamarulhk/riina`
- Workstream: Option A small UI feature chunk / activityType fields.
- Queued items: t4a model+form → t4b badges in MyTasks → t4c Analytics breakdown → t4d verify.

## Lesson
After cleaning up the broken type model, continue straight into the queued frontend
implementation instead of asking the user to choose next. The task order already
encodes the intent; the job is to take the smallest obvious chunk and advance it.

Preferred continuation order:
1. Add `activityType` control to `TaskCreate.tsx`.
2. Display activity badges in `MyTasks.tsx`.
3. Add activity breakdown to `Analytics.tsx`.
4. Final lint/build/UI-check pass.

## Why this matters
Re-summarizing the queue and asking "A or B?" slows work and burns tokens,
especially when the user prefers atomic forward moves and the next step is already
obvious from the ticket order.
