# Kiri Engine — dual-asset strategy (learned 2026-08-14)

Ref: https://www.kiriengine.app + github.com/Kiri-Innovation/3dgs-render-blender-addon

## What Kiri does
Capture → reconstruct → 3DGS native (.ply, needs a viewer/plugin) OR
3DGS-to-Mesh → standard OBJ/FBX/GLB/GLTF/USDZ (no plugin). The EDIT step
(crop/color/relight) is where value is added before export.

## Applied to DTwin
Two delivery formats from one trained splat:
- **Web**: the .ply splat via three.js gaussian-splat renderer — richest look,
  but needs the splat viewer. Source of truth for "the hologram".
- **Unity AR**: baked **.glb mesh** from the splat — ARKit/ARCore-native,
  lighter, no splat plugin in the AR app. The AR-friendly fallback.

Both come from the same COLMAP+SfM→3DGS step; plan for both outputs up front
so web and AR stay in sync. SuperSplat handles the crop/clean edit for either.

## Format note
Native 3DGS .ply is NOT a normal point cloud — it carries extra splat
attributes (f_dc, opacity, scale, rot). Three.js gaussian-splat viewer,
SuperSplat, Kiri's Blender addon, and Unity's GaussianSplatting package all
read this format.
