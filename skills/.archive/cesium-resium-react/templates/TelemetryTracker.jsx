// TelemetryTracker.jsx — drop inside <Viewer> to bridge Cesium -> React state.
// Lives in the Viewer tree so useCesium() returns the live engine the instant
// it mounts. Eliminates rAF polling and the stale-closure race on camera reads,
// and exposes the engine via viewerRef so buttons OUTSIDE <Viewer> (Locate Me,
// etc.) can call camera.flyTo.
//
// useCesium is a PUBLIC resium export (resium/dist/index.d.ts -> `export * from
// './core'`, where core defines useCesium). It yields { viewer, scene, camera,
// globe }. NOTE: resium 1.24 <Viewer> has NO onReady prop — useCesium inside a
// child is the correct substitute.
//
// G13 (CRITICAL): on the FIRST render, before <Viewer> injects context,
// useCesium() returns an EMPTY OBJECT {}, so `const { viewer } = useCesium()`
// yields `viewer = undefined` and any viewer.camera access throws
// "Cannot read properties of undefined (reading 'scene')". Read through an
// optional chain (cesiumContext?.viewer) and bail until the genuine engine is
// present. This template MUST keep the `?.` form — do not revert to a bare
// destructure.
import { useEffect, useRef } from 'react'
import { useCesium } from 'resium'

export default function TelemetryTracker({ viewerRef, setCamPos }) {
  // Resium's context can yield {} on first render; read through optional chain.
  const cesiumContext = useCesium()
  const viewer = cesiumContext?.viewer // undefined on first render -> safe

  const last = useRef({ lat: '', long: '' })

  useEffect(() => {
    // Genuine engine present? isDestroyed() exists only on a real Cesium.Viewer.
    if (!viewer || typeof viewer.isDestroyed !== 'function' || viewer.isDestroyed()) return

    // Share this genuine viewer instance with the parent ref for the Locate Me button.
    if (viewerRef) viewerRef.current = viewer

    const read = () => {
      // Camera read: postRender every frame (live during drag) + camera.moveEnd
      // for one accurate final read on settle. Events on Camera, postRender on Scene.
      const carto = viewer.camera.positionCartographic
      if (!carto) return
      const lat = (carto.latitude * 180 / Math.PI).toFixed(4)
      const long = (carto.longitude * 180 / Math.PI).toFixed(4)
      if (last.current.lat === lat && last.current.long === long) return
      last.current = { lat, long }
      setCamPos({ lat, long })
    }

    const onRender = () => read()
    const onMoveEnd = () => read()
    viewer.scene.postRender.addEventListener(onRender)
    viewer.camera.moveEnd.addEventListener(onMoveEnd)
    read()

    return () => {
      viewer.scene.postRender.removeEventListener(onRender)
      viewer.camera.moveEnd.removeEventListener(onMoveEnd)
    }
  }, [viewer, viewerRef, setCamPos])

  return null
}
