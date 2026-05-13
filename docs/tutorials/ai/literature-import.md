---
title: Importing a Paper
description: Upload a PDF or paste a DOI so CatBot can reference it while building a workflow
source: server/catgo/routers/paper.py
---

# Importing a Paper

CatBot can read scientific papers and use them as context for workflow construction. There are two ways to feed a paper in: upload the PDF directly, or paste a DOI and let CatGo fetch the metadata.

This tutorial walks through both, plus what CatBot can — and can't — do with the result.

## Option 1: Upload a PDF

1. Open the CatBot chat panel.
2. Drag a PDF onto the chat input, or click the attachment icon and pick the file.
3. CatBot uploads the PDF to the backend (`POST /paper/upload`), receives a session ID, and shows a confirmation card with the paper's title and page count.
4. The paper's text is now available as context for the rest of the conversation (until session TTL expires — typically 1 hour of inactivity).

## Option 2: Paste a DOI

1. In the chat input, paste a DOI (`10.1038/nature12345`) or a DOI URL (`https://doi.org/10.1038/nature12345`).
2. CatBot resolves it through CrossRef (`POST /paper/resolve-doi`) and shows title, authors, journal, year, and abstract.
3. The metadata enters the chat context — note that DOI resolution gives you metadata only, not the full text.

## What CatBot Can Do With an Imported Paper

- Answer questions about the paper's content: methods used, functionals, basis sets, k-point meshes, post-processing steps
- Compare two papers' computational setups
- Suggest a workflow that mirrors the paper's method
- Build a workflow on request, populating nodes with parameters discussed in the paper

## What CatBot Can *Not* Do

- Automatic, click-once "build me a workflow from this paper" generation — there's no extractor that produces a workflow from a PDF without a chat turn
- Read figures, tables, or embedded images from the PDF — only the extracted text is available
- Persist papers across CatGo restarts — the session is in-memory with a TTL

## Example Conversation

```
[You upload "Kreitz_2021_CO2_desorption_Ni.pdf"]
[CatBot: "Loaded — 18 pages, abstract mentions Ni(111), (100), (110), (211) facets."]

You:    What functional did they use and at what ENCUT?

CatBot: PBE-D3(BJ) with a 450 eV plane-wave cutoff. K-point sampling
        was 8×8×1 for slabs and 12×12×12 for the bulk.

You:    Good. Build a workflow that reproduces their Ni(111) setup —
        slab construction, adsorbate placement for CO, then a VASP
        relax with their parameters.

CatBot: [adds Slab → Adsorbate → VASP Relax nodes, populates ENCUT=450,
        KPOINTS=8x8x1, with PBE-D3 selected; opens the run config.]
```

## Manually Clearing a Session

Sessions expire automatically, but you can clear one early from the chat menu (the paper attachment card has a "Forget paper" action), which calls `DELETE /paper/{session_id}` under the hood.

## Related

- [Paper Import Module](/modules/ai/literature-import) — API reference and data model
- [Workflows Tutorial](/tutorials/workflows/workflows) — Constructing workflows by hand
