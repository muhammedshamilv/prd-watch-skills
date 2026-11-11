#!/usr/bin/env python3
"""Store / compare Figma frame fingerprints (built by figma_extract.py from read-only Figma tools).

Usage:
  figma_state.py STATE.json FILE_KEY SNAPSHOT.json --kind text|layout --mode baseline|check [--force]

  baseline : store as baseline (frames already baselined for that kind are kept unless --force).
  check    : compare with baseline. Prints
             {"changed": {id: {...}}, "missing": [...], "sparse": [...], "unchanged": n}
             text kind  -> per changed frame: text_added, text_removed, baseline_at, first_seen_changed
             layout kind-> per changed frame: elements [baseline, now], baseline_at, first_seen_changed
             Exit 1 if anything changed or went missing.
Text is redacted (emails, phones, short codes, long ids) before it is stored.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\+?\d[\d \-]{7,}\d")
LONGNUM = re.compile(r"(?<![\d,.])\d{6,}(?![\d,.]|\s*GNF)")
SHORTCODE = re.compile(r"(?i)\b(at|au|call|appelez|composez|dial|ussd)\s*[*#]?\d{3,6}#?")


def red(t):
    t = EMAIL.sub("[REDACTED-EMAIL]", t)
    t = PHONE.sub("[REDACTED-PHONE]", t)
    t = SHORTCODE.sub(lambda m: m.group(1) + " [REDACTED-NUMBER]", t)
    return LONGNUM.sub("[REDACTED-ID]", t)  # account/transaction-like ids


def main():
    a = sys.argv[1:]
    force = "--force" in a
    a = [x for x in a if x != "--force"]
    if (len(a) != 7 or a[3] != "--kind" or a[4] not in ("text", "layout")
            or a[5] != "--mode" or a[6] not in ("baseline", "check")):
        print(__doc__)
        return 2
    state_path, fkey, snap_path, _, kind, _, mode = a
    snap = json.load(open(snap_path, encoding="utf-8"))
    state = json.load(open(state_path)) if os.path.exists(state_path) else {"version": 2, "frames": {}}
    frames = state["frames"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if mode == "baseline":
        n = 0
        for nid, v in snap.get("f", {}).items():
            fr = frames.setdefault(f"{fkey}:{nid}", {})
            if kind in fr and not force:
                continue
            entry = {"hash": v[0], "count": v[1], "at": now}
            if kind == "text":
                entry["texts"] = [red(t) for t in v[2]]
            fr[kind] = entry
            fr.pop(f"{kind}_first_seen_changed", None)
            n += 1
        out = {"baselined": n, "missing": snap.get("missing", []), "sparse": snap.get("sparse", [])}
    else:
        changed, unchanged = {}, 0
        for nid, v in snap.get("f", {}).items():
            fr = frames.get(f"{fkey}:{nid}", {})
            base = fr.get(kind)
            if not base:
                continue
            fr[f"{kind}_last"] = {"hash": v[0], "at": now}
            if v[0] == base["hash"]:
                fr.pop(f"{kind}_first_seen_changed", None)
                unchanged += 1
                continue
            first = fr.setdefault(f"{kind}_first_seen_changed", now)
            d = {"baseline_at": base["at"], "first_seen_changed": first}
            if kind == "text":
                cur = [red(t) for t in v[2]]
                d["text_added"] = [t for t in cur if t not in base["texts"]]
                d["text_removed"] = [t for t in base["texts"] if t not in cur]
            else:
                d["elements"] = [base["count"], v[1]]
            changed[nid] = d
        for nid in snap.get("missing", []):
            frames.setdefault(f"{fkey}:{nid}", {}).setdefault("missing_since", now)
        out = {"changed": changed, "missing": snap.get("missing", []),
               "sparse": snap.get("sparse", []), "unchanged": unchanged}

    with open(state_path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(state_path + ".tmp", state_path)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if mode == "check" and (out["changed"] or out["missing"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
