#!/usr/bin/env python3
"""Pick which Figma frames to read this run, within a call budget.

Usage:
  figma_plan.py FEATURE_DIR --mode baseline|check [--tier daily|weekly|all]
                [--file <fileKey or name>] [--kinds text,layout] [--max-calls N]

Reads FEATURE_DIR/figma-links.json and FEATURE_DIR/figma.json.
  baseline : frames that have no baseline yet for a kind.
  check    : baselined frames, least recently checked first.
Each frame costs one call per kind. Stops at --max-calls (default 40).
Prints {"calls": n, "remaining": m, "batches": [{"file_key", "file_name", "kind", "node_ids": [...]}]}
"""
import argparse
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feature_dir")
    ap.add_argument("--mode", choices=["baseline", "check"], required=True)
    ap.add_argument("--tier", choices=["daily", "weekly", "all"], default="daily")
    ap.add_argument("--file")
    ap.add_argument("--kinds", default="text")
    ap.add_argument("--max-calls", type=int, default=40)
    a = ap.parse_args()

    links = json.load(open(os.path.join(a.feature_dir, "figma-links.json")))
    sp = os.path.join(a.feature_dir, "figma.json")
    frames = json.load(open(sp))["frames"] if os.path.exists(sp) else {}
    kinds = [k.strip() for k in a.kinds.split(",") if k.strip()]

    cands = []
    for f in links:
        if a.tier != "all" and f.get("tier", "daily") != a.tier:
            continue
        if a.file and a.file not in (f["file_key"], f["file_name"]):
            continue
        st = frames.get(f["key"], {})
        for k in kinds:
            has = k in st
            if a.mode == "baseline" and has:
                continue
            if a.mode == "check" and not has:
                continue
            last = st.get(f"{k}_last", {}).get("at") or st.get(k, {}).get("at") or ""
            cands.append((last, f["file_key"], f["file_name"], k, f["node_id"]))

    cands.sort()  # oldest checked first; never-checked ("") first
    pick, rest = cands[: a.max_calls], cands[a.max_calls:]
    batches = {}
    for _, fk, fn, k, nid in pick:
        b = batches.setdefault((fk, k), {"file_key": fk, "file_name": fn, "kind": k, "node_ids": []})
        b["node_ids"].append(nid)
    print(json.dumps({"calls": len(pick), "remaining": len(rest),
                      "batches": list(batches.values())}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
