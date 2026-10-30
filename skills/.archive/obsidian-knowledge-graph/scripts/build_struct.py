#!/usr/bin/env python3
"""Structural Graphify build over an Obsidian vault — NO LLM key needed.

Verified working on graphifyy 0.9.28. Produces a knowledge graph from the vault's
markdown structure (headings + [[wikilinks]]) and reports the "cleanup map":
orphans, hubs, duplicate files, community count. Stages a to_obsidian export to a
temp dir (does NOT touch the live vault) so the caller can copy it in after consent.

USAGE:
    python3 build_struct.py --vault /path/to/vault --stage /path/to/staging [--restore /path/to/vault/Graphify]

FLAGS:
    --vault   source vault root (default: ~/Documents/obsidian_maru_1)
    --stage   where to write graphify-out/ + obsidian/ staging (default: ~/graphify-builds/<name>)
    --restore optional: copy the staged obsidian/ into this dir (e.g. VAULT/Graphify)
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from graphify.extractors.markdown import extract_markdown
from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.export import to_obsidian, to_json


def main():
    ap = argparse.ArgumentParser()
    default_vault = Path.home() / "Documents" / "obsidian_maru_1"
    ap.add_argument("--vault", default=str(default_vault))
    ap.add_argument("--stage", default=None)
    ap.add_argument("--restore", default=None)
    args = ap.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    stage = Path(args.stage).expanduser().resolve() if args.stage else (
        Path.home() / "graphify-builds" / vault.name
    )
    (stage / "graphify-out").mkdir(parents=True, exist_ok=True)

    md_files = sorted(p for p in vault.rglob("*.md") if ".obsidian" not in str(p))
    print(f"Markdown files found: {len(md_files)}")

    nodes, edges = [], []
    for f in md_files:
        try:
            r = extract_markdown(f)
        except Exception as e:
            print(f"  ERR {f.name}: {e}")
            continue
        nodes += r.get("nodes", [])
        edges += r.get("edges", [])

    # dedup nodes by id (markdown extractor may emit dup file nodes)
    seen, ded = set(), []
    for n in nodes:
        if n["id"] not in seen:
            seen.add(n["id"])
            ded.append(n)
    nodes = ded

    extraction = {"nodes": nodes, "edges": edges, "input_tokens": 0, "output_tokens": 0}
    if not nodes:
        print("ERROR: no nodes extracted.")
        sys.exit(1)

    G = build_from_json(extraction, root=str(vault), directed=False)
    communities = cluster(G)

    deg = dict(G.degree())
    orphans = [n for n, d in deg.items() if d == 0]
    hubs = sorted(deg.items(), key=lambda x: -x[1])[:15]
    edge_types = Counter(e.get("relation", "?") for e in edges)

    # community sizes (cluster returns node -> list[int])
    members = defaultdict(list)
    for node, clist in communities.items():
        for c in (clist if isinstance(clist, (list, tuple)) else [clist]):
            members[c].append(node)
    csizes = Counter({c: len(m) for c, m in members.items()})

    # duplicate labels across G
    label_map = defaultdict(list)
    for nid, nd in G.nodes(data=True):
        label_map[nd.get("label", nid)].append(nid)
    dup_labels = {l: ids for l, ids in label_map.items() if len(ids) > 1}

    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, "
          f"{len(members)} communities")
    print(f"ORPHANS (degree 0): {len(orphans)}")
    for n in orphans[:50]:
        print(f"   - {G.nodes[n].get('label', n)}")
    print("TOP HUBS:")
    for n, d in hubs:
        print(f"   - {G.nodes[n].get('label', n)} (degree {d})")
    print(f"EDGE TYPES: {dict(edge_types)}")
    print(f"COMMUNITY COUNT: {len(members)}")
    print(f"DUPLICATE-LABEL GROUPS: {len(dup_labels)}")
    for l, ids in list(dup_labels.items())[:20]:
        print(f"   - {l}: {len(ids)}")
        for i in ids:
            print(f"        {G.nodes[i].get('source_file', '?')}")

    # save graph + stage obsidian export
    to_json(G, communities, str(stage / "graphify-out" / "graph.json"))
    n_notes = to_obsidian(G, communities, str(stage / "obsidian"))
    print(f"\nSTAGED Obsidian export: {n_notes} notes -> {stage / 'obsidian'}")

    summary = {
        "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
        "orphans": len(orphans), "communities": len(members),
        "edge_types": dict(edge_types),
        "duplicate_label_groups": len(dup_labels),
    }
    (stage / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"Summary -> {stage / 'summary.json'}")

    if args.restore:
        dst = Path(args.restore).expanduser().resolve()
        dst.mkdir(parents=True, exist_ok=True)
        import shutil
        for item in (stage / "obsidian").iterdir():
            if item.is_dir():
                shutil.copytree(item, dst / item.name, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst / item.name)
        print(f"RESTORED into {dst} (reversible: delete that folder)")


if __name__ == "__main__":
    main()
