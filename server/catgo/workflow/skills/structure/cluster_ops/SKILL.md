---
name: cluster-ops
description: One-shot recipes for adding, removing, or repositioning molecular fragments (adsorbates, water layers, ion clusters) on the active CatGo viewer structure. Use whenever the user asks to "place CO on the surface", "put H2O on top site", "add an adsorbate", "build a coverage", "add a water layer", "place two adsorbates for coupling", "build a (2,2,1) supercell", "remove the adsorbate", "delete the water cluster". Skips the discovery loop, finds adsorption sites once, and places the molecule(s) with a single `add_molecule` / `merge` call. Triggers in Chinese on 放吸附物, 放分子, 加水层, 偶联, 双吸附, 加水, 超胞, 删除吸附物, 移除分子.
---

# cluster-ops

Multi-atom edits — adsorbate placement, water layers, ion clusters, supercell expansion. The default exploration path lists `catgo_structure` actions, asks the analysis MCP for adsorption sites, eyeballs them, then composes a `merge` call manually. This skill collapses each case to a single MCP call with the correct parameters.

## When to use this skill

- Placing a molecule or polyatomic adsorbate on a surface (`add_molecule` or analysis→merge).
- Building dual-adsorbate configurations for coupling reactions (C–N, C–C, N–N).
- Adding a water solvation layer on top of a slab.
- Building or expanding a supercell.
- Removing a previously-placed cluster (delete by indices spanning the cluster atoms).

If the user wants to edit a **single atom** (add H at coord, swap O for F, move atom 12, delete one atom), **use the `structure/atom_ops` skill instead** — atom-level ops have different MCP entry points.

## Operation cheat sheet

### Add a single small molecule at a Cartesian position

User: *"Add a water molecule at (3.0, 3.0, 8.0)"* or *"加一个 H2O 在 slab 上方"*

```json
{
  "action": "add_molecule",
  "query": "water",
  "count": 1,
  "position": [3.0, 3.0, 8.0]
}
```

`query` accepts common names (`water`, `methanol`, `ammonia`, `formate`, `co`, `oh`, `nh2`, …) or formulas. If position is omitted, the molecule is placed near the structure centroid; specify `position` for placement above a slab.

### Place an adsorbate on a surface (auto site selection)

User: *"Place CO on a hollow site of the Cu(111) slab"*

Two-step playbook:

1. Call `catgo_analyze` once to enumerate adsorption sites:
   ```json
   {"action": "adsorption_sites"}
   ```
   The response lists sites with type (top/bridge/hollow/fcc/hcp) and `[x, y, z]` coordinates. Use it to pick the matching site type the user asked for; if multiple, pick the first one by default and tell the user "placed on the first hollow site — there are N total, ask to switch if needed".

2. Add the adsorbate at the chosen site, offset above the surface by the typical bond length:
   ```json
   {
     "action": "add_molecule",
     "query": "CO",
     "count": 1,
     "position": [site_x, site_y, site_z + 1.8]
   }
   ```
   Typical bond-length offsets above the topmost slab atom:
   - C, N, O end-on to metal: **1.8 Å**
   - C–C through carbon: **2.0 Å**
   - H to metal (η¹-H): **1.5 Å**
   - O of H₂O (η¹ oxygen): **2.2 Å**

Do **not** call `adsorption_sites` more than once per turn. Re-use the same response if the user asks for several placements on the same slab.

### Dual adsorbates for C–N (or any X–Y) coupling

User: *"Place CO and NH2 on Cu(111), 3.5 Å apart, for C–N coupling slow-growth"*

The CatGo server exposes a dedicated combined call (used by the AI workflow tutorial). Pattern:

1. `catgo_analyze adsorption_sites` once.
2. Pick two distinct sites whose Cartesian distance is closest to the requested separation (or just pick adjacent fcc-hcp pair on a (111) surface — typical distance ~2.5–3 Å on metals).
3. Two sequential `add_molecule` calls anchored at those sites, with adsorbates oriented so the coupling atoms face each other. The `query` accepts the molecule, and orientation is currently a follow-up edit.

If the user names a specific reaction (C–N coupling for nitrate-to-ammonia, urea synthesis, etc.), recommend the `slow_growth` workflow node with `iconst="R i1 i2 0"` where `i1` and `i2` are the atom indices of C and N after placement. The user usually wants to chain "place + slow-growth"; combine this skill with `workflow_builder` in a single response.

### Add a water solvation layer on top of a slab

User: *"Add a water layer 3 Å above the Cu surface"* or *"做水层"*

Packmol-style placement using `add_molecule` with `count > 1`:

```json
{
  "action": "add_molecule",
  "query": "water",
  "count": 16,
  "spacing": 2.8,
  "position": [center_x, center_y, top_z + 3.0]
}
```

- `count = 16` is a typical 1-monolayer coverage for a 2x2 surface. For larger cells scale ~density: 4 waters per ~6×6 Å² of surface area.
- `spacing = 2.8` Å matches the average O–O hydrogen-bond distance.
- `top_z + 3.0` places the centre of the cluster ~3 Å above the topmost slab atom.

The result is a Packmol-packed cluster of waters above the slab. Tell the user the count and the layer height, and offer to follow with an MD equilibration step (an NVT MD node at 300 K, 2000 steps) if they want a physically reasonable starting geometry instead of a frozen packed configuration.

### Build a supercell

User: *"Make a 2x2x1 supercell"* / *"做超胞 3×3×1"*

```json
{"action": "supercell", "scaling": [2, 2, 1]}
```

For non-diagonal supercells (anisotropic strain studies, twisted bilayer commensurate cells), pass a `matrix` (3×3 integers) instead of `scaling`.

If the user asks for a supercell of a *slab*, do it **after** slab generation, not before — supercelling a bulk and then slabbing along an oblique direction can change the actual surface orientation. The same constraint matters for adsorbate placement: supercell **before** placing the adsorbate so the placement is the right multiplicity, otherwise the adsorbate gets duplicated.

### Merge an external structure (cluster, fragment, molecule from file)

User: *"Drop this ammonia cluster I just loaded onto the slab"*

```json
{"action": "merge", "structure": <pymatgen-dict>, "position": [x, y, z]}
```

Use this when the incoming fragment is not a standard library molecule (`add_molecule` covers common species). The `structure` argument is the pymatgen dict for the incoming fragment; the position is where to place its centroid.

### Remove a previously-placed cluster

User: *"Remove the CO I just placed"* or *"删掉刚才的水层"*

CatGo flags placed clusters' atom indices in the action response. Re-use those indices in a single `delete` call from the `structure/atom_ops` skill (`{"action":"delete","indices":[...]}`). If you don't have the indices, calling `get` once and filtering by element / Cartesian range is acceptable but slower; prefer keeping the indices from the previous placement turn.

## What NOT to do

- Calling `adsorption_sites` repeatedly within a chat turn — the site list does not change unless the slab changes, so cache it.
- Calling `add_molecule` once per atom of a polyatomic adsorbate. The skill is `add_molecule` (one call per molecule, not per atom).
- Picking a placement height by visual inspection of the structure summary. The bond-length offsets above are calibrated and produce starting geometries within ~0.3 Å of relaxed positions.

## After-edit confirmation

One sentence. Name the species, where it was placed (site type, fractional or "above topmost atom by X Å"), and the new total atom count.

> Placed CO on the first fcc-hollow site of Cu(111), 1.8 Å above the surface. Structure now has 26 atoms.
> Added a 16-water layer 3 Å above the slab (Packmol-packed, O–O spacing 2.8 Å). 92 atoms total.
> Made a 2x2x1 supercell. 48 → 192 atoms.

Do **not** dump the full coordinate list — the viewer renders the result.
