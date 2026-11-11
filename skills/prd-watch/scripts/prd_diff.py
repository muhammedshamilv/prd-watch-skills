#!/usr/bin/env python3
"""Section-level diff of two markdown PRD snapshots.

Usage: prd_diff.py BASELINE.md CURRENT.md

Splits each file on markdown headings, normalises whitespace, and prints
a markdown summary of ADDED / REMOVED / MODIFIED sections with a unified
diff for each modified one. Exit code 0 = no changes, 1 = changes found.
"""
import difflib
import re
import sys

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def norm(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def sections(text: str) -> dict:
    out, path, key = {}, [], "(preamble)"
    out[key] = []
    for raw in text.splitlines():
        m = HEADING.match(raw)
        if m:
            level, title = len(m.group(1)), norm(m.group(2))
            path = path[: level - 1] + [title]
            key = " > ".join(p for p in path if p)
            base, n = key, 2
            while key in out:  # duplicate headings
                key = f"{base} ({n})"
                n += 1
            out[key] = []
            continue
        line = norm(raw)
        if line:
            out[key].append(line)
    return {k: v for k, v in out.items() if v or k != "(preamble)"}


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    with open(sys.argv[1], encoding="utf-8") as f:
        base = sections(f.read())
    with open(sys.argv[2], encoding="utf-8") as f:
        cur = sections(f.read())

    added = [k for k in cur if k not in base]
    removed = [k for k in base if k not in cur]
    modified = [k for k in cur if k in base and cur[k] != base[k]]

    if not (added or removed or modified):
        print("NO CHANGES")
        return 0

    print(f"# Diff: {len(added)} added, {len(removed)} removed, {len(modified)} modified sections\n")
    for k in added:
        print(f"## ADDED: {k}\n")
        print("\n".join(f"+ {l}" for l in cur[k]) + "\n")
    for k in removed:
        print(f"## REMOVED: {k}\n")
        print("\n".join(f"- {l}" for l in base[k]) + "\n")
    for k in modified:
        print(f"## MODIFIED: {k}\n")
        diff = difflib.unified_diff(base[k], cur[k], "baseline", "current", lineterm="", n=1)
        print("```diff\n" + "\n".join(diff) + "\n```\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
