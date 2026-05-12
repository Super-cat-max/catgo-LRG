# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-05-12

### Added
- **Static Web Deployment**: Full support for Cloudflare Pages (frontend-only mode).
- **Static Mode Banner**: Informational UI component for features requiring the desktop app.
- **SPA Routing**: Automatic `_redirects` generation for Cloudflare Pages.
- **Workflow Engine**: DAG-based visual editor for complex calculation pipelines.
- **CatBot AI Assistant**: Natural language structure operations and workflow authoring.
- **HPC Integration**: SSH terminal, remote file browser, and job monitoring.
- **Built-in Calculators**: xTB and EMT bundled in the desktop application.
- **Database Browser**: OPTIMADE and PubChem integration.

### Changed
- Migrated all repository links to `Hello-QM/catgo-LRG`.
- Unified structure saving and exporting across project, HPC, and local file system.
- Improved coordination polyhedra rendering and performance.
- Enhanced MD trajectory playback with per-frame bond caching.

### Fixed
- Fixed oxidation state serialization issues in ASE exports.
- Resolved CORS issues for OPTIMADE providers in static mode.
- Fixed compressed file loading in the desktop sidebar.
- Corrected various accessibility and linting issues.

## [0.3.0] - 2026-03-02
- Initial private beta release.
- 3D structure viewer with basic editing.
- VASP input generation.
- Basic HPC connectivity.
