#!/usr/bin/env python3
"""Turn a read-only Figma MCP response into a fingerprint and add it to a snapshot file.

Usage:
  figma_extract.py --kind text   SNAPSHOT.json NODE_ID DUMP_FILE   # DUMP = get_design_context output
  figma_extract.py --kind layout SNAPSHOT.json NODE_ID DUMP_FILE   # DUMP = get_metadata output
  figma_extract.py --missing     SNAPSHOT.json NODE_ID             # frame not found / no access

DUMP_FILE may be raw tool text or a harness-saved tool-result file.
SNAPSHOT.json accumulates {"f": {node_id: [hash, count, texts?]}, "missing": [], "sparse": []}
and is then fed to figma_state.py. Text is redacted before it is written.
"""
import hashlib
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figma_state import red  # noqa: E402  (single redaction rule set)


def load(path):
    raw = open(path, encoding="utf-8").read()
    try:  # harness-saved result: JSON list/dict with text parts
        j = json.loads(raw)
        parts = []
        def walk(x):
            if isinstance(x, str):
                parts.append(x)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
            elif isinstance(x, dict):
                for k in ("text", "content", "value"):
                    if k in x:
                        walk(x[k])
        walk(j)
        if parts:
            return "\n".join(parts)
    except ValueError:
        pass
    return raw


def texts_from_code(code):
    """Group <p> runs by the nearest preceding data-node-id; one string per text node."""
    groups, order, cur = {}, [], None
    token = re.compile(r'data-node-id="([^"]+)"|<p\b[^>]*>(.*?)</p>', re.S)
    for m in token.finditer(code):
        if m.group(1):
            cur = m.group(1)
            continue
        t = m.group(2)
        t = re.sub(r'\{\s*["`\']([^"`\']*)["`\']\s*\}', r"\1", t)  # {"text"} JSX literals
        t = re.sub(r"<br\s*/?>", " ", t)
        t = re.sub(r"<[^>]+>", "", t)
        t = html.unescape(t)
        if cur not in groups:
            groups[cur] = []
            order.append(cur)
        groups[cur].append(t)
    out = []
    for k in order:
        s = re.sub(r"\s+", " ", " ".join(groups[k])).strip()
        if s:
            out.append(red(s))
    return list(dict.fromkeys(out))


def layout_from_xml(xml):
    struct = [f"{m.group(1)}:{m.group(2)}" for m in
              re.finditer(r'<\s*([a-z-]+)\b[^>]*?\bname="([^"]*)"', xml)]
    return struct


def main():
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == "--missing":
        snap_path, nid = a[1], a[2]
        snap = json.load(open(snap_path)) if os.path.exists(snap_path) else {"f": {}, "missing": [], "sparse": []}
        snap["missing"].append(nid)
        json.dump(snap, open(snap_path, "w"), ensure_ascii=False)
        return 0
    if len(a) != 5 or a[0] != "--kind" or a[1] not in ("text", "layout"):
        print(__doc__)
        return 2
    kind, snap_path, nid, dump = a[1], a[2], a[3], a[4]
    body = load(dump)
    snap = json.load(open(snap_path)) if os.path.exists(snap_path) else {"f": {}, "missing": [], "sparse": []}
    if kind == "text":
        if "data-node-id" not in body:  # sparse/metadata-only response
            snap["sparse"].append(nid)
            json.dump(snap, open(snap_path, "w"), ensure_ascii=False)
            print(json.dumps({"node": nid, "sparse": True}))
            return 0
        texts = texts_from_code(body)
        h = hashlib.sha256(json.dumps(sorted(texts), ensure_ascii=False).encode()).hexdigest()[:16]
        snap["f"][nid] = [h, len(texts), texts]
        print(json.dumps({"node": nid, "texts": len(texts)}))
    else:
        struct = layout_from_xml(body)
        h = hashlib.sha256(json.dumps(struct, ensure_ascii=False).encode()).hexdigest()[:16]
        snap["f"][nid] = [h, len(struct)]
        print(json.dumps({"node": nid, "elements": len(struct)}))
    json.dump(snap, open(snap_path, "w"), ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
