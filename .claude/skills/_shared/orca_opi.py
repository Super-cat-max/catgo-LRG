"""Shared OPI (orca-pi) helpers for the ORCA skills.

Lives at .claude/skills/_shared/orca_opi.py. The leading underscore keeps the
directory out of skill discovery (it has no SKILL.md).

Two responsibilities:

1. Define the `%output ... end` block that every skill must inject so ORCA
   writes the JSON files OPI parses (`*.property.json`, `*.json`).
2. Provide `parse_local()` which takes a directory containing files staged
   back from Expanse and returns a typed `opi.output.core.Output` object.

Install: `python -m pip install orca-pi` (Python 3.10+).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opi.output.core import Output


# Inject this into the workflow node's `extra_blocks` so ORCA emits the JSONs
# OPI's Output.parse() consumes. Without it, parsing falls back to grepping
# the .out file (still works, just less rich).
JSON_OUTPUT_TEXT = "%output jsongbwfile True jsonpropfile True end"


# Column order in `Spectrum.excitationenergies` rows for ORCA 6.1.1.
# OPI surfaces the rows but doesn't name the columns — keep the mapping here
# so per-skill UV-Vis code stays agnostic.
UVVIS_COLS = {
    "energy_eV": 0,
    "energy_cm": 1,
    "wavelength_nm": 2,
    "fosc": 3,
    "mu2": 4,
}


def parse_local(work_dir: str | Path, basename: str = "ORCA") -> "Output":
    """Parse a run staged back from Expanse to a local directory.

    Expects at minimum `<basename>.out` in `work_dir`. For full property-tree
    parsing (energies, frequencies, IR, thermo, populations, spectra),
    `<basename>.property.json` must also be present — stage it back via
    `/api/hpc/files/read-content` after the workflow status flips COMPLETED.

    Returns an `opi.output.core.Output` object. Common accessors:
      - out.terminated_normally(), out.scf_converged()
      - out.geometry_optimization_converged()
      - out.get_final_energy(), out.get_structure().to_xyz_block()
      - out.get_ir(), out.get_zpe(), out.get_free_energy()
      - out.get_mulliken(), out.get_homo(), out.get_lumo(), out.get_hl_gap()
      - out.results_properties.geometries[i].absorption_spectrum
    """
    from opi.core import Calculator

    calc = Calculator(
        basename=basename,
        working_dir=Path(work_dir),
        version_check=False,
    )
    out = calc.get_output()
    out.parse()
    return out


def grep_block(
    out_file: str | Path,
    header: str,
    *,
    offset: int = 2,
    count: int = 200,
) -> list[str]:
    """Pull lines from a named block in `<basename>.out`.

    Use for ORCA tables OPI does not model: IRC PATH SUMMARY, NEB
    convergence summary, ABSORPTION SPECTRUM (when raw oscillator-strength
    columns are needed instead of the typed `Spectrum` model).

    `offset` skips the header and ruler; `count` is an upper bound — strip
    blank lines on the consumer side.
    """
    from opi.output.grepper.recipes import get_lines_from_block

    return get_lines_from_block(Path(out_file), header, offset=offset, count=count)


def show_png(path: str | Path, alt: str = "ORCA plot") -> Path:
    """Print a markdown image link so the chat UI surfaces the PNG inline.

    Claude Code renders `![alt](relative/path.png)` as an inline image when
    the path resolves to a real file under the current working directory.
    Call this after `plt.savefig(...)` so the agent can include the link
    in its reply.

    Returns the absolute path so the caller can chain.
    """
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"PNG not found: {p}")
    cwd = Path.cwd().resolve()
    try:
        rel = p.relative_to(cwd).as_posix()
    except ValueError:
        rel = p.as_posix()
    print(f"\n![{alt}]({rel})\n")
    return p


def quick_plot_opt_energy(out, output_png: str | Path = "./local_run/opt_energy.png"):
    """Per-step SCF energy curve for an opt run. Returns the PNG path."""
    import matplotlib.pyplot as plt
    geoms = out.results_properties.geometries
    energies = [g.single_point_data.finalenergy for g in geoms]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(range(len(energies)), energies, color="#2563eb", marker="o", markersize=3)
    ax.set_xlabel("Optimization step")
    ax.set_ylabel("Total energy (Eh)")
    ax.set_title(f"Opt convergence — final {energies[-1]:.6f} Eh")
    fig.tight_layout()
    fig.savefig(output_png, dpi=150)
    plt.close(fig)
    return Path(output_png)


def quick_plot_ir(out, output_png: str | Path = "./local_run/ir_spectrum.png"):
    """IR stick spectrum from out.get_ir(). Returns the PNG path."""
    import matplotlib.pyplot as plt
    ir = out.get_ir()
    waves = [m.wavenumber for m in ir.values()]
    intens = [m.intensity for m in ir.values()]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.vlines(waves, 0, intens, color="#10b981", linewidth=1.5)
    ax.set_xlabel("Wavenumber (cm⁻¹)")
    ax.set_ylabel("IR intensity (km/mol)")
    ax.set_xlim(max(waves) + 100, 0)  # ORCA convention: high to low wavenumber
    ax.set_title(f"IR spectrum — {sum(1 for w in waves if w < 0)} imaginary")
    fig.tight_layout()
    fig.savefig(output_png, dpi=150)
    plt.close(fig)
    return Path(output_png)


def quick_plot_neb_mep(out, output_png: str | Path = "./local_run/neb_mep.png"):
    """Per-image energy curve for an NEB-TS run. Returns the PNG path."""
    import matplotlib.pyplot as plt
    geoms = out.results_properties.geometries
    energies = [g.single_point_data.finalenergy for g in geoms]
    rel_kcal = [(e - energies[0]) * 627.5095 for e in energies]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(range(len(rel_kcal)), rel_kcal, color="#8b5cf6", marker="o", markersize=4)
    ts_idx = max(range(len(rel_kcal)), key=lambda i: rel_kcal[i])
    ax.scatter([ts_idx], [rel_kcal[ts_idx]], color="#ef4444", s=80, zorder=5, label=f"TS ({rel_kcal[ts_idx]:.1f} kcal/mol)")
    ax.set_xlabel("Image")
    ax.set_ylabel("ΔE (kcal/mol)")
    ax.legend(loc="best", frameon=False)
    ax.set_title("NEB-TS minimum energy path")
    fig.tight_layout()
    fig.savefig(output_png, dpi=150)
    plt.close(fig)
    return Path(output_png)


def blocks_to_extra_text(*blocks) -> str:
    """Render typed OPI blocks (BlockTddft, BlockOutput, BlockFreq, ...) as
    `extra_blocks` text suitable for a catgo workflow node param.

    Critical: this returns ONLY the `%...end` blocks, not a full input file.
    The catgo backend already emits the route line, `%pal`, `%maxcore`,
    charge/multiplicity, and geometry from node params — passing a full input
    via `extra_blocks` would duplicate those.

    Also avoid using this for blocks the catgo node already emits from its
    own params: `%irc` is emitted by the `irc` node, `%neb` is emitted by
    the `orca_neb_ts` node. Pasting those again produces a doubled block
    with undefined behavior.

    Safe blocks today: `BlockOutput`, `BlockTddft`, `BlockFreq` (when not
    using a freq-aware node).
    """
    return "\n".join(b.format_orca() for b in blocks)


__all__ = [
    "JSON_OUTPUT_TEXT",
    "UVVIS_COLS",
    "parse_local",
    "grep_block",
    "blocks_to_extra_text",
    "show_png",
    "quick_plot_opt_energy",
    "quick_plot_ir",
    "quick_plot_neb_mep",
]
