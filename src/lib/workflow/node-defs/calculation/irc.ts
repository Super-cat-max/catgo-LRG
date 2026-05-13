import type { NodeDefinition } from '../../workflow-types'
import {
  SYSTEM_TYPE_PARAM,
  orca_only,
} from '../common'

export const IRC_NODE: NodeDefinition = {
  type: `irc`,
  label: `IRC`,
  color: `#d946ef`,
  icon: `\u{1F6E4}\uFE0F`,
  category: `Calculation`,
  description: `Intrinsic reaction coordinate`,
  inputs: [`structure`],
  outputs: [`trajectory`, `structures`],
  default_params: { system_type: `molecular`, software: `orca`, method: `r2SCAN-3c`, basis: `6-31G`, max_iterations: 30, initial_displacement_energy: 2.0, charge: 0, multiplicity: 1 },
  help_text: `**IRC** — Trace reaction path from transition state.

Intrinsic Reaction Coordinate (IRC) follows the steepest descent path from a TS to the nearest minima (reactant and product).`,
  param_schema: [
    SYSTEM_TYPE_PARAM,
    {
      key: `software`, label: `Software`, type: `select`, default: `orca`, group: `Software`,
      options: [
        { label: `ORCA`, value: `orca` },
      ],
    },
    // ── ORCA IRC params ──
    ...orca_only([
      {
        key: `method`, label: `Method`, type: `select`, default: `r2SCAN-3c`, group: `Quantum`,
        options: [
          { label: `HF`, value: `HF` },
          { label: `BP86`, value: `BP86` },
          { label: `BLYP`, value: `BLYP` },
          { label: `PBE`, value: `PBE` },
          { label: `B3LYP`, value: `B3LYP` },
          { label: `PBE0`, value: `PBE0` },
          { label: `B3PW91`, value: `B3PW91` },
          { label: `M06L`, value: `M06L` },
          { label: `M062X`, value: `M062X` },
          { label: `R2SCAN`, value: `R2SCAN` },
          { label: `r2SCAN-3c`, value: `r2SCAN-3c` },
          { label: `PBEh-3c`, value: `PBEh-3c` },
          { label: `B2PLYP`, value: `B2PLYP` },
          { label: `CCSD`, value: `CCSD` },
          { label: `MP2`, value: `MP2` },
        ],
        help: `Quantum chemistry method. r2SCAN-3c recommended for speed.`,
      },
      {
        key: `basis`, label: `Basis Set`, type: `select`, default: `6-31G`, group: `Quantum`,
        options: [
          { label: `(none — composite method)`, value: `` },
          { label: `STO-3G`, value: `STO-3G` },
          { label: `6-31G`, value: `6-31G` },
          { label: `6-31G*`, value: `6-31G*` },
          { label: `6-311G`, value: `6-311G` },
          { label: `6-311+G**`, value: `6-311+G**` },
          { label: `def2-SVP`, value: `def2-SVP` },
          { label: `def2-TZVP`, value: `def2-TZVP` },
          { label: `def2-TZVPP`, value: `def2-TZVPP` },
          { label: `def2-QZVP`, value: `def2-QZVP` },
          { label: `cc-pVDZ`, value: `cc-pVDZ` },
          { label: `cc-pVTZ`, value: `cc-pVTZ` },
          { label: `cc-pVQZ`, value: `cc-pVQZ` },
          { label: `cc-pVDZ-F12`, value: `cc-pVDZ-F12` },
          { label: `cc-pVTZ-F12`, value: `cc-pVTZ-F12` },
        ],
        help: `Basis set. def2 family recommended for ORCA. def2-SVP for screening, def2-TZVP for production.`,
      },
      {
        key: `wavefunction`, label: `Wavefunction`, type: `select`, default: ``, group: `Quantum`,
        options: [
          { label: `Auto (default)`, value: `` },
          { label: `RHF`, value: `RHF` },
          { label: `UHF`, value: `UHF` },
          { label: `ROHF`, value: `ROHF` },
          { label: `RKS`, value: `RKS` },
          { label: `UKS`, value: `UKS` },
          { label: `ROKS`, value: `ROKS` },
        ],
        help: `Wavefunction reference. Auto lets ORCA choose (RHF for HF, RKS for DFT). Use UHF/UKS for open-shell systems.`,
      },
      {
        key: `dispersion`, label: `Dispersion`, type: `select`, default: `none`, group: `SCF`,
        options: [
          { label: `None`, value: `none` },
          { label: `D2`, value: `D2` },
          { label: `D3 (BJ damping)`, value: `D3` },
          { label: `D3BJ (recommended)`, value: `D3BJ` },
          { label: `D3ZERO (zero damping)`, value: `D3ZERO` },
          { label: `D30 (= D3ZERO)`, value: `D30` },
          { label: `D3TZ (triple-ζ params, D3ZERO only)`, value: `D3TZ` },
          { label: `D4 (BJ + ATM, newer)`, value: `D4` },
          { label: `NOVDW (disable D corrections)`, value: `NOVDW` },
        ],
        help: `ORCA simple-input dispersion keyword. D3BJ is the typical default for DFT functionals; D4 is newer and BJ-damped by default. NOVDW explicitly disables dispersion. See ORCA manual §3.4.1.`,
      },
      {
        key: `three_body_dispersion`, label: `Three-body term (ABC/ATM)`, type: `boolean`, default: false, group: `SCF`,
        show_if: { key: `dispersion`, values: [`D2`, `D3`, `D3BJ`, `D3ZERO`, `D30`, `D3TZ`] },
        help: `Adds the three-body Axilrod-Teller-Muto (ATM) term to the route line as 'ABC'. Only relevant for D3 variants — D4 already includes ATM by default.`,
      },
      {
        key: `grid`, label: `Integration Grid`, type: `select`, default: `DefGrid2`, group: `SCF`,
        options: [
          { label: `DefGrid1 (coarse)`, value: `DefGrid1` },
          { label: `DefGrid2 (standard)`, value: `DefGrid2` },
          { label: `DefGrid3 (fine)`, value: `DefGrid3` },
        ],
        help: `DFT integration grid accuracy. DefGrid2 standard, DefGrid3 for tight convergence or meta-GGA.`,
      },
      {
        key: `num_cores`, label: `CPU Cores`, type: `number`, default: 4, group: `Parallelization`,
        min: 1, max: 256, step: 1,
        help: `Number of CPU cores for ORCA parallel execution.`,
      },
      {
        key: `max_core_mb`, label: `Memory per Core (MB)`, type: `number`, default: 4000, group: `Parallelization`,
        min: 256, max: 64000, step: 256,
        help: `Maximum memory per core in MB.`,
      },
      {
        key: `max_iterations`, label: `Max IRC Steps`, type: `number`, default: 30, group: `IRC`, min: 10, max: 100,
        help: `Maximum IRC path-following steps.`,
      },
      {
        key: `initial_displacement_energy`, label: `Initial Displacement Energy (mEh)`, type: `number`, default: 2.0, group: `IRC`, min: 0.5, max: 10.0, step: 0.5,
        help: `Initial IRC step size (mEh). 2.0 typical.`,
      },
      {
        key: `uno`, label: `Generate Natural Orbitals (UNO)`, type: `boolean`, default: false, group: `Output`,
        help: `Generate natural orbitals and occupation numbers.`,
      },
      {
        key: `uco`, label: `Corresponding Orbitals (UCO)`, type: `boolean`, default: false, group: `Output`,
        help: `Generate corresponding orbitals.`,
      },
      {
        key: `charge`, label: `Charge`, type: `number`, default: 0, group: `System`,
        help: `Total charge of the system.`,
      },
      {
        key: `multiplicity`, label: `Multiplicity`, type: `number`, default: 1, group: `System`,
        help: `Spin multiplicity (2S+1). 1=singlet, 2=doublet, 3=triplet.`,
      },
    ]),
  ],
}
