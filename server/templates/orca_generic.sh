#!/bin/bash
#SBATCH --job-name="{{job_name}}"
#SBATCH --nodes={{nodes}}
#SBATCH --ntasks-per-node={{ntasks}}
{% if partition %}#SBATCH --partition={{partition}}{% endif %}
{% if memory %}#SBATCH --mem={{memory}}{% endif %}
{% if account %}#SBATCH --account={{account}}{% endif %}
#SBATCH --time={{walltime}}
#SBATCH --output={{job_name}}.log
#SBATCH --error={{job_name}}.err

# Set up environment (customize as needed for your cluster)
{% if module_loads %}{{module_loads}}{% endif %}

# ORCA setup with full path (required for parallel MPI runs)
{% if orca_dir %}export ORCA_DIR={{orca_dir}}
export PATH=$ORCA_DIR:$PATH
export LD_LIBRARY_PATH=$ORCA_DIR/lib:$LD_LIBRARY_PATH
ORCA_BINARY=$ORCA_DIR/orca
{% else %}
ORCA_BINARY=orca
{% endif %}

# Local scratch directory setup (improves I/O performance)
SCRATCH_DIR=${TMPDIR:-/tmp}/orca_${SLURM_JOB_ID}
mkdir -p $SCRATCH_DIR
trap "rm -rf $SCRATCH_DIR" EXIT

# Copy input files to local scratch
cp {{work_dir}}/ORCA.inp $SCRATCH_DIR/ 2>/dev/null || true
if [ -f {{work_dir}}/reactant.xyz ]; then cp {{work_dir}}/reactant.xyz $SCRATCH_DIR/; fi
if [ -f {{work_dir}}/product.xyz ]; then cp {{work_dir}}/product.xyz $SCRATCH_DIR/; fi

# Work in scratch directory
cd $SCRATCH_DIR

# Run ORCA calculation with full binary path
$ORCA_BINARY ORCA.inp > ORCA.out 2>&1
EXIT_CODE=$?

# Copy results back to work directory.
# Use `2>/dev/null || true` for everything optional so a missing file never
# fails the stage-back step (and cp on a no-match wildcard fails silently).
shopt -s nullglob

cp ORCA.out {{work_dir}}/
cp ORCA.inp {{work_dir}}/ 2>/dev/null || true

# OPI / orca_2json structured outputs (required for skill-side OPI parsing).
# `jsonpropfile True` -> ORCA.property.json
# `jsongbwfile  True` -> ORCA.json (the GBW JSON)
cp ORCA.property.json {{work_dir}}/ 2>/dev/null || true
cp ORCA.json {{work_dir}}/ 2>/dev/null || true

# Common single-file outputs.
cp ORCA.gbw     {{work_dir}}/ 2>/dev/null || true
cp ORCA.hess    {{work_dir}}/ 2>/dev/null || true   # for IRC InitHess=read reuse
cp ORCA.engrad  {{work_dir}}/ 2>/dev/null || true
cp ORCA.xyz     {{work_dir}}/ 2>/dev/null || true
cp ORCA_property.txt {{work_dir}}/ 2>/dev/null || true
cp ORCA_freq.txt     {{work_dir}}/ 2>/dev/null || true
cp reactant_opt.xyz  {{work_dir}}/ 2>/dev/null || true
cp product_opt.xyz   {{work_dir}}/ 2>/dev/null || true

# Multi-file globs (require nullglob set above so unmatched patterns expand
# to nothing instead of being passed literally to cp).
for f in ORCA_IRC*.dat ORCA_IRC*.xyz; do cp "$f" {{work_dir}}/; done   # orca-irc
for f in ORCA_MEP_trj.xyz ORCA.NEB*.log ORCA_im*.gbw; do cp "$f" {{work_dir}}/; done   # orca-neb-ts

shopt -u nullglob

exit $EXIT_CODE
