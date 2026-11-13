#!/usr/bin/env python3
"""Cheap version pre-check for the daily prd-watch run.

The full `/prd-watch check` run is only needed when a PRD or the RFC has a new
Confluence version. daily-check.sh asks a small model for the current version
numbers, then uses this script to decide whether the full run can be skipped.

Usage:
  precheck.py ids FEATURE_DIR
      Print "<cloud_id> <page_id>..." (all RFCs, then all PRDs) for the version lookup prompt.
  precheck.py compare FEATURE_DIR VERSIONS_FILE
      Exit 0  = nothing changed; appends a short entry to today's report and
                updates last_checked_at in meta.json.
      Exit 10 = something changed, or the versions are missing/unreadable
                (run the full check).
  precheck.py save FEATURE_DIR VERSIONS_FILE
      After a successful full run, record the RFC versions seen, so the next
      pre-check can tell whether any RFC moved.

VERSIONS_FILE holds the model's output; the last line that parses as a JSON
object of {"page_id": version_number} is used.
"""
import datetime as dt
import json
import pathlib
import sys

CHANGED = 10


def load_versions(path):
    for line in reversed(pathlib.Path(path).read_text().splitlines()):
        line = line.strip().strip("`")
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "error" not in data and data and all(
            isinstance(v, int) for v in data.values()
        ):
            return {str(k): v for k, v in data.items()}
    return None


def rfcs_of(meta):
    """A feature has a list of RFCs ("rfcs"); old metadata has a single "rfc"."""
    return meta.get("rfcs") or [meta["rfc"]]


def main():
    cmd, fdir = sys.argv[1], pathlib.Path(sys.argv[2])
    meta_path = fdir / "meta.json"
    meta = json.loads(meta_path.read_text())
    state_path = fdir / "precheck.json"
    rfcs = rfcs_of(meta)
    rfc_ids = [r["page_id"] for r in rfcs]

    if cmd == "ids":
        print(meta["cloud_id"], *rfc_ids, *(p["page_id"] for p in meta["prds"]))
        return 0

    versions = load_versions(sys.argv[3])
    if cmd == "save":
        if versions and all(i in versions for i in rfc_ids):
            state = {"rfc_versions": {i: versions[i] for i in rfc_ids}}
            state_path.write_text(json.dumps(state) + "\n")
        return 0

    if cmd != "compare":
        sys.exit(f"unknown command {cmd}")
    if not versions or not state_path.exists():
        return CHANGED
    seen = json.loads(state_path.read_text()).get("rfc_versions", {})
    for i in rfc_ids:
        if i not in versions or versions[i] != seen.get(i):
            return CHANGED
    for p in meta["prds"]:
        if versions.get(p["page_id"]) != p["last_checked_version"]:
            return CHANGED

    # Nothing moved: write the short scheduled-run entry ourselves.
    now = dt.datetime.now(dt.timezone.utc)
    today = dt.date.today().isoformat()
    open_crs = []
    changes_path = fdir / "changes.json"
    if changes_path.exists():
        changes = json.loads(changes_path.read_text()).get("changes", [])
        open_crs = [c["id"] for c in changes if c.get("status") in ("open", "deferred")]
        waiting = sorted({c.get("change_file", "") for c in changes if c.get("status") == "in-change-rfc"} - {""})

    rows = "\n".join(
        f"| {p['title']} | v{p['baseline_version']} | v{versions[p['page_id']]} | no change since last check |"
        for p in meta["prds"]
    )
    rfc_list = "; ".join(f"{r['title']} v{versions[r['page_id']]} ({r['url']})" for r in rfcs)
    entry = (
        f"## {meta['feature']} — RFCs: {rfc_list}\n\n"
        f"Version pre-check at {now:%H:%M} UTC: no PRD or RFC edits since the last check. "
        "Full analysis skipped.\n\n"
        "| PRD | Baseline | Current | Status |\n|---|---|---|---|\n"
        f"{rows}\n\n"
    )
    if open_crs:
        entry += (
            f"Still open: {', '.join(open_crs)} (details in the last full report). "
            f"Draft change RFC: `change-rfcs/draft.md`. "
            f"Run `/prd-watch change-rfc {meta['feature']}` to freeze it as the next change RFC.\n\n"
        )
    for f in waiting:
        entry += f"Change RFC waiting to be published: `{f}`.\n\n"

    report = fdir / "reports" / f"{today}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    if not report.exists():
        report.write_text(f"# PRD drift report — {today}\n\n")
    with report.open("a") as fh:
        fh.write(entry)

    meta["last_checked_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
