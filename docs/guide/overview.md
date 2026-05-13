# CatGo Documentation

**CatGo** is an **AI-driven workbench for computational materials science**. It combines an interactive 3D structure viewer, a visual DAG workflow engine, integrated HPC orchestration, and a natural-language AI assistant (**CatBot**) into a single desktop application (Tauri) — with an additional VS Code extension for in-editor workflows. The viewer handles crystals, molecules, and surfaces; the workflow engine generates DFT/MD/ML inputs, submits and monitors jobs on remote clusters, and post-processes results through band structure plots, phase diagrams, trajectory players, and more.

## Key Features

- **3D Structure Viewer** — Interactive visualization of crystals, molecules, and surfaces with bonds, lattice, and periodic images
- **Multi-Format I/O** — Parse and export CIF, POSCAR, XYZ, EXTXYZ, HDF5, CUBE, and compressed archives
- **Surface Engineering** — Generate slabs from Miller indices, add vacuum layers, find adsorption sites
- **Symmetry Analysis** — Space group detection, Wyckoff positions via Spglib/Moyo (WASM)
- **Structure Optimization** — Geometry relaxation with EMT, xTB, MACE, CHGNet, M3GNet calculators
- **Spectroscopy** — XRD patterns, radial distribution functions, band structure, density of states
- **Phase Diagrams** — Binary, ternary, and quaternary convex hull stability analysis
- **Trajectory Playback** — MD trajectory animation with streaming support for large files
- **Density Visualization** — CUBE file isosurfaces and 2D slice planes
- **Database Integration** — Search structures from OPTIMADE, Materials Project, and PubChem
- **Cross-Platform** — Web app, Tauri desktop app, VSCode extension, Jupyter widget

## Architecture Overview

```
CatGo
├── src/lib/                  # Svelte 5 component library (88 components)
│   ├── structure/            # 3D structure viewer (largest module)
│   ├── bands/                # Band structure & DOS plots
│   ├── brillouin/            # Brillouin zone visualization
│   ├── composition/          # Composition charts
│   ├── coordination/         # Coordination analysis
│   ├── cube/                 # CUBE file density viewer
│   ├── element/              # Element database (118 elements)
│   ├── periodic-table/       # Interactive periodic table
│   ├── phase-diagram/        # Phase diagram components
│   ├── plot/                 # General plotting (scatter, bar, histogram)
│   ├── rdf/                  # Radial distribution function
│   ├── trajectory/           # MD trajectory player
│   ├── xrd/                  # X-ray diffraction patterns
│   ├── api/                  # API clients (OPTIMADE, MP, PubChem)
│   └── settings.ts           # Unified settings schema
├── extensions/rust/          # Rust library compiled to WASM
│   └── src/wasm.rs           # 65+ WASM-exposed functions
├── server/                   # Python FastAPI computation backend
│   └── routers/              # Optimization, database, spectroscopy routes
├── src-tauri/                # Tauri desktop app shell
└── extensions/vscode/        # VSCode extension
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| UI Components | Svelte 5 (runes: `$state`, `$derived`, `$effect`) |
| Framework | SvelteKit with static adapter |
| 3D Rendering | Three.js via Threlte |
| 2D Plots | D3.js |
| Heavy Computation | Rust compiled to WebAssembly (ferrox-wasm) |
| Symmetry | Spglib / Moyo (WASM) |
| HDF5 Files | h5wasm |
| Desktop App | Tauri 2.0 |
| Computation Server | Python FastAPI + ASE |
| Type Safety | TypeScript (strict mode) |

## Modules

### Core

| Module | Description |
|--------|-------------|
| [Structure Viewer](/modules/core/structure-viewer) | 3D interactive visualization of atoms, bonds, and lattices |
| [File I/O](/modules/core/file-io) | Parse and export crystal/molecular structure files |
| [Lattice & Cell](/modules/core/lattice-cell) | Lattice parameters, coordinate transforms, cell operations |
| [Bonding](/modules/core/bonding) | Bond detection, editing, and coordination analysis |

### Crystallography

| Module | Description |
|--------|-------------|
| [Surfaces & Slabs](/modules/crystallography/surfaces-slabs) | Miller index slab generation, vacuum layers, adsorption sites |
| [Symmetry](/modules/crystallography/symmetry) | Space group detection, Wyckoff positions, Bravais lattices |
| [Supercells](/modules/crystallography/supercells) | Periodic cell expansion and transformation |

### Dynamics & Optimization

| Module | Description |
|--------|-------------|
| [Trajectories](/modules/dynamics/trajectories) | MD trajectory playback, frame indexing, streaming |
| [Optimization](/modules/dynamics/optimization) | Structure relaxation with multiple calculators |

### Analysis & Spectroscopy

| Module | Description |
|--------|-------------|
| [Spectroscopy](/modules/analysis/spectroscopy) | XRD, RDF, band structure, density of states |
| [Phase Diagrams](/modules/analysis/phase-diagrams) | Thermodynamic stability and convex hulls |
| [Composition](/modules/analysis/composition) | Chemical formula handling and composition charts |
| [Periodic Table](/modules/analysis/periodic-table) | Interactive element explorer with property data |

### Integrations

| Module | Description |
|--------|-------------|
| [Density Visualization](/modules/integrations/density-visualization) | CUBE file isosurfaces and slice planes |
| [Database Integration](/modules/integrations/database-integration) | OPTIMADE, Materials Project, PubChem search |
| [Settings](/modules/core/settings) | 40+ configurable properties across platforms |

## Deployment Targets

| Target | Description |
|--------|-------------|
| **Web App** | SvelteKit static site — runs in any modern browser |
| **Desktop App** | Tauri 2.0 — native app for macOS, Windows, Linux with file system access |
| **VSCode Extension** | Embedded viewer inside the text editor |
| **Jupyter / Marimo** | Widget for computational notebooks |

## Tutorials

Step-by-step guides for common workflows:

| Tutorial | Description |
|----------|-------------|
| [Getting Started](/tutorials/basics/getting-started) | Load, explore, and export your first structure |
| [Building Slabs](/tutorials/structures/building-slabs) | Generate surface slabs from Miller indices |
| [Structure Optimization](/tutorials/structures/optimization) | Relax structures with UFF, xTB, MACE, and more |
| [Database Search](/tutorials/structures/database-search) | Find structures from OPTIMADE, Materials Project, PubChem |
| [Trajectory Playback](/tutorials/visualization/trajectories) | Load and analyze MD trajectories |
| [Density Visualization](/tutorials/visualization/density-viz) | CUBE file isosurfaces and slice planes |

## Quick Links

- [Installation](/guide/installation)
- [Tutorials](/tutorials/basics/getting-started)
- [Gallery](/guide/gallery)
- [Tips and Tricks](/guide/tips-and-tricks)
- [FAQ](/reference/faq)
- [Changelog](/reference/changelog)
- [Contributing](/developer/contributing)
- [Development Guide](/developer/development-guide)
- [Desktop Build Guide](/developer/desktop-build)
- [GitHub Repository](https://github.com/Hello-QM/catgo-LRG)
