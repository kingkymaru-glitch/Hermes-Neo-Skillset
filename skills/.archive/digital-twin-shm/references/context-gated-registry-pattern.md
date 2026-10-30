# Troubleshooting: context-gated registries / module-time ReferenceError

## Symptom
`ReferenceError: SOME_CTX_URL is not defined` at line N inside a `registry = [...]` constant declaration in a component file that consumes `useEdgeData()`.

## Cause
The registry is built at module load, before React mounts and before `EdgeDataContext` provides values. So `SOME_CTX_URL` is `undefined` because `import.meta.env` + provider wiring hasn’t populated the destructured name yet.

## Fix pattern
Replace top-level constant registry with:
- builder function `buildDefaultDevices(stateUrl)` returning the array
- `const devicesRef = useRef(buildDefaultDevices(SHIFU_STATE_URL))`
- sync ref in `useEffect(..., [SHIFU_STATE_URL])`
- replace all read-site usages with `devicesRef.current[...]`

## Verification
- search: `SHIFU_REGISTRY`, `SHIFU_DEVICES`, or old constant name; should be zero hits
- `npm run lint`, `npm run build`: exit 0
- dev: run app, confirm console no longer has module-time ReferenceError
