# prd-watch & figma-watch: catch requirement drift before QA does

Two Claude Code skills for engineers who write an RFC from a PRD.

**The problem:** business edits the PRD after the RFC is written. Nobody tells engineering. QA tests against the new PRD and logs the gaps as bugs.

**What the skills do:** they remember which PRD version (and which Figma designs) the RFC was built on. Every day they report what changed since then, map each change to the RFC section it affects, and draft a change-request note for business. Your **base RFC is never edited**: the changes go into a **change RFC** markdown file, in the same Engineering Specification layout, which you publish as a new RFC page.

| Skill | Checks | Runs | Writes anywhere? |
|---|---|---|---|
| `prd-watch` | Confluence PRDs against your Confluence RFCs (one base RFC + change RFCs) | Daily (cron) or on demand | Local reports and change-RFC files only. Writes to an RFC page **only** in `rfc-update`, after you confirm each edit |
| `figma-watch` | Figma frames linked from the PRDs | On demand only (Figma MCP call quota) | Local reports only. **Never writes to Figma** |

---

## Requirements

- Claude Code (CLI) logged in with your claude.ai account.
- The **Atlassian** connector (Confluence). For `figma-watch`, also the **Figma** connector.
- `python3` (standard library only).
- Linux or macOS with `cron`, if you want the daily check.
- For `figma-watch`, a Figma **Dev or Full seat** is strongly recommended. Collab seats hit the Figma MCP tool-call limit after a handful of calls.

## Install

```bash
git clone https://github.com/muhammedshamilv/prd-watch-skills.git && cd prd-watch-skills
./install.sh                 # skills only
./install.sh --cron 10:15    # skills + daily PRD check at 10:15 local time
```

Then in Claude Code run `/mcp` and connect **Atlassian** (and **Figma** if needed). The skills install into `~/.claude/skills/`. Your data goes in `~/prd-watch/<feature>/`.

To update later: `git pull && ./install.sh`.

To uninstall: `rm -rf ~/.claude/skills/prd-watch ~/.claude/skills/figma-watch`, then remove the `daily-check.sh` line with `crontab -e`.

---

## Quick start

A **feature** is one or more RFC pages plus one or more PRD pages. The first RFC is the **base RFC**; later ones are **change RFCs**.

```text
/prd-watch init my-feature --rfc <RFC URL> --prd <PRD URL> [--prd <PRD URL> ...]
/prd-watch init my-feature <RFC URL> <PRD URL> ...      # older one-RFC form, still works
```

`init` picks, for each PRD, the newest version that existed **before your (earliest) RFC was created**. That's the baseline. If a PRD has already changed since then, `init` tells you straight away. Add the line it suggests (e.g. "Based on PRDs: X v31, Y v4 (as of 24 Aug)") to your RFC; that's your evidence later.

Then optionally:

```text
/prd-watch coverage my-feature     # one-off: is every PRD requirement covered by the RFC?
```

## Daily use

| Command | What it does |
|---|---|
| `/prd-watch check` | Compares every PRD against its baseline, writes `reports/YYYY-MM-DD.md` and refreshes `change-rfcs/draft.md` with the open changes. Also what cron runs |
| `/prd-watch change-rfc <feature> [CR-id ...]` | Freezes the open changes into the next numbered change-RFC file, `change-rfcs/<feature>-change-NN-<date>.md`. Local only |
| `/prd-watch add-rfc <feature> <page URL> --change NN` | Registers the change RFC you published, **checks it** against its change requests, and marks them done |
| `/prd-watch accept <feature> <prd-page-id\|all>` | Moves a PRD's baseline forward once business has accepted its changes (asks for confirmation) |
| `/prd-watch list` | RFCs (base, change, superseded), PRDs with baseline and current versions, open changes, change RFCs waiting to be published |
| `/prd-watch add-prd <feature> <PRD URL>` | Adds another PRD to the feature |
| `/prd-watch set-base-rfc <feature> <RFC URL>` | Makes another RFC the base, for example after you merge all change RFCs into a new full RFC. Older RFCs become `superseded`. Asks first |
| `/prd-watch coverage <feature>` | Traceability table: requirement → RFC section → Covered / Partial / Missing |
| `/prd-watch rfc-update <feature>` | Edits an RFC page in place, one confirmed change at a time. For small fixes; not the default for PRD changes |

Each change in a report has:
- the type (**NEW / CHANGED / REMOVED**; cosmetic edits are listed separately)
- the PRD before/now quote, who edited it and when, and a link to Confluence's compare view
- the RFC section affected and a **proposed RFC edit**
- a **draft change-request note** to send to business

### Change RFCs (the default flow)

The base RFC stays as it was agreed. Each batch of PRD changes becomes a new, numbered change RFC holding **only** the changes.

1. **The check finds PRD changes.** It writes them to `~/prd-watch/<feature>/change-rfcs/draft.md`, in your Engineering Specification layout (`skills/prd-watch/templates/change-rfc.md`).
2. **`/prd-watch change-rfc <feature>`** freezes the draft as `change-rfcs/<feature>-change-02-<date>.md`. The file:
   - links the base RFC and its version, and lists the change requests and PRD versions it covers;
   - keeps flags such as "(Pending human review)", and puts unanswered PRD questions under Key Design Decisions as "Open point";
   - uses placeholders instead of real IDs, references or tokens in sample payloads;
   - ends with a table of the change requests it covers.
3. **You create a new Confluence page from the file**, for example "My Feature RFC — Change RFC 02". Confluence converts pasted markdown.
4. **`/prd-watch add-rfc <feature> <page URL> --change 02`** registers the page and checks it: anything missing, or sensitive data that shouldn't be on the page. Change requests whose content is there are marked done.
5. **`/prd-watch accept <feature> <prd-page-id>`** moves the PRD's baseline once business accepts.

Reading order for engineers: base RFC, then change RFCs in number order. A later change RFC wins where they overlap.

### Editing an RFC page in place (`rfc-update`)

- **Draft only at check time.** The daily check drafts the edit but never writes to Confluence; the scheduled job only has read-only Atlassian permissions.
- **You decide each change separately.** `rfc-update` shows the current and proposed RFC text side by side:
  - **Apply:** edits only that part of the RFC page.
  - **Reject:** nothing is written. The change stays in reports as "RFC intentionally not updated", as evidence that it's a change request.
  - **Not now:** asked again next time.
- **Safety checks:**
  - It re-reads the RFC before writing and re-drafts if someone edited it in the meantime.
  - It changes only the targeted block, keeping tables, macros, comments and links intact.
  - It diffs the RFC after writing, and offers to restore if anything else changed.
  - It writes only to RFC pages listed for the feature, never to a PRD.
  - If the Atlassian connector offers no page-write operation, it writes a paste file (`~/prd-watch/<feature>/paste-<page-id>-*.md`) instead, and verifies with a version diff after you paste.

## Daily check cost

The cron job keeps token use low:

- **Version pre-check first.** A small Haiku run reads only the version numbers of every RFC and PRD (about $0.006). If nothing moved, `scripts/precheck.py` writes the short report itself and the full check is skipped.
- **Full check on Sonnet.** It runs only when a PRD or RFC version moved, or the pre-check couldn't read the versions.
- **Overrides:** set `PRD_WATCH_MODEL` (full check, default `sonnet`) or `PRD_WATCH_PRECHECK_MODEL` (default `haiku`) in the crontab line.

## Figma designs (`figma-watch`)

Designers can change a frame without touching the PRD. `figma-watch` fingerprints the visible text (and optionally the layout) of every Figma frame the PRDs link to, and reports changed frames as **DESIGN-n** items.

```text
/figma-watch status my-feature                    # free: no Figma calls
/figma-watch init my-feature --max-calls 40       # baseline, in budgeted batches; re-run to continue
/figma-watch check my-feature --tier daily        # forms/confirmations/errors first
/figma-watch check my-feature --tier weekly       # history/bulk screens
/figma-watch accept my-feature <frame|all>
```

- **Read-only.** It uses only `get_metadata` and `get_design_context`, never `use_figma` or any other edit tool.
- **Budgeted.** Every run is capped by `--max-calls` (default 40). If Figma reports its limit, the run stops and the next run continues where it left off.
- **Cheaper model.** Figma reading happens in Haiku sub-agents.
- **Today is the starting point.** Designs are recorded as they are on the day you run `init`; earlier changes can't be detected.

## Data handling

- **No PRD copies.** Confluence keeps the history, so the skills store only version numbers. Reports contain short quotes only.
- **Redaction.** Phone numbers, emails, short codes, long ID-like numbers and credentials are redacted in reports and Figma fingerprints. Change-RFC files use placeholders in sample payloads, and `add-rfc --change` warns if the published page contains real-looking identifiers, transaction references or tokens.
- **Flags, not conclusions.** Changes touching data protection, AML/CFT or KYC are flagged **Needs Legal/Compliance review**. Reconciliation, ledger or float changes are flagged **Mandatory human review**. The skills never state legal conclusions.
- **Local reports.** Reports are written in UK English and stay in `~/prd-watch/`. Nothing is sent anywhere else.

## Files

```text
~/.claude/skills/prd-watch/     SKILL.md, templates/change-rfc.md,
                                scripts/daily-check.sh (cron), scripts/precheck.py (version pre-check), scripts/prd_diff.py
~/.claude/skills/figma-watch/   SKILL.md, scripts/figma_{links,plan,extract,state}.py, figma_agent_prompt.md
~/prd-watch/<feature>/          meta.json (rfcs + prds), changes.json, open-changes.md, precheck.json,
                                reports/, change-rfcs/ (draft.md + numbered change RFCs), figma*.json
~/prd-watch/cron.log            output of scheduled runs
```

## Troubleshooting

- **Cron runs but there's no report:** check `~/prd-watch/cron.log`. Run `claude` once interactively so the login is fresh. Set `CLAUDE_BIN=/path/to/claude` in the crontab line if `claude` isn't found.
- **"connector not authenticated":** run `/mcp` and reconnect Atlassian or Figma.
- **Figma "tool call limit for your Collab seat":** wait for the quota to reset or get a Dev/Full seat, then re-run the same `figma-watch` command; it continues where it stopped.
- **A machine that's off at the scheduled time:** that day is skipped. Run `/prd-watch check` manually.
- **Existing features from before multi-RFC support:** a `meta.json` with a single `"rfc"` is still read and is rewritten as an `rfcs` list (that RFC becomes the base) on the next save.
