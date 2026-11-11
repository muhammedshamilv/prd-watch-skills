---
name: prd-watch
description: Detect changes to one or more Confluence PRDs (Confluence only; Figma is the separate figma-watch skill) made after the RFC was written, map each change to the affected RFC section, and write a dated markdown change-request report. Use when the user says "prd-watch", "check PRD drift", "did the PRD change", or runs the daily scheduled check. Can propose RFC edits for each PRD change and apply them to the Confluence RFC only after the user confirms each one. Subcommands - init, check, rfc-update, accept, coverage, list.
---

# PRD Watch

Purpose: catch PRD edits made after the RFC was written, so they go back to the business as change requests and are not found later by QA.

One **feature** = one RFC + one or more PRD pages. State lives in `~/prd-watch/<feature>/`:

```
meta.json        # schema below
changes.json     # every detected change, its RFC proposal and the user's decision (source of truth)
open-changes.md  # human-readable view of changes.json, regenerated each run
reports/YYYY-MM-DD.md
```

Confluence keeps full page history, so we store only **version numbers**, not copies of the PRDs. No PRD text is written to disk except quotes in reports.

`meta.json`:
```json
{
  "feature": "my-feature",
  "cloud_id": "<your-site>.atlassian.net",
  "rfc": { "page_id": "<rfc-page-id>", "title": "...", "url": "..." },
  "prds": [
    {
      "page_id": "1055031440",
      "title": "...",
      "url": "...",
      "baseline_version": 31,
      "baseline_date": "2026-08-11",
      "last_checked_version": 31
    }
  ],
  "last_checked_at": "2026-11-08T10:15:00Z"
}
```

## Confluence operations (Atlassian MCP)

Load via ToolSearch: `mcp__claude_ai_Atlassian_MCP__getConfluenceContent`, `mcp__claude_ai_Atlassian_MCP__executeRead`. Pass `cloud_id` from meta.json as `cloudId`.

| Need | Call |
|---|---|
| Current version number | `getConfluenceContent(content_id, detail="summary")` → `metadata.version.number` |
| Version list (author, time) | `executeRead name=listConfluenceContentVersions inputs={contentId, limit}` with `responseFields=["results.number","results.createdAt","results.authorId"]` |
| Diff baseline → current | `executeRead name=diffConfluenceContentVersions inputs={contentId, from_version, to_version, content_format:"markdown"}` |
| Old version body | `executeRead name=getConfluenceContentVersion inputs={contentId, versionNumber, content_format:"markdown"}` |
| RFC body | `getConfluenceContent(content_id, detail="full", content_format="markdown")` |
| Author name | `getPeopleInfo` (optional; otherwise show accountId) |

If an operation name fails, run `discover` once with "confluence page version diff" and use what it returns. If the connector is not authenticated, write a report saying so and stop. Do not guess at content.

## Figma designs

Figma is handled by the separate **`figma-watch`** skill (on demand, because of Figma's MCP call quota). This skill makes **no Figma calls**.
In `check`: if a PRD diff adds, removes or changes a `figma.com` link, list it under **Design links changed** in the report and add: "Run `/figma-watch check <feature>` to compare the designs."

## changes.json

```json
{"changes": [{
  "id": "CR-1",                      // stable; never reused
  "prd_page_id": "1376419842", "prd_title": "...",
  "versions": "4->6",                // baseline -> version where it was seen
  "type": "NEW|CHANGED|REMOVED",     // COSMETIC changes are not stored
  "prd_section": "FR-RI-02", "before": "<short quote>", "now": "<short quote>",
  "rfc_sections": ["5. API Contract"],
  "flags": [],
  "proposal": {                      // drafted by check; plain text, no Confluence markup
    "rfc_section": "5. API Contract",
    "action": "replace|insert_after|delete",
    "anchor": "<exact current RFC text the edit attaches to>",
    "new_text": "<text to put in the RFC>",
    "rationale": "<one line>",
    "drafted_against_rfc_version": 73
  },
  "status": "open|rfc-updated|rejected|deferred",
  "decided_at": null, "rfc_version_after": null, "note": ""
}]}
```

Statuses:
- `open`: detected, no decision yet.
- `deferred`: the user chose "not now"; ask again next `rfc-update`.
- `rejected`: the user said **don't** update the RFC. Never edit the RFC for it, and never propose it again unless a later PRD version changes the same section again (then create a **new** CR id). It stays listed in reports as "RFC intentionally not updated", which is evidence for the change-request conversation.
- `rfc-updated`: applied; `rfc_version_after` records the RFC version.

## Writing to the RFC (safety rules, mandatory)

The only command that may write to Confluence is `rfc-update`, and only in an interactive session.
- **Never** write during `check`, scheduled runs, `coverage`, `list` or `accept`. These are read-only.
- **One explicit confirmation per change**, given by the user in this conversation (AskUserQuestion). A confirmation covers only that CR. No batch "apply all" unless the user types that themselves.
- Only the RFC page in `meta.json` → `rfc.page_id`. Never edit a PRD or any other page.
- Write operation: `executeWrite name=updateConfluenceContent` (run `discover "update confluence page content"` first to get its exact inputs; follow `getContentFormatGuide toolName=updateConfluencePage`). Body format **HTML**.
- **Edit surgically.** Re-read the RFC as HTML immediately before writing (`getConfluenceContent detail=full content_format=html`). Change only the block(s) that contain the anchor. Keep everything else byte-for-byte: `data-local-id`, `data-colwidth`, table layout, macros/extensions, links, inline comments. If the anchor isn't found exactly once, or the page contains structures the format guide says may not round-trip, **stop** and show the user the proposal to paste manually.
- **Version guard.** If the RFC version is newer than `drafted_against_rfc_version`, re-draft the proposal against the current text and ask again. Don't apply a stale proposal.
- Version message: `prd-watch <CR-id>: <PRD title> v<from>→v<to>, <one line>`.
- **Verify after every write.** Run `diffConfluenceContentVersions(rfc, before, after)` and check that only the intended lines changed. If anything else changed, tell the user straight away and offer to restore the previous version's body. Don't continue with other CRs until it's resolved.
- Flags stay visible. For **Mandatory human review** or **Needs Legal/Compliance review** CRs, show the flag in the question and add to the RFC text: "(Pending <Compliance|human> review)". The RFC states what will be built; it never states a legal or regulatory conclusion.
- Don't translate French customer-facing terms; quote them as the PRD writes them.

## Data rules (organisation policy, mandatory)

- Quote only the minimum PRD text needed. If any quoted text has customer PII, account numbers, wallet balances, transaction references, phone numbers, API keys, PINs, USSD short codes or credentials, replace it with `[REDACTED]` and say so in the report.
- Never state a legal or regulatory conclusion. If a change touches data protection, AML/CFT or KYC, flag it **"Needs Legal/Compliance review"**.
- If a change touches payment reconciliation, ledger balances or float management, flag it **"Mandatory human review"**.
- Do not translate French customer-facing financial terms informally. Quote them as written and flag them for Product/Localisation if their meaning matters.
- Write in UK English.

## Subcommands

### `init <feature> <rfc-url> <prd-url>...`
1. Get the RFC's version list. Its **creation time** (version 1) is the default baseline point.
2. For each PRD, list its versions and pick the newest version created **before** the RFC's creation. If the PRD was created after the RFC, use version 1 and note that.
3. If any PRD has versions after the baseline, say so immediately: those are changes the RFC has not yet seen.
4. Write `meta.json`. Tell the user to add this line to the RFC Overview: `Based on PRDs: <title> v<N>, ... (as of <date>).` Do not edit the RFC yourself.

### `check [feature|all]` (default: all)
For each feature, for each PRD:
1. Get the current version. If it equals `last_checked_version` and the PRD has no items in `open-changes.md`, record `no change, v<N>` and move on.
2. Otherwise run `diffConfluenceContentVersions(from=baseline_version, to=current)`. This diffs against the **baseline**, not the previous day, so changes stay listed until they are accepted.
3. Get the version list between the baseline and the current version for who changed it and when.
4. Fetch the RFC (once per run) and map each change to RFC sections.
5. Classify each diff hunk using only the quoted diff text, and never invent requirements:
   - **NEW**: a requirement not in the baseline → change request
   - **CHANGED**: behaviour differs from the baseline → change request
   - **REMOVED**: the RFC may contain work that is no longer needed
   - **COSMETIC**: wording, typos or formatting with no behavioural effect → one line, no change request
6. For each non-cosmetic change, name the affected RFC section(s). If the RFC already covers it, mark it **Already covered**.
7. Merge into `changes.json`: same PRD section and same change → keep the existing entry and status; new → next CR id, `status: open`. A `rejected` entry is not re-opened unless the PRD text for that section changed again (that's a new CR).
8. For each `open` or `deferred` CR without a current proposal, **draft** one (`proposal`) against the current RFC text: the smallest edit that makes the RFC match the PRD, in the RFC's own style. Draft only; **do not write to Confluence**.
9. Append to `reports/<today>.md` (one report per day for all features). Regenerate `open-changes.md` from `changes.json`. Update `last_checked_version` and `last_checked_at`. If any CR is open, end the report with: "Run `/prd-watch rfc-update <feature>` to review the proposed RFC edits." 
10. Scheduled runs: if every PRD is unchanged, keep the report to one line per PRD.

### `rfc-update <feature> [CR-id...]`
Interactive only; refuse in a scheduled or `-p` run. Goes through `open` and `deferred` CRs (or the given ids), one at a time:
1. Re-read the RFC (version guard above). Re-draft the proposal if the RFC changed.
2. Show the CR: PRD before/now quotes, flags, RFC section, and the proposed edit as **Current RFC text** → **Proposed RFC text**, plus a one-line rationale.
3. Ask with AskUserQuestion: **Apply** · **Edit wording** (the user gives text; show the revised proposal and ask again) · **Reject (don't update RFC)** · **Not now**.
4. Apply → write per the safety rules, verify the diff, set `status: rfc-updated`, `rfc_version_after`, `decided_at`. Reject → `status: rejected`, `decided_at`, nothing written. Not now → `status: deferred`.
5. At the end, summarise applied, rejected and deferred, with the RFC version link. If every CR of a PRD is now `rfc-updated` or `rejected`, offer `accept <feature> <prd-page-id>` to move that PRD's baseline (it needs its own confirmation).

### `accept <feature> [prd-page-id|all]`
Use after the business has accepted the change request and the RFC has been updated. Requires explicit confirmation from the user in the conversation; never runs in a scheduled run. Sets `baseline_version` to the current version (and `baseline_date`) for the given PRD(s) and clears their items from `open-changes.md`.

### `coverage <feature>`
One-off traceability check against the baseline versions. Write a table to `reports/<today>-coverage.md`: `ID | PRD | Requirement (short quote) | RFC section | Status (Covered / Partial / Missing)`.

### `list`
For each feature, list each PRD with its baseline version, current version and number of open changes.

## Report format

```markdown
# PRD drift report — <YYYY-MM-DD>

## <feature> — RFC: <title> (<link>)

| PRD | Baseline | Current | Status |
|---|---|---|---|
| <title> | v31 (2026-08-11) | v33 | 2 changes |

### CR-1 · NEW · <short title>
**PRD:** <title> · section <heading> · v31 → v33, edited <time> by <author> · [Confluence compare](<diff.compareUrl>)
**Before:**
> <quote or "— not present —">
**Now:**
> <quote>
**Affects RFC:** <section(s)> — <one line on the impact>
**Flags:** <Needs Legal/Compliance review | Mandatory human review | none>
**Proposed RFC edit** (not applied; run `rfc-update`): <section> · <replace|insert|delete>
> Current: <anchor>
> Proposed: <new_text>
**Status:** <open | deferred | rfc-updated in v<N> | rejected on <date>: RFC intentionally not updated>
**Draft CR note:**
> The PRD "<title>" was updated on <date>, after the RFC was written (baseline v31, <date>). <What changed>. This is outside the agreed scope and is raised as a change request. Please confirm priority and timeline impact.

### Removed
...
### Cosmetic (no action)
- <PRD> · <section>: <one line>
```
