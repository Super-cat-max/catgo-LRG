# Installation

CatGo is a desktop application. The recommended development setup runs the Svelte frontend and the Python backend together via a single command (`pnpm desktop:serve`). For a production-ready bundle, use the Tauri build path further down this page.

## Prerequisites

- **Node.js** ≥ 20 with [pnpm](https://pnpm.io/)
- **Python** ≥ 3.10 (Conda recommended — gives you a clean environment for the scientific Python stack)
- **Git**

For the full Tauri desktop build (producing `.dmg` / `.msi` / `.AppImage` installers), you'll also need:

- [Rust](https://rustup.rs/) toolchain (stable channel)
- Platform-specific build tooling — see the [Tauri 2.0 prerequisites](https://tauri.app/start/prerequisites/) page for your OS

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Hello-QM/catgo-LRG.git
cd catgo-LRG

# 2. Frontend dependencies
pnpm install

# 3. Python environment
conda create -n catgo python=3.11
conda activate catgo
pip install -r server/requirements.txt

# 4. Launch (frontend on :3100, backend on :8000)
pnpm desktop:serve
```

Open [http://localhost:3100](http://localhost:3100) in your browser. Drop a CIF / POSCAR / XYZ / extxyz / mol2 / pdb / traj file onto the viewer, or ask CatBot something like *"fetch Cu from Materials Project and cut a (100) slab."*

## Development Commands

| Command | What it does |
|---|---|
| `pnpm desktop:serve` | Frontend on :3100 + Python backend on :8000 (recommended for daily development) |
| `pnpm desktop:dev` | Frontend only — useful when the backend is running separately or unneeded |
| `pnpm tauri:dev` | Full Tauri desktop app with hot-reload (requires Rust toolchain) |
| `pnpm check` | Svelte / TypeScript type-check across the codebase |
| `pnpm test` | Vitest unit tests (one-shot); `pnpm vitest` for watch mode |
| `cd server && pytest` | Python backend tests |
| `pnpm docs:dev` | Serve this documentation site locally on :5173 |

## Production Builds

```bash
# Build the Tauri desktop app for your current platform
pnpm tauri:build

# Or target a specific platform explicitly
pnpm tauri:build:mac-arm     # macOS Apple Silicon (.dmg + .app)
pnpm tauri:build:mac         # macOS universal (Intel + Apple Silicon)
pnpm tauri:build:windows     # Windows x64 (.msi + .exe)
pnpm tauri:build:linux       # Linux x64 (.AppImage + .deb)

# Build with the Python backend bundled via PyInstaller (single-file install)
pnpm bundle                  # Current platform
pnpm bundle:mac-arm          # macOS Apple Silicon
pnpm bundle:windows          # Windows x64
```

Built artifacts land in `src-tauri/target/release/bundle/`. The `bundle:*` variants produce a self-contained installer that includes the Python computation server — users don't need to install Python themselves.

## VSCode Extension

```bash
cd extensions/vscode
pnpm install
pnpm build
```

Load the result via *Extensions → Install from VSIX* in VSCode, or run it in the Extension Development Host (press <kbd>F5</kbd> with the `extensions/vscode/` folder open).

## WASM Module (Optional)

The Rust → WASM module (bonding analysis, slab generation, fast geometry operations) ships pre-built at `extensions/rust-wasm/pkg/`. You only need to rebuild from source if you're modifying the Rust code:

```bash
cd extensions/rust

# One-time: install wasm-pack
cargo install wasm-pack

# Build the WASM package
wasm-pack build --target web --out-dir ../rust-wasm/pkg
```

## Running the Backend Alone

If you need only the Python computation server (e.g. headless scripting, CI, or driving CatGo from a Jupyter notebook), bypass the frontend:

```bash
cd server
python main.py
```

The server listens on `http://localhost:8000` with CORS enabled for the frontend.

### Available Calculators

| Calculator | Package | Description |
|---|---|---|
| EMT | ASE (built-in) | Effective medium theory for metals — fast, no setup |
| xTB | tblite + xtb CLI | Semi-empirical tight-binding (GFN2 / GFN1 / GFN0 / GFN-FF) |
| MACE | mace-torch | Machine learning potential, including `mace_mp` foundation models |
| CHGNet | chgnet | Crystal Hamiltonian Graph Network |
| M3GNet | matgl | Materials 3-body Graph Network |

## Troubleshooting

- **`pnpm desktop:serve` says it can't find `python`** — your shell `python` may point to a broken or unrelated interpreter. Either activate the `catgo` conda environment first (`conda activate catgo`), or set the `PYTHON` environment variable to an absolute path like `/opt/anaconda3/bin/python`.
- **`pnpm tauri:dev` fails to compile** — make sure you have the platform-specific build tools for [Tauri 2.0](https://tauri.app/start/prerequisites/) (Xcode Command Line Tools on macOS, the WebView2 runtime on Windows, the standard build essentials on Linux).
- **Frontend loads but viewer is blank** — the WASM module may be missing. Re-run `pnpm install` (the pre-built WASM ships as a workspace link), or rebuild from source as shown above.
