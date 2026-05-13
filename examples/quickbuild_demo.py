"""quickbuild_demo.py — drive CatGo's zero-LLM workflow builder from Python.

The HTTP endpoint /api/workflow/quickbuild takes a recipe name and emits a
complete DAG workflow in one round-trip (~200 ms), bypassing the LLM. This
script lists the available recipes, builds one for each, and prints the
resulting workflow id + name. Useful for high-throughput catalyst screening,
or as a starting point for scripted experiments that wrap the same API the
in-app Quick Recipe button hits.

Run with the CatGo desktop server running locally:

    pnpm desktop:serve                  # in one terminal
    python examples/quickbuild_demo.py  # in another
"""

from __future__ import annotations

import sys

import httpx


API_BASE = "http://localhost:8000/api"


def list_recipes(client: httpx.Client) -> list[dict]:
    resp = client.get(f"{API_BASE}/workflow/quickbuild/recipes")
    resp.raise_for_status()
    return resp.json()


def build_recipe(
    client: httpx.Client,
    recipe: str,
    material_id: str | None = None,
    name: str | None = None,
) -> dict:
    payload: dict[str, object] = {"recipe": recipe}
    if material_id is not None:
        payload["material_id"] = material_id
    if name is not None:
        payload["name"] = name
    resp = client.post(f"{API_BASE}/workflow/quickbuild", json=payload)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    with httpx.Client(timeout=30.0) as client:
        try:
            recipes = list_recipes(client)
        except httpx.ConnectError:
            print(
                "ERROR: cannot reach CatGo backend at", API_BASE,
                "— start the dev server first (pnpm desktop:serve).",
                file=sys.stderr,
            )
            return 1

        print(f"Available quickbuild recipes ({len(recipes)}):")
        for r in recipes:
            print(f"  {r['id']:<14s}  {r['label']:<60s}  "
                  f"{r['node_count']} nodes / {r['edge_count']} edges")

        # Build HER on Pt(111) as a worked example.
        print("\nBuilding HER on Pt(111) (mp-126) …")
        result = build_recipe(client, "HER", material_id="mp-126")
        if not result["ok"]:
            print(f"  failed: {result['message']}", file=sys.stderr)
            return 1
        print(f"  workflow_id = {result['workflow_id']}")
        print(f"  message     = {result['message']}")

        # Build a batch of recipes at once — pattern for high-throughput
        # screening across reactions on the same material.
        print("\nBuilding HER + OER + ORR on mp-126 in series:")
        for recipe in ("HER", "OER", "ORR"):
            r = build_recipe(client, recipe, material_id="mp-126",
                             name=f"{recipe}-mp126-demo")
            print(f"  {recipe:<6s} → {r['workflow_id']}")

        return 0


if __name__ == "__main__":
    raise SystemExit(main())
