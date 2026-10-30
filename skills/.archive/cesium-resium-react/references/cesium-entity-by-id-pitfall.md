# Resium <Entity> by-id "already exists in collection" pitfall

## Symptom
When you render resium `<Entity id={...}>` inside a list (keyed by id) that
refreshes on a poll/interval, Cesium throws:

    Entity with id "X" already exists in this collection.

This happens on the SECOND render of an entity whose id persisted in the feed
between refreshes — the first render added it, the second tries to re-add.

## Root cause
resium's `<Entity>` JSX calls `viewer.entities.add(entity)` under the hood on
every mount/update. Cesium's `entities` collection forbids two entities with
the same `id`. There is no implicit idempotent upsert for JSX entities.

## Fix — manage entities imperatively
Do NOT render resium `<Entity>` in a list that re-renders with the same ids.
Instead sync imperatively via `viewer.entities`:

    useEffect(() => {
      if (!viewer) return
      if (!items.length) {
        viewer.entities.values
          .filter(e => typeof e.id === 'string' && e.id.startsWith('PREFIX-'))
          .forEach(e => viewer.entities.remove(e))
        return
      }
      const seen = new Set()
      for (const it of items) {
        const e = viewer.entities.getOrCreateEntity(it.id) // idempotent, no throw
        e.position = Cartesian3.fromDegrees(it.lon, it.lat)
        e.point = new PointGraphics({ ... })
        e.label = new LabelGraphics({ ... })
        seen.add(it.id)
      }
      // Prune items that dropped out of the feed
      viewer.entities.values
        .filter(e => typeof e.id === 'string' && e.id.startsWith('PREFIX-') && !seen.has(e.id))
        .forEach(e => viewer.entities.remove(e))
    }, [items, selected, viewer])

`getOrCreateEntity(id)` is idempotent — re-running for an existing id just
returns the same entity and updates its graphics. No throw.

## Click-to-inspect HUD
Pick via `viewer.scene.pick(click.position)` inside a `ScreenSpaceEventHandler`
(LEFT_CLICK). Match `picked?.id?.id` against your `PREFIX-` namespace, then
look up from a `ref` of the current list (fresh closure, no re-bind per poll).

## MARU precedent
`src/components/MaritimeEntities.jsx` uses exactly this imperative pattern.
The SituationalEntities layer originally used resium `<Entity>` JSX by id and
inherited the "already exists" risk — convert it to imperative before claiming
a green build.
