---
name: atom-ops
description: One-shot recipes for adding, deleting, moving, and replacing individual atoms in the active CatGo viewer structure. Use whenever the user asks to "add an atom", "delete atoms", "remove this atom", "move atom N", "replace H with Li", or any single-atom edit — including "add a hydrogen on top of atom 12" / "delete atoms 5–9" / "swap the oxygen at site 3 for fluorine". Skips the discovery loop (no need to list structure tools or check adsorption sites first); goes straight to the matching `catgo_structure` action. Triggers in Chinese on 加原子, 删原子, 减原子, 移动原子, 替换原子, 增加氢, 删除氧, 把 ... 换成 ....
---

# atom-ops

Single-atom edits via `mcp__catgo__catgo_structure`. The default exploration path lists structure-tool actions, reads several skill docs, and queries the current viewer state before each action — that is 4–8 MCP calls for a one-atom edit and the user sees "Thinking…" for 15–30 s. This skill collapses every common operation to a single call.

## When to use this skill

- Adding one atom (or a small handful) at known coordinates or a known relationship to an existing atom.
- Deleting atoms by index or by element.
- Replacing an atom's element without moving it.
- Moving an atom by index to a new position.

If the user wants to add **a molecule or cluster** (CO, H₂O, NH₂, …) onto a surface, **stop and use the `structure/cluster_ops` skill instead** — placing a molecule needs adsorbate placement and site selection, not raw atom addition.

## Operation cheat sheet

Every recipe below is a single `mcp__catgo__catgo_structure` call. Each item lists the `action`, the required params, and the typical user phrasing.

### Add a single atom at explicit Cartesian coordinates

User: *"Add an H at (1.5, 2.0, 6.3) Å"*

```json
{"action":"add_atom","element":"H","position":[1.5,2.0,6.3]}
```

### Add an atom near another atom (height above a site)

User: *"Place a hydrogen 1.0 Å above atom 12"*

You need the position of atom 12. Two paths:

1. If the user just told you the coordinate, use it directly with `position`.
2. Otherwise call `mcp__catgo__catgo_structure {"action":"get_info"}` once, find the site, add `[0, 0, height]` to its xyz, then issue `add_atom`. **Do not call `get_info` more than once per chat turn** — re-use the result.

For atoms placed on a slab surface (above the topmost layer), use `mcp__catgo__catgo_structure {"action":"add_atom","element":"H","position":[x,y,z]}` where z = (highest-atom z) + bond length (typical: O–H 1.0 Å, H–metal 1.5 Å, C–metal 2.0 Å).

### Delete atoms by index

User: *"Delete atoms 5, 6, 7"* or *"remove the last 3 atoms"* or *"删除 5 到 9"*

```json
{"action":"delete_atoms","indices":[5,6,7]}
```

Indices are 0-based and refer to the current viewer site order. For ranges, expand them yourself (`5,6,7` not `5-7`). For "the last 3 atoms" you need `get_info` to know the site count first; same single-call-per-turn rule applies.

### Delete all atoms of an element

User: *"Remove all hydrogens"*

```json
{"action":"delete_atoms","element":"H"}
```

This is faster than enumerating indices when the user names an element.

### Replace an atom's element

User: *"Swap the oxygen at site 3 for fluorine"* or *"把 site 7 的 C 换成 N"*

```json
{"action":"replace_atom","index":3,"new_element":"F"}
```

This is **substitution at a fixed position** — the element changes, the xyz stays. For systematic element-screening across many sites, use the dedicated `structure/substitution` skill instead.

### Move an atom to a new position

User: *"Move atom 12 to (2.0, 3.0, 5.5)"*

```json
{"action":"move_atom","index":12,"position":[2.0,3.0,5.5]}
```

For relative moves ("shift atom 12 by 0.5 Å along z"), compute the new absolute position yourself from `get_info` once, then call `move_atom`.

## What NOT to do

These patterns are slow and add no value:

- Listing all structure-tool actions (`{"action":"list"}` or similar discovery calls) before doing the edit. The actions above are the complete set you need.
- Calling `get_info` repeatedly to verify each edit succeeded. CatGo's viewer reactivity already shows the change; the tool response confirms it; re-fetching wastes round-trips.
- Asking the user to confirm "which atom" when the indices are obvious from their message. Confirm only when the request is genuinely ambiguous ("remove the carbon atoms" with multiple carbons in different chemical environments — confirm which set).

## After-edit confirmation

One sentence stating what changed. Mention the new total atom count if it changed.

> Added one H at (1.5, 2.0, 6.3). Structure now has 13 atoms.
> Deleted atoms 5–9. Structure now has 27 atoms.
> Replaced O at site 3 with F. Composition: Ti2O3F.

Do **not** dump the full site list or coordinates back to the user — the viewer shows the result.
