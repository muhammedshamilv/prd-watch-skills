#!/usr/bin/env python3
"""Extract Figma frame links from a PRD (markdown) with requirement context.

Usage: figma_links.py PRD_ID FILE [FILE...]
  FILE: plain markdown, or a saved getConfluenceContent JSON result
        (data.body.value is used).

Prints JSON list: [{"key": "<fileKey>:<nodeId>", "file_key", "node_id",
  "file_name", "url", "prd": PRD_ID, "section", "context", "label"}]
Duplicate frames within one run are merged (refs list).
"""
import json
import re
import sys
from urllib.parse import unquote

LINK = re.compile(r"\[([^\]]*)\]\((https://www\.figma\.com/(?:design|file)/([A-Za-z0-9]+)/([^?)\s]*)\?[^)\s]*node-id=([0-9]+-[0-9]+)[^)\s]*)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*)")


def load(path):
    raw = open(path, encoding="utf-8").read()
    try:
        return json.loads(raw)["data"]["body"]["value"]
    except (ValueError, KeyError, TypeError):
        return raw


def clean(s):
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)  # drop link targets
    s = re.sub(r"[*_`|\\]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    prd = sys.argv[1]
    frames = {}
    for path in sys.argv[2:]:
        section = ""
        for line in load(path).splitlines():
            h = HEADING.match(line)
            if h:
                section = clean(h.group(1))
            for m in LINK.finditer(line):
                label, url, fkey, fname, nid = m.groups()
                node = nid.replace("-", ":")
                key = f"{fkey}:{node}"
                ctx = clean(line.split("(links to design")[0].split(m.group(0))[0])[:200]
                ref = {"prd": prd, "section": section, "context": ctx, "label": clean(label)}
                f = frames.setdefault(key, {
                    "key": key, "file_key": fkey, "node_id": node,
                    "file_name": unquote(fname).replace("-", " "),
                    "url": url, "refs": []})
                if ref not in f["refs"]:
                    f["refs"].append(ref)
    print(json.dumps(list(frames.values()), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
