"""Result extraction from completed HPC jobs.

Reads output structures, energies, frequencies, and engine-specific results
from HPC work directories after job completion.
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _extract_xyz_from_orca_output(output_text: str, node_type: str) -> str | None:
    """Extract the last optimized XYZ geometry from ORCA.out.

    ORCA writes coordinates in blocks starting with:
        CARTESIAN COORDINATES (ANGSTROEM)
        ---------------------------------
        C      0.000000    0.000000    0.000000
        ...

    For opt/neb_ts: extracts the LAST such block (final optimized geometry).
    For sp/freq/irc/uvvis: extracts the first (input geometry echoed back).
    Returns an XYZ-format string, or None if not found.
    """
    marker = "CARTESIAN COORDINATES (ANGSTROEM)"
    positions = []
    start = 0
    while True:
        idx = output_text.find(marker, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + len(marker)

    if not positions:
        return None

    # For optimization types, take the last block; otherwise first
    if node_type in ("orca_opt", "orca_neb_ts"):
        block_start = positions[-1]
    else:
        block_start = positions[-1]  # last is safest for all types

    # Skip marker line and the dashes line
    lines = output_text[block_start:].split("\n")
    atoms = []
    for line in lines[2:]:  # skip marker + dashes
        stripped = line.strip()
        if not stripped:
            break
        parts = stripped.split()
        if len(parts) >= 4:
            try:
                float(parts[1])
                float(parts[2])
                float(parts[3])
                atoms.append(f"{parts[0]:>2s}  {parts[1]:>14s}  {parts[2]:>14s}  {parts[3]:>14s}")
            except ValueError:
                break
        else:
            break

    if not atoms:
        return None

    n = len(atoms)
    xyz_lines = [str(n), f"ORCA {node_type} output geometry"]
    xyz_lines.extend(atoms)
    return "\n".join(xyz_lines) + "\n"


async def _try_read_output_structure(
    hpc: Any,
    work_dir: str,
    node_type: str,
) -> Optional[str]:
    """Try to read output structure from HPC for downstream nodes.

    For VASP: reads CONTCAR. For other engines: reads appropriate output.
    """
    from workflow.node_sets import get_engine_for_node

    engine_key = get_engine_for_node(node_type)

    # VASP: read CONTCAR
    if engine_key == "vasp":
        try:
            result = await hpc.run_on_owner(lambda: hpc.conn.run(f"cat {work_dir}/CONTCAR", check=False))
            if result.exit_status == 0 and result.stdout and len(result.stdout.strip()) > 10:
                return result.stdout
        except Exception:
            logger.debug("Failed to read CONTCAR from %s", work_dir, exc_info=True)

    # CP2K: read output structure
    if engine_key == "cp2k":
        try:
            result = await hpc.run_on_owner(lambda: hpc.conn.run(
                f"ls -t {work_dir}/*-pos-*.xyz 2>/dev/null | head -1",
                check=False,
            ))
            if result.exit_status == 0 and result.stdout.strip():
                xyz_file = result.stdout.strip()
                result2 = await hpc.run_on_owner(lambda: hpc.conn.run(f"cat {xyz_file}", check=False))
                if result2.exit_status == 0:
                    return result2.stdout
        except Exception:
            logger.debug("Failed to read CP2K output structure from %s", work_dir, exc_info=True)

    # Sella: read structure.xyz (preferred) or CONTCAR
    if engine_key == "sella":
        for fname in ("structure.xyz", "CONTCAR"):
            try:
                result = await hpc.run_on_owner(lambda fname=fname: hpc.conn.run(f"cat {work_dir}/{fname}", check=False))
                if result.exit_status == 0 and result.stdout and len(result.stdout.strip()) > 5:
                    logger.info("Read Sella output structure from %s/%s", work_dir, fname)
                    return result.stdout
            except Exception:
                continue
        logger.debug("No Sella output structure found in %s", work_dir)

    # ORCA standalone nodes
    if engine_key == "orca":
        # NEB-TS: read the dedicated converged TS XYZ file (small, authoritative)
        # rather than parsing the last coordinate block from the ~5MB ORCA.out
        if node_type in ("orca_neb_ts", "ts_search"):
            for suffix in ("_NEB-TS_converged.xyz", "_NEB-CI_converged.xyz"):
                try:
                    ts_file = f"{work_dir}/ORCA{suffix}"
                    result = await hpc.run_on_owner(lambda ts_file=ts_file: hpc.conn.run(f"cat {ts_file}", check=False))
                    if result.exit_status == 0 and result.stdout and len(result.stdout.strip()) > 5:
                        logger.info("Read NEB-TS converged structure from %s", ts_file)
                        return result.stdout
                except Exception:
                    continue

        # Fallback: extract optimized geometry from ORCA.out
        # (handles orca_opt, orca_sp, orca_freq, etc. and NEB-TS when converged files missing)
        try:
            result = await hpc.run_on_owner(lambda: hpc.conn.run(f"cat {work_dir}/ORCA.out", check=False))
            if result.exit_status == 0 and result.stdout:
                xyz_str = _extract_xyz_from_orca_output(result.stdout, node_type)
                if xyz_str:
                    return xyz_str
        except Exception:
            logger.debug("Failed to extract ORCA output structure from %s", work_dir, exc_info=True)

    # MLP (MACE/CHGNet/M3GNet): read CONTCAR
    if engine_key == "mlp":
        try:
            result = await hpc.run_on_owner(lambda: hpc.conn.run(f"cat {work_dir}/CONTCAR", check=False))
            if result.exit_status == 0 and result.stdout and len(result.stdout.strip()) > 10:
                return result.stdout
        except Exception:
            logger.debug("Failed to read MLP CONTCAR from %s", work_dir, exc_info=True)

    return None


async def _try_read_sella_results(
    hpc: Any,
    work_dir: str,
) -> dict:
    """Read Sella-specific results: energy, convergence, forces from stdout/log.

    Returns a dict with keys: energy, converged, max_force, n_steps.
    """
    results: dict = {}

    # Try reading ts.log for step count
    try:
        result = await hpc.run_on_owner(lambda: hpc.conn.run(f"wc -l {work_dir}/ts.log 2>/dev/null", check=False))
        if result.exit_status == 0 and result.stdout.strip():
            n_lines = int(result.stdout.strip().split()[0])
            results["n_steps"] = max(0, n_lines - 1)  # subtract header line
    except Exception:
        pass

    # Try reading stdout for energy and convergence (from SLURM output or direct run)
    try:
        # Check for SLURM output first, then stdout capture
        result = await hpc.run_on_owner(lambda: hpc.conn.run(
            f"grep -h 'Final energy\\|Max force\\|Converged' {work_dir}/*.out {work_dir}/*.log 2>/dev/null | tail -5",
            check=False,
        ))
        if result.exit_status == 0 and result.stdout:
            for line in result.stdout.splitlines():
                if "Final energy:" in line:
                    try:
                        results["energy"] = float(line.split(":")[-1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass
                elif "Max force:" in line:
                    try:
                        results["max_force"] = float(line.split(":")[-1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass
                elif "Converged:" in line:
                    results["converged"] = "True" in line
    except Exception:
        logger.debug("Failed to parse Sella results from %s", work_dir, exc_info=True)

    return results


async def collect_completed_results(
    hpc, work_dir: str, node_id: str, node_type: str, params: dict,
    session_id: str, job_id: str,
) -> dict:
    """Build the result dict for a completed HPC job.

    Reads output files (CONTCAR, OUTCAR energy, CP2K energy, MLP energy,
    VASP frequencies, Sella results) and returns a dict suitable for
    ``step_results[node_id]``.

    This is a pure extraction helper -- it does **not** modify any external
    state.  Callers are responsible for storing the returned dict.
    """
    from workflow.node_sets import get_engine_for_node

    engine_key = get_engine_for_node(node_type)

    result: dict = {
        "status": "completed",
        "work_dir": work_dir,
        "job_id": job_id,
        "session_id": session_id,
        "node_type": node_type,
    }

    # Propagate system_name for downstream gibbs_energy / free_energy nodes
    if params.get("system_name"):
        result["system_name"] = params["system_name"]

    # Try to read CONTCAR/output structure for downstream nodes
    output_structure = await _try_read_output_structure(
        hpc, work_dir, node_type,
    )
    if output_structure:
        result["structure"] = output_structure

    # Extract Sella-specific results (energy, convergence, forces)
    if engine_key == "sella":
        try:
            sella_results = await _try_read_sella_results(hpc, work_dir)
            if sella_results:
                result.update(sella_results)
                logger.info("Sella results for %s: %s", node_id, sella_results)
        except Exception as exc:
            logger.warning("Failed to read Sella results for %s: %s", node_id, exc)

    # Extract MLP results (energy from stdout)
    if engine_key == "mlp":
        try:
            # Read the SLURM stdout file for "Final energy: X eV"
            grep_result = await hpc.run_on_owner(lambda: hpc.conn.run(
                f"cat {work_dir}/*.out 2>/dev/null || cat {work_dir}/slurm-*.out 2>/dev/null",
                check=False,
            ))
            if grep_result.exit_status == 0 and grep_result.stdout:
                for line in grep_result.stdout.splitlines():
                    if "Final energy:" in line:
                        try:
                            energy = float(line.split("Final energy:")[1].strip().split()[0])
                            result["energy"] = energy
                            logger.info("MLP energy for %s: %.6f eV", node_id, energy)
                        except (ValueError, IndexError):
                            pass
        except Exception as exc:
            logger.warning("Failed to read MLP energy for %s: %s", node_id, exc)

    # Extract VASP final energy from OUTCAR for downstream nodes (gibbs_energy etc.)
    if engine_key == "vasp" and "energy" not in result:
        try:
            grep_result = await hpc.run_on_owner(lambda: hpc.conn.run(
                f"grep 'free  energy   TOTEN' {work_dir}/OUTCAR | tail -1",
                check=False,
            ))
            if grep_result.exit_status == 0 and grep_result.stdout.strip():
                # Format: "  free  energy   TOTEN  =      -123.45678901 eV"
                energy_str = grep_result.stdout.strip().split("=")[-1].strip().split()[0]
                energy = float(energy_str)
                result["energy"] = energy
                logger.info("VASP energy for %s: %.6f eV", node_id, energy)
        except Exception as exc:
            logger.warning("Failed to extract VASP energy for %s: %s", node_id, exc)

    # Extract CP2K final energy for downstream nodes
    if engine_key == "cp2k" and "energy" not in result:
        try:
            grep_result = await hpc.run_on_owner(lambda: hpc.conn.run(
                f"grep 'ENERGY| Total' {work_dir}/cp2k.out | tail -1",
                check=False,
            ))
            if grep_result.exit_status == 0 and grep_result.stdout.strip():
                # Format: " ENERGY| Total FORCE_EVAL ( QS ) energy [a.u.]:          -123.456789"
                energy_ha = float(grep_result.stdout.strip().split()[-1])
                energy_ev = energy_ha * 27.211386245988  # Hartree to eV
                result["energy"] = energy_ev
                logger.info("CP2K energy for %s: %.6f eV (%.6f Ha)", node_id, energy_ev, energy_ha)
        except Exception as exc:
            logger.warning("Failed to extract CP2K energy for %s: %s", node_id, exc)

    # Record ORCA .gbw wavefunction path for downstream nodes (restart speedup)
    if engine_key == "orca":
        gbw_path = f"{work_dir}/ORCA.gbw"
        try:
            check = await hpc.run_on_owner(lambda: hpc.conn.run(f"test -f {gbw_path} && echo exists", check=False))
            if check.exit_status == 0 and "exists" in (check.stdout or ""):
                result["wavefunction_file"] = gbw_path
                logger.info("ORCA .gbw found for %s: %s", node_id, gbw_path)
        except Exception:
            logger.debug("Failed to check for ORCA .gbw at %s", gbw_path, exc_info=True)

    # Extract ORCA final energy from ORCA.out for downstream nodes
    if engine_key == "orca" and "energy" not in result:
        try:
            grep_result = await hpc.run_on_owner(lambda: hpc.conn.run(
                f"grep 'FINAL SINGLE POINT ENERGY' {work_dir}/ORCA.out | tail -1",
                check=False,
            ))
            if grep_result.exit_status == 0 and grep_result.stdout.strip():
                # Format: "FINAL SINGLE POINT ENERGY      -123.456789012345"
                energy_ha = float(grep_result.stdout.strip().split()[-1])
                energy_ev = energy_ha * 27.211386245988  # Hartree to eV
                result["energy"] = energy_ev
                result["energy_eh"] = energy_ha
                logger.info("ORCA energy for %s: %.6f eV (%.10f Eh)", node_id, energy_ev, energy_ha)
        except Exception as exc:
            logger.warning("Failed to extract ORCA energy for %s: %s", node_id, exc)

    # Extract ORCA-specific results (frequencies, convergence, UV-Vis)
    # Check params for software type since unified types (freq, geo_opt) don't indicate engine
    is_orca_task = engine_key == "orca" or params.get("software") == "orca"
    if is_orca_task and node_type in ("freq", "orca_freq", "geo_opt", "orca_opt",
                                       "uvvis", "orca_uvvis", "irc", "orca_irc", "orca_neb_ts"):
        try:
            orca_output = await _read_orca_output(hpc, work_dir, node_id)
        except Exception as exc:
            logger.debug(f"Failed to read ORCA.out for {node_id}: {exc}")
            orca_output = None

        if orca_output:
            try:
                # Route to correct parser based on node type
                if node_type in ("freq", "orca_freq"):
                    from catgo.utils.orca_output import OrcaFreqOutput
                    parser = OrcaFreqOutput(orca_output)
                    orca_results = parser.get_summary()
                    result.update(orca_results)
                    logger.info("ORCA freq parsed: %d frequencies, %d imaginary",
                               len(orca_results.get("frequencies", [])),
                               orca_results.get("num_imaginary", 0))

                elif node_type in ("geo_opt", "orca_opt"):
                    from catgo.utils.orca_output import OrcaOptOutput
                    parser = OrcaOptOutput(orca_output)
                    orca_results = parser.get_summary()
                    result.update(orca_results)
                    conv_pts = orca_results.get("convergence_points", [])
                    logger.info("ORCA opt parsed: %d convergence points, converged=%s",
                               len(conv_pts), orca_results.get("converged", False))

                elif node_type in ("uvvis", "orca_uvvis"):
                    from catgo.utils.orca_output import OrcaUvVisOutput
                    parser = OrcaUvVisOutput(orca_output)
                    orca_results = parser.get_summary()
                    result.update(orca_results)
                    logger.info("ORCA UV-Vis parsed: %d excitations", len(orca_results.get("excitations", [])))

                elif node_type in ("irc", "orca_irc"):
                    from catgo.utils.orca_output import OrcaIrcOutput
                    parser = OrcaIrcOutput(orca_output)
                    orca_results = parser.get_summary()
                    result.update(orca_results)
                    conv_pts = orca_results.get("convergence_points", [])
                    logger.info("ORCA IRC parsed: %d path points", len(conv_pts))

                elif node_type == "orca_neb_ts":
                    from catgo.utils.orca_output import OrcaNebOutput
                    parser = OrcaNebOutput(orca_output)
                    orca_results = parser.get_summary()
                    result.update(orca_results)
                    logger.info("ORCA NEB-TS parsed")

                    # Read ORCA.interp for per-iteration image energies
                    try:
                        from catgo.utils.job_parser import _parse_interp_content
                        interp_result = await hpc.run_on_owner(lambda: hpc.conn.run(
                            f"cat {work_dir}/ORCA.interp", check=False
                        ))
                        if interp_result.exit_status == 0 and interp_result.stdout:
                            image_energies = _parse_interp_content(interp_result.stdout)
                            if image_energies:
                                # Convert tuple values to lists for JSON serialization
                                result["image_energies"] = {
                                    str(k): [[img_idx, energy] for img_idx, energy in v]
                                    for k, v in image_energies.items()
                                }
                                logger.info("ORCA NEB-TS: parsed %d iterations from .interp",
                                           len(image_energies))
                    except Exception as exc:
                        logger.debug("Failed to read ORCA.interp for %s: %s", node_id, exc)

            except Exception as exc:
                logger.warning(f"Failed to parse ORCA results for {node_id}: {exc}", exc_info=True)

    # Extract frequency data for VASP freq nodes
    if node_type == "freq" and engine_key == "vasp":
        try:
            from catgo.utils.vasp_freq_parser import parse_vasp_frequencies
            freq_data = await hpc.run_on_owner(lambda: parse_vasp_frequencies(hpc.conn, work_dir))
            if freq_data.get("success"):
                result.update(freq_data)
        except Exception as exc:
            logger.warning(
                "Failed to parse VASP frequencies for %s: %s", node_id, exc
            )

    return result


async def _read_orca_output(hpc_connection: Any, work_dir: str, task_id: str) -> str:
    """Read ORCA.out from HPC. Returns output text or raises on failure."""
    result = await hpc_connection.run_on_owner(lambda: hpc_connection.conn.run(
        f"cat {work_dir}/ORCA.out",
        check=True,
    ))
    return result.stdout


async def collect_orca_freq_results(
    hpc_connection: Any,
    work_dir: str,
    task_id: str,
) -> str:
    """Collect frequency calculation results from completed ORCA job.

    Uses OrcaFreqOutput.get_summary() which produces the exact format
    the frontend NodeStatusPanel expects: frequencies as array-of-objects
    with index/frequency_cm/imaginary/ir_intensity_km_mol, plus
    num_imaginary, zpe_kj_mol, enthalpy_eh, entropy_j_mol_k, gibbs_eh.
    """
    from catgo.utils.orca_output import OrcaFreqOutput

    try:
        output_text = await _read_orca_output(hpc_connection, work_dir, task_id)
    except Exception as e:
        logger.error(f"Task {task_id}: failed to read ORCA.out: {e}")
        return json.dumps({"error": f"Failed to read output: {str(e)}"})

    try:
        parser = OrcaFreqOutput(output_text)
        results_dict = parser.get_summary()
        results_dict["type"] = "orca_freq"

        n_freqs = len(results_dict.get("frequencies", []))
        logger.info(f"Task {task_id}: parsed {n_freqs} frequencies, "
                     f"num_imaginary={results_dict.get('num_imaginary', 0)}")
        return json.dumps(results_dict)

    except Exception as e:
        logger.error(f"Task {task_id}: failed to parse ORCA output: {e}", exc_info=True)
        return json.dumps({"error": f"Parsing failed: {str(e)}"})


async def collect_orca_irc_results(
    hpc_connection: Any,
    work_dir: str,
    task_id: str,
) -> str:
    """Collect IRC path results from completed ORCA job.

    Uses OrcaIrcOutput.get_summary() which produces: irc_converged,
    forward_converged, backward_converged, convergence_thresholds,
    convergence_points (array for IrcPathPlot), forward_endpoint,
    backward_endpoint, reaction_coordinate_data.
    """
    from catgo.utils.orca_output import OrcaIrcOutput

    try:
        output_text = await _read_orca_output(hpc_connection, work_dir, task_id)
    except Exception as e:
        logger.error(f"Task {task_id}: failed to read ORCA.out: {e}")
        return json.dumps({"error": f"Failed to read output: {str(e)}"})

    try:
        parser = OrcaIrcOutput(output_text)
        results_dict = parser.get_summary()
        results_dict["type"] = "orca_irc"

        n_points = len(results_dict.get("convergence_points", []))
        logger.info(f"Task {task_id}: parsed IRC with {n_points} points, "
                     f"converged={results_dict.get('irc_converged')}")
        return json.dumps(results_dict)

    except Exception as e:
        logger.error(f"Task {task_id}: failed to parse ORCA IRC: {e}", exc_info=True)
        return json.dumps({"error": f"Parsing failed: {str(e)}"})


async def collect_orca_opt_results(
    hpc_connection: Any,
    work_dir: str,
    task_id: str,
) -> str:
    """Collect geometry optimization results from completed ORCA job.

    Uses OrcaOptOutput.get_summary() which produces: energy_eh, energy_ev,
    converged, n_steps, max_gradient, rms_gradient, convergence_points
    (array for ConvergencePlot).
    """
    from catgo.utils.orca_output import OrcaOptOutput

    try:
        output_text = await _read_orca_output(hpc_connection, work_dir, task_id)
    except Exception as e:
        logger.error(f"Task {task_id}: failed to read ORCA.out: {e}")
        return json.dumps({"error": f"Failed to read output: {str(e)}"})

    try:
        parser = OrcaOptOutput(output_text)
        results_dict = parser.get_summary()
        results_dict["type"] = "orca_opt"

        logger.info(f"Task {task_id}: collected ORCA opt results, "
                     f"energy={results_dict.get('energy_eh')}, "
                     f"converged={results_dict.get('converged')}, "
                     f"steps={results_dict.get('n_steps')}")
        return json.dumps(results_dict)

    except Exception as e:
        logger.error(f"Task {task_id}: failed to parse ORCA opt output: {e}", exc_info=True)
        return json.dumps({"error": f"Parsing failed: {str(e)}"})


async def collect_orca_neb_results(
    hpc_connection: Any,
    work_dir: str,
    task_id: str,
) -> str:
    """Collect NEB-TS results from completed ORCA job.

    Uses OrcaNebOutput.get_summary() which produces: ts_converged,
    activation_barrier_kcal_mol, ts_imaginary_frequency,
    path_summary (with images array for NebPathPlot), convergence_points,
    vibrational_data, warnings.
    """
    from catgo.utils.orca_output import OrcaNebOutput

    try:
        output_text = await _read_orca_output(hpc_connection, work_dir, task_id)
    except Exception as e:
        logger.error(f"Task {task_id}: failed to read ORCA.out: {e}")
        return json.dumps({"error": f"Failed to read output: {str(e)}"})

    try:
        parser = OrcaNebOutput(output_text)
        results_dict = parser.get_summary()
        results_dict["type"] = "orca_neb_ts"

        # Read ORCA.interp for per-iteration image energies (same as
        # collect_completed_results does for the generic path).  Without
        # this, the early-exit in collector.py skips the generic collector
        # and image_energies never make it into the stored results.
        try:
            from catgo.utils.job_parser import _parse_interp_content
            interp_result = await hpc_connection.conn.run(
                f"cat {work_dir}/ORCA.interp", check=False
            )
            if interp_result.exit_status == 0 and interp_result.stdout:
                image_energies = _parse_interp_content(interp_result.stdout)
                if image_energies:
                    results_dict["image_energies"] = {
                        str(k): [[img_idx, energy] for img_idx, energy in v]
                        for k, v in image_energies.items()
                    }
                    logger.info("Task %s: parsed %d iterations from .interp",
                               task_id, len(image_energies))
        except Exception as exc:
            logger.debug("Task %s: failed to read ORCA.interp: %s", task_id, exc)

        logger.info(f"Task {task_id}: collected ORCA NEB results, "
                     f"ts_converged={results_dict.get('ts_converged')}, "
                     f"barrier={results_dict.get('activation_barrier_kcal_mol')}")
        return json.dumps(results_dict)

    except Exception as e:
        logger.error(f"Task {task_id}: failed to parse ORCA NEB output: {e}", exc_info=True)
        return json.dumps({"error": f"Parsing failed: {str(e)}"})


async def collect_orca_sp_results(
    hpc_connection: Any,
    work_dir: str,
    task_id: str,
) -> str:
    """Collect single point energy results from completed ORCA job.

    Uses OrcaSinglePointOutput.get_summary() which produces: energy_eh,
    energy_ev, convergence_points.
    """
    from catgo.utils.orca_output import OrcaSinglePointOutput

    try:
        output_text = await _read_orca_output(hpc_connection, work_dir, task_id)
    except Exception as e:
        logger.error(f"Task {task_id}: failed to read ORCA.out: {e}")
        return json.dumps({"error": f"Failed to read output: {str(e)}"})

    try:
        parser = OrcaSinglePointOutput(output_text)
        results_dict = parser.get_summary()
        results_dict["type"] = "orca_sp"
        results_dict["converged"] = results_dict.get("energy_eh") is not None

        logger.info(f"Task {task_id}: collected ORCA SP results, "
                     f"energy={results_dict.get('energy_eh')}")
        return json.dumps(results_dict)

    except Exception as e:
        logger.error(f"Task {task_id}: failed to parse ORCA SP output: {e}", exc_info=True)
        return json.dumps({"error": f"Parsing failed: {str(e)}"})


async def collect_orca_uvvis_results(
    hpc_connection: Any,
    work_dir: str,
    task_id: str,
) -> str:
    """Collect UV-Vis spectroscopy results from completed ORCA job.

    Uses OrcaUvVisOutput.get_summary() which produces: transitions,
    n_transitions, method, brightest_wavelength_nm,
    brightest_oscillator_strength, convergence_points.
    """
    from catgo.utils.orca_output import OrcaUvVisOutput

    try:
        output_text = await _read_orca_output(hpc_connection, work_dir, task_id)
    except Exception as e:
        logger.error(f"Task {task_id}: failed to read ORCA.out: {e}")
        return json.dumps({"error": f"Failed to read output: {str(e)}"})

    try:
        parser = OrcaUvVisOutput(output_text)
        results_dict = parser.get_summary()
        results_dict["type"] = "orca_uvvis"

        logger.info(f"Task {task_id}: collected ORCA UV-Vis results, "
                     f"n_transitions={results_dict.get('n_transitions')}")
        return json.dumps(results_dict)

    except Exception as e:
        logger.error(f"Task {task_id}: failed to parse ORCA UV-Vis output: {e}", exc_info=True)
        return json.dumps({"error": f"Parsing failed: {str(e)}"})
