---
name: prd-watch
description: Detect changes to one or more Confluence PRDs (Confluence only; Figma is the separate figma-watch skill) made after the RFC was written, map each change to the affected section of the feature's RFC(s) (one or more), and write a dated markdown change-request report. Use when the user says "prd-watch", "check PRD drift", "did the PRD change", or runs the daily scheduled check. Can propose RFC edits for each PRD change and apply them to a Confluence RFC only after the user confirms each one. Default flow: the base RFC is never edited; PRD changes go into a markdown change-RFC file that the user publishes as a new RFC. Subcommands - init, set-base-rfc, add-rfc, add-prd, check, change-rfc, rfc-update, accept, coverage, list.
---

# PRD Watch

Purpose: catch PRD edits made after the RFC was written, so they go back to the business as change requests and are not found later by QA.

One **feature** = one or more RFC pages + one or more PRD pages. A feature often starts with one RFC and gets more later (for example a follow-up RFC for a set of PRD changes). State lives in `~/prd-watch/<feature>/`:

```
meta.json        # schema below
changes.json     # every detected change, its RFC proposal and the user's decision (source of truth)
open-changes.md  # human-readable view of changes.json, regenerated each run
reports/YYYY-MM-DD.md
change-rfcs/draft.md                       # open CRs not yet in a change RFC; refreshed by every check
change-rfcs/<feature>-change-NN-YYYY-MM-DD.md  # frozen by change-rfc; the user publishes it as a new RFC page
```

## Base RFC and change RFCs (default flow)

- The **base RFC** (`role: "base"`) is the RFC written against the PRD baselines. It is **not edited** for PRD changes.
- PRD changes found after it go into a **change RFC**: a markdown file in the same Engineering Specification layout (`templates/change-rfc.md`) holding **only** the changes, numbered 01, 02, … per feature. The user creates it in Confluence as a new RFC page and registers it with `add-rfc --change NN`. That page gets `role: "change"`.
- Reading order for engineers: base RFC, then change RFCs in number order. A later change RFC wins where they overlap.
- When the user consolidates everything into a new base RFC, `set-base-rfc` switches the base; older RFCs become `role: "superseded"`.
- `rfc-update` (editing an RFC page in place) still exists for small fixes to a change RFC, but it is not the default for PRD changes.

Confluence keeps full page history, so we store only **version numbers**, not copies of the PRDs. No PRD text is written to disk except quotes in reports.

`meta.json`:
```json
{
  "feature": "my-feature",
  "cloud_id": "<your-site>.atlassian.net",
  "rfcs": [
    {
      "page_id": "<rfc-page-id>",
      "title": "...",
      "url": "...",
      "created": "2026-08-24",
      "last_checked_version": 73,
      "role": "base",                // base | change | superseded
      "change_no": null,             // 1, 2, ... for role "change"
      "change_file": null,           // change-rfcs/... file it was published from
      "crs": [],                     // CR ids this RFC page carries (role "change")
      "covers": "optional one line: what this RFC is for"
    }
  ],
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

Older metadata has a single `"rfc": {...}` object. Treat it as a one-item `rfcs` list, and write it back as `rfcs` the next time you save `meta.json`.

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
  "rfc_sections": ["My Feature RFC › 5. API Contract"],   // "<RFC title> › <section>"
  "flags": [],
  "proposal": {                      // drafted by check; plain text, no Confluence markup
    "rfc_page_id": "<rfc-page-id>",    // which RFC in meta.rfcs this edit goes to
    "rfc_section": "5. API Contract",
    "action": "replace|insert_after|delete",
    "anchor": "<exact current RFC text the edit attaches to>",
    "new_text": "<text to put in the RFC>",
    "rationale": "<one line>",
    "drafted_against_rfc_version": 73   // version of rfc_page_id
  },
  "target_page": null,               // optional: set when the user sends the CR to a different listed RFC than first proposed
  "status": "open|rfc-updated|rejected|deferred",
  "decided_at": null, "rfc_version_after": null, "note": ""
}]}
```

Statuses:
- `open`: detected, no decision yet.
- `in-change-rfc`: frozen into a change-RFC file (`change_file`), waiting for the user to publish it and run `add-rfc --change`.
- `deferred`: the user chose "not now"; ask again next `rfc-update`.
- `rejected`: the user said **don't** update the RFC. Never edit the RFC for it, and never propose it again unless a later PRD version changes the same section again (then create a **new** CR id). It stays listed in reports as "RFC intentionally not updated", which is evidence for the change-request conversation.
- `rfc-updated`: in an RFC page (a published change RFC, or an in-place `rfc-update`); `proposal.rfc_page_id` and `rfc_version_after` record where.

## Writing to the RFC (safety rules, mandatory)

The only command that may write to Confluence is `rfc-update`, and only in an interactive session.
- **Never** write during `check`, scheduled runs, `coverage`, `list` or `accept`. These are read-only.
- **One explicit confirmation per change**, given by the user in this conversation (AskUserQuestion). A confirmation covers only that CR. No batch "apply all" unless the user types that themselves.
- Only RFC pages listed in `meta.json` → `rfcs`. Never edit a PRD or any other page. If the user names a page that isn't listed, ask whether to add it with `add-rfc` first.
- Write operation: `executeWrite name=updateConfluenceContent` (run `discover "update confluence page content"` first to get its exact inputs; follow `getContentFormatGuide toolName=updateConfluencePage`). Body format **HTML**.
- **Edit surgically.** Re-read the RFC as HTML immediately before writing (`getConfluenceContent detail=full content_format=html`). Change only the block(s) that contain the anchor. Keep everything else byte-for-byte: `data-local-id`, `data-colwidth`, table layout, macros/extensions, links, inline comments. If the anchor isn't found exactly once, or the page contains structures the format guide says may not round-trip, **stop** and show the user the proposal to paste manually.
- **No write operation available.** If `discover` returns no Confluence page-update operation (the connector can be read-only), don't guess an operation name. Write the content to `~/prd-watch/<feature>/paste-<page_id>-<slug>.md`, one block per target heading, tell the user to paste it, leave the CR `open`, and verify with a version diff once they say it's pasted.
- **Version guard.** If the target RFC (`proposal.rfc_page_id`) is newer than `drafted_against_rfc_version`, re-draft the proposal against the current text and ask again. Don't apply a stale proposal.
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

### `init <feature> --rfc <rfc-url>... --prd <prd-url>...`
(The older form `init <feature> <rfc-url> <prd-url>...`, with exactly one RFC first, still works.)
1. Get each RFC's version list. The **earliest RFC creation time** (version 1) is the default baseline point.
2. For each PRD, list its versions and pick the newest version created **before** the RFC's creation. If the PRD was created after the RFC, use version 1 and note that.
3. If any PRD has versions after the baseline, say so immediately: those are changes the RFC has not yet seen.
4. Write `meta.json` with every RFC in `rfcs` (`last_checked_version` = current version). Tell the user to add this line to each RFC's Overview: `Based on PRDs: <title> v<N>, ... (as of <date>).` Do not edit the RFC yourself.

### `add-rfc <feature> <rfc-url> [--change NN] [covers text]`
Adds another RFC to the feature. Read-only on Confluence.
With `--change NN` it registers the published page for change-RFC file NN: set `role: "change"`, `change_no`, `change_file`, `crs` (from the file). Then **verify**: read the page as markdown and check that each CR's content is there (endpoints, fields, flows, error cases, flags, "(Pending … review)" markers, open points). Report what is missing and anything on the page that breaks the data rules (real-looking customer or taxpayer identifiers, transaction references, tokens or credentials). Mark each CR whose content is present `rfc-updated` with `proposal.rfc_page_id` and `rfc_version_after`; leave the others `in-change-rfc` and say why.
Without `--change`, the page is added with `role: "change"` if it isn't the first RFC, else `"base"`.
1. Read the page (`detail=summary`) to get its id, title and current version. Refuse if it's a PRD already listed in `prds`.
2. Append it to `rfcs` with `created`, `last_checked_version` = current version and an optional `covers` line.
3. Don't move any PRD baseline. Open CRs keep their proposals; when it fits, offer to re-target one to the new RFC (`rfc-update` handles that).
4. Update `precheck.json` → `rfc_versions` with the new page id and version, if that file exists.

### `set-base-rfc <feature> <rfc-url>`
Makes this RFC the base (adds it to `rfcs` first if needed). Read-only on Confluence. Ask the user to confirm (AskUserQuestion) and show the effect:
- The current base and every change RFC become `role: "superseded"` (kept for history, still read by `check` for coverage).
- For every CR that is `rfc-updated`, `in-change-rfc` or `open`, read the new base and say whether it carries it. Don't change statuses on a guess.
- Ask separately whether to move PRD baselines to their current versions (this is `accept`, with its own confirmation). Change-RFC numbering continues; it doesn't restart.

### `change-rfc <feature> [CR-id...]`
Freezes the change requests into a new numbered change-RFC file. Local only; **never** writes to Confluence. Allowed interactively; scheduled runs only refresh `draft.md` (see `check`).
1. Pick the CRs: the given ids, else every `open` and `deferred` CR. If none, say so and stop.
2. Read the base RFC and any existing change RFCs (current versions) for the "current flow" and to avoid repeating what is already specified.
3. Fill `templates/change-rfc.md` (in this skill's folder): next `change_no` (two digits), base RFC title, version and link, CR ids, PRD versions, and a merged view of the CRs per section. Keep sections that don't apply with "No change." Every flagged CR keeps its flag and its "(Pending <human|Compliance> review)" marker in the text. Put unanswered PRD questions under Key Design Decisions as "Open point". List every CR in section 9.
4. Data rules apply in full: no real customer or taxpayer identifiers, transaction references, tokens or credentials. Sample payloads use obvious placeholders (`<code_nif>`, `<reference_id>`). Quote French field names and customer-facing terms as the PRD writes them.
5. Write `change-rfcs/<feature>-change-NN-<today>.md`. Set those CRs to `in-change-rfc` with `change_file`. Clear them from `draft.md`.
6. Tell the user: create a new Confluence page from this file (suggested title `<base RFC title> — Change RFC NN`; Confluence converts pasted markdown), then run `/prd-watch add-rfc <feature> <page-url> --change NN`.

### `add-prd <feature> <prd-url>`
Adds another PRD. Its baseline is the newest version created before the earliest RFC, or version 1 if the PRD is newer (say so).

### `check [feature|all]` (default: all)
For each feature, for each PRD:
1. Get the current version. If it equals `last_checked_version` and the PRD has no items in `open-changes.md`, record `no change, v<N>` and move on. Also get every RFC's current version; if an RFC moved, re-check open CRs whose proposal targets it (version guard), and note any RFC edit that already covers an open CR.
2. Otherwise run `diffConfluenceContentVersions(from=baseline_version, to=current)`. This diffs against the **baseline**, not the previous day, so changes stay listed until they are accepted.
3. Get the version list between the baseline and the current version for who changed it and when.
4. Fetch every RFC in `rfcs` (each once per run) and map each change to sections across all of them. Use `covers` to pick the best RFC when more than one fits.
5. Classify each diff hunk using only the quoted diff text, and never invent requirements:
   - **NEW**: a requirement not in the baseline → change request
   - **CHANGED**: behaviour differs from the baseline → change request
   - **REMOVED**: the RFC may contain work that is no longer needed
   - **COSMETIC**: wording, typos or formatting with no behavioural effect → one line, no change request
6. For each non-cosmetic change, name the affected RFC and section(s), as `<RFC title> › <section>`. If any RFC already covers it, mark it **Already covered** and say which.
7. Merge into `changes.json`: same PRD section and same change → keep the existing entry and status; new → next CR id, `status: open`. A `rejected` entry is not re-opened unless the PRD text for that section changed again (that's a new CR).
8. For each `open` or `deferred` CR without a current proposal, **draft** one (`proposal`) against the current text of the RFC that best fits (set `rfc_page_id`): the smallest edit that makes the RFC match the PRD, in the RFC's own style. Draft only; **do not write to Confluence**.
9. Append to `reports/<today>.md` (one report per day for all features). Regenerate `open-changes.md` from `changes.json`. Update `last_checked_version` (PRDs and RFCs) and `last_checked_at`. If any CR is `open` or `deferred`, regenerate `change-rfcs/draft.md` with them (same template and rules as `change-rfc`, number shown as "NN (draft)") and end the report with: "Draft change RFC updated: `change-rfcs/draft.md`. Run `/prd-watch change-rfc <feature>` to freeze it as the next change RFC." If a CR is `in-change-rfc`, add: "Change RFC NN is waiting to be published: `<change_file>`." 
10. Scheduled runs: if every PRD is unchanged, keep the report to one line per PRD.

Scheduled runs go through `scripts/daily-check.sh`. A Haiku pre-check fetches only the version numbers, and `scripts/precheck.py` compares them with `meta.json` and `precheck.json` (the last version seen of each RFC). If nothing moved, the script writes the short report itself and this skill is not invoked. Otherwise the full `check` runs on Sonnet (`PRD_WATCH_MODEL` overrides it). `precheck.json` holds `rfc_versions`, one entry per RFC page id.

### `rfc-update <feature> [CR-id...]`
For small in-place fixes to an RFC page (usually a change RFC). PRD changes normally go through `change-rfc`. Interactive only; refuse in a scheduled or `-p` run. Goes through `open` and `deferred` CRs (or the given ids), one at a time:
1. Re-read the target RFC (`proposal.rfc_page_id`; version guard above). Re-draft the proposal if that RFC changed.
2. Show the CR: PRD before/now quotes, flags, target RFC title and section, and the proposed edit as **Current RFC text** → **Proposed RFC text**, plus a one-line rationale.
3. Ask with AskUserQuestion: **Apply** · **Edit wording** (the user gives text; show the revised proposal and ask again) · **Reject (don't update RFC)** · **Not now**. If the user names a different RFC (for example via Other), and it's listed in `rfcs`, re-draft the proposal against that RFC, set `rfc_page_id` and `target_page`, and ask again. If it isn't listed, offer `add-rfc` first.
4. Apply → write per the safety rules to `rfc_page_id`, verify the diff, set `status: rfc-updated`, `rfc_version_after` (version of that RFC), `decided_at`. Reject → `status: rejected`, `decided_at`, nothing written. Not now → `status: deferred`.
5. At the end, summarise applied, rejected and deferred, with a version link for each RFC that changed. If every CR of a PRD is now `rfc-updated` or `rejected`, offer `accept <feature> <prd-page-id>` to move that PRD's baseline (it needs its own confirmation).

### `accept <feature> [prd-page-id|all]`
Use after the business has accepted the change request and the RFC has been updated. Requires explicit confirmation from the user in the conversation; never runs in a scheduled run. Sets `baseline_version` to the current version (and `baseline_date`) for the given PRD(s) and clears their items from `open-changes.md`.

### `coverage <feature>`
One-off traceability check against the baseline versions. Write a table to `reports/<today>-coverage.md`: `ID | PRD | Requirement (short quote) | RFC section | Status (Covered / Partial / Missing)`.

### `list`
For each feature, list each RFC (title, role, change number, current version, CRs it carries), any change-RFC files waiting to be published, and each PRD with its baseline version, current version and number of open changes.

## Report format

```markdown
# PRD drift report — <YYYY-MM-DD>

## <feature> — RFCs: <title> v<N> (<link>); <title> v<N> (<link>)

| PRD | Baseline | Current | Status |
|---|---|---|---|
| <title> | v31 (2026-08-11) | v33 | 2 changes |

### CR-1 · NEW · <short title>
**PRD:** <title> · section <heading> · v31 → v33, edited <time> by <author> · [Confluence compare](<diff.compareUrl>)
**Before:**
> <quote or "— not present —">
**Now:**
> <quote>
**Affects RFC:** <RFC title> › <section(s)> — <one line on the impact>
**Flags:** <Needs Legal/Compliance review | Mandatory human review | none>
**Proposed RFC edit** (not applied; run `rfc-update`): <RFC title> › <section> · <replace|insert|delete>
> Current: <anchor>
> Proposed: <new_text>
**Status:** <open | deferred | in change RFC NN (not published yet) | in <RFC title> v<N> | rejected on <date>: RFC intentionally not updated>
**Draft CR note:**
> The PRD "<title>" was updated on <date>, after the RFC was written (baseline v31, <date>). <What changed>. This is outside the agreed scope and is raised as a change request. Please confirm priority and timeline impact.

### Removed
...
### Cosmetic (no action)
- <PRD> · <section>: <one line>
```
