---
name: hardware-robotics-design
description: "Design hardware in code: CAD, PCB, URDF, FEA all FOSS."
---

# Autonomous Hardware & Robotics Design Engineer

## Trigger

When the user asks to design, model, or fabricate mechanical parts, PCB boards, robotic assemblies, or complete hardware systems -- and wants the output as executable Python scripts producing STEP/STL/Gerber/URDF files, NOT manual CAD/EDA GUI steps.

## Core Stack (100% FOSS, 100% code-driven)

| Domain | Engine | Outputs |
|--------|--------|---------|
| **Mechanical CAD** | `FreeCAD` (headless, primary — installed) | `.STEP`, `.STL`, `.FCStd` |
| **CAD (alt)** | `build123d` / `CadQuery` (pip-installable fallback) | `.STEP`, `.STL`, `.3MF` |
| **Kinematics** | `Pinocchio`, `ikpy` | `.urdf` with CoM + inertia |
| **PCB/Schematic** | `SKiDL` (netlist), `pcbnew` (layout), `Freerouting CLI` (autoroute) | Gerber ZIP, BOM CSV, PnP |
| **Simulation** | `PySpice` (circuits), FreeCAD FEM (structural) | SPICE plots, stress reports |
| **Mesh utils** | `trimesh`, FreeCAD `Mesh` module | mass properties, collision volumes |

## FreeCAD Setup (installed on this Mac)

- **App:** `/Applications/FreeCAD.app` — FreeCAD 1.0.0 (Python 3.11.10)
- **Headless execution:** `/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd`
- **Usage:** write a `.py` script, run with `freecadcmd script.py`
- **All modules available:** Part (B-Rep solids), Sketcher (constrained 2D), Mesh (STL), Draft, FEM (structural FEA), Path/CAM, TechDraw

### FreeCAD scripting cheat sheet

```python
import FreeCAD
import Part
import Mesh
from FreeCAD import Vector

# Create parametric box
box = Part.makeBox(10, 20, 30, Vector(0, 0, 0))

# Boolean operations
cyl = Part.makeCylinder(5, 50, Vector(15, 10, -5))
cut = box.cut(cyl)

# Export
cut.exportStep("/tmp/part.step")
Mesh.export([cut], "/tmp/part.stl")

# Load/save FreeCAD project
doc = FreeCAD.newDocument("Design")
doc.addObject("Part::Feature", "MyPart").Shape = cut
doc.saveAs("/tmp/design.FCStd")
```

### FreeCAD from external Python (limited)

```python
import sys
sys.path.append('/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD, Part, Mesh  # core modules work
# Draft, FEM need PySide2 (FreeCAD-bundled) -- use freecadcmd for those
```

## Phase Execution Order

### Phase 1: Math & Concept
- Parse payload, DOF, voltage, dimensions constraints
- Calculate torque, joint velocity, structural loads, power budget via `numpy`/`scipy`
- Produce a short markdown spec before any code

### Phase 2: Electronics (Code-to-PCB)
1. Write `SKiDL` Python script -- ICs, passives, regulators, motor drivers
2. Run SKiDL ERC (electrical rules check)
3. `pcbnew` -- board edge, mounting holes, footprint placement
4. Export `.dsn` -> `Freerouting CLI` -> import `.ses`
5. `kicad-cli` / `KiBot` -> Gerbers, BOM CSV, PnP

### Phase 3: Mechanical (Code-to-CAD)
1. Write FreeCAD Python script -- chassis, brackets, enclosures, linkages
2. Use Part workbench for B-Rep solids, Sketcher for constrained profiles
3. Align mount holes with PCB layout from Phase 2
4. Run via `freecadcmd script.py`
5. Export `.STEP` + `.STL`

### Phase 4: Assembly & URDF
1. Calculate mass properties via `trimesh` or FreeCAD's `Shape.Volume`/`Shape.CenterOfMass`
2. Generate `.urdf` with joints (revolute, continuous, fixed)
3. Auto-calculate CoM and inertia from geometry

### Phase 5: Deliverables
- All Python source scripts
- Manufacturing artifacts (STEP, STL, URDF, Gerber, BOM, FCStd)
- Verification report (FEA stress limits, PCB power, mass budget)

## Code Standards

- **Parametric constants at top:** `MOTOR_SHAFT_DIAMETER = 5.0`, `WALL_THICKNESS = 2.0`, etc.
- **No GUI dependencies** -- no SolidWorks, Fusion360, Altium instructions
- **Graceful error recovery** -- catch OpenCascade boolean failures, adjust offsets, retry
- **All units in mm** unless otherwise stated
- **Write scripts as standalone `.py` files** -- execute with `freecadcmd` for production, or import FreeCAD modules for quick tests

## Installation (macOS)

FreeCAD is already installed. Additional tools if needed:

```bash
# Alternative CAD libraries
pip install build123d cadquery trimesh

# Kinematics
pip install pinocchio yourdfpy  # or ikpy

# PCB
pip install skidl
# KiCad + Freerouting installed via Homebrew or .app

# Simulation
pip install pyspice pycalculix sfepy
```

## Pitfalls

- FreeCAD's Python API requires `freecadcmd` for full module access (Draft, FEM, Path need PySide2)
- Core modules (Part, Mesh, Sketcher) work from external Python with sys.path addition
- OpenCascade boolean ops can fail on coincident faces; add 0.01mm clearance
- `Freerouting CLI` needs Java runtime
- `Pinocchio` wheel availability varies by platform; `conda` install is most reliable on macOS
- KiCad Python API (`pcbnew`) requires KiCad.app installed; import from its bundled Python
- FreeCAD `.FCStd` files are ZIP archives containing BREP XML -- fully scriptable, no GUI needed