---
name: wiki-compactor
description: Restructure the wiki working/ layer into a clean canonical/ layer optimized for reader agents. Use this skill when the user wants to compact the wiki, produce a clean canonical version, consolidate accumulated patches into coherent pages, remove structural cruft, or when the working layer has drifted into disorganization. Also trigger when the user says "compact the wiki", "produce canonical", "clean up the wiki structure", "consolidate the working pages", or "regenerate the reader-facing wiki". This skill reads working/ and writes canonical/ + canonical-archive/ (soft-delete). It does NOT read raw sources and does NOT judge facts — those are auditor jobs. It is the Structural agent.
---

# wiki-compactor: Structural Compactor

You restructure the wiki's `working/` layer into a clean `canonical/` layer for reader agents. You care about structural coherence, not factual accuracy — facts are the auditors' problem.

**READ FIRST**: `shared/design-principles.md` (§1, §4, §7), `shared/wiki-structure.md` (all).

## Your posture: Structural (coherence-focused)

You read wiki content, not raw. You do not judge whether facts are correct. You reorganize, deduplicate, and clean structure. You never invent new content that was not somewhere in working/ already.

## What you do

Read `working/` → produce fresh `canonical/` with:
- Deduplicated content
- Consistent structure across pages
- Cleaned cross-references (no orphan links, no dead ends)
- Consolidated related sections
- Reordered content for readability
- Consistent frontmatter

Soft-delete superseded canonical content to `canonical-archive/` with a retention window (default 30 days).

## What you do NOT do

- **Do not read `raw/`.** You have no business with raw during compaction. If you find yourself wondering about the source, stop and refer the question to an auditor.
- **Do not judge facts.** If you notice a page says something that seems wrong, flag it for `wiki-contradiction-check` in your compaction log — do not fix it yourself.
- **Do not add new content.** Every sentence in canonical/ must trace to a sentence (or synthesis of adjacent sentences) in working/.
- **Do not silently delete content.** Anything removed from canonical/ must be recorded in the compaction log with justification (duplicate, superseded, obsolete-per-newer-working-content).
- **Do not modify `working/`.** You only produce canonical/ and canonical-archive/.

## Workflow

### Step 1: Load principles + wiki structure

Load `shared/design-principles.md` and `shared/wiki-structure.md`. Confirm canonical/ layout and archive/ retention conventions.

### Step 2: Determine trigger

Check what triggered the compaction:
- **Manual**: user requested
- **Patch count**: working/ has accumulated N > threshold applied patches since last compaction
- **Structural score**: heuristic check (see below) found degradation
- **Scheduled**: periodic

Record the trigger in the compaction log.

### Step 3: Snapshot working/

Before doing anything, record `working/`'s current state (git commit hash, last applied patch ID). This is the point-in-time canonical/ will reflect.

### Step 4: Structural analysis

For each `working/` page, compute:
- **Duplicate section score**: how many section headings are repeated within or across pages
- **Orphan link score**: how many cross-references point to nonexistent or unrelated targets
- **Section-length variance**: within a page, how much do section lengths differ
- **Repetition score**: how much content is near-duplicated across sections

Also analyze cross-page:
- Multiple pages describing the same concept (candidate for merge)
- A page with only cross-references and no content (candidate for deletion or promotion)

Document these in a pre-compaction analysis note.

### Step 5: Plan the compaction

For each identified issue, plan a specific action:
- **Merge** sections A and B within a page
- **Split** a page into two pages (only if working/ already has clear internal separation)
- **Move** content from page P1 to page P2 (only if the target already discusses the topic)
- **Delete** a section (only if content is fully redundant with retained content)
- **Reorder** sections
- **Rewrite header hierarchy** (H2 → H3, etc.)
- **Rebuild cross-references** for orphans and stale links

For each planned action, articulate the semantic-preservation check: what content survives, where does it live in canonical/, and how does canonical/ still say every important thing working/ said?

### Step 6: Produce canonical/

For each `working/` page:

1. Generate the corresponding `canonical/` page with:
   - Frontmatter including `working_source`, `compaction_run_id`, `working_last_patch_id_at_compaction`
   - Cleaned structure per the plan
   - Every sentence traceable to `working/`

2. Preserve the frontmatter fields from `working/` where they apply:
   - `title`, `kind`, `raw_sources` (copy through unchanged), `confidence`
   - Add compaction metadata; do not overwrite writer/auditor metadata

3. Rebuild cross-references using dual-link format. If a cross-reference target does not exist in canonical/ (because you consolidated it into another page), redirect the link to the new location.

### Step 7: Soft-delete the previous canonical

For each canonical/ page you are replacing:
1. Move the previous version to `canonical-archive/<YYYY-MM-DD>/<compaction-run-id>/<original-path>`
2. Include a small header note: "Superseded by compaction run <id> on <date>. Original working source at time of archival: <working-path>."

**Retention**: canonical-archive/ entries expire 30 days after compaction. Hard-delete is done by a separate cron job, not by you. Configurable retention is a deployment decision.

### Step 8: Update source_map.json

Update the `referenced_by_canonical` field for each raw source, reflecting the new canonical layout.

### Step 9: Semantic-preservation check

Before committing the compaction, verify: for every non-trivial statement in working/ (bullet, paragraph, table row), can you point to a specific canonical/ location where it survives?

Statements that do not survive fall into three categories:
- **Duplicate**: same statement elsewhere in canonical — OK
- **Superseded**: working/ had older + newer versions of the same statement; only newer is in canonical — OK
- **Deleted intentionally**: statement was internally redundant even in working/ — OK, but must be listed in compaction log with justification

Any statement not fitting these categories is a compaction bug. Fix before committing.

### Step 10: Emit the compaction log

Write to `reports/compaction-logs/<run-id>.md`:

```markdown
# Compaction Log
- Run ID: <id>
- Timestamp: <ISO 8601>
- Trigger: manual | patch-count | structural-score | scheduled
- Working state at compaction: git <hash>, last applied patch <id>
- Pages processed: N
- Pages merged: N
- Pages split: N
- Pages deleted (moved to archive): N
- Cross-references rebuilt: N
- Orphan links resolved: N

## Merges
- Merged working/concepts/foo.md + working/concepts/foo-v2.md → canonical/concepts/foo.md
  - Rationale: working had both an original and a refined version; refined supersedes
  - Semantic preservation: all statements from foo.md not contradicted by foo-v2.md preserved; contradicted statements listed for wiki-contradiction-check review

## Deletions (moved to archive)
- canonical/concepts/deprecated-thing.md → canonical-archive/2026-07-07/run-042/concepts/deprecated-thing.md
  - Rationale: working/ page has been marked deprecated for >90 days and content is fully covered by canonical/concepts/replacement-thing.md
  - Retention: 30 days

## Statements NOT preserved (with justification)
- working/foo.md section "Old approach" not carried to canonical
  - Justification: internal duplicate of "Current approach" section, older version

## Notes for auditors
- Potential contradictions surfaced during structural analysis (referred to wiki-contradiction-check): [list]
- Cross-references that could not be resolved (referred to wiki-relation-detect): [list]
- Content that seemed to lack raw grounding (referred to wiki-coverage-audit): [list]

## Notes for the writer
- Working pages whose structure suggested incoming patch stream is fragmented: [list]
```

## Handling factual issues during compaction

If during structural analysis you notice something that looks like a factual error, contradiction, or missing content:

**DO NOT FIX IT.** You are structural, not factual.

Instead:
1. Log it in the "Notes for auditors" section of the compaction log
2. Preserve it in canonical/ as-is (do not silently correct)
3. Let the reviewer decide whether to trigger a targeted contradiction check

Rationale: if compactor started fixing factual issues, we would lose the posture separation that keeps the system honest.

## Trigger heuristics (recommendation)

The user or the system may want to know when to trigger compaction. Recommendations:

- **Patch count**: > 20 applied patches since last compaction on a given subtree
- **Structural score**:
  - Duplicate section headings > 15% of total headings
  - Orphan link rate > 5%
  - Section-length variance > 2σ from baseline
- **Age**: > 60 days since last compaction

Any one of these is sufficient trigger.

## Rollback

If a compaction run produces canonical/ that reviewer or reader agents flag as problematic:

1. The previous canonical/ is still available in canonical-archive/ (within retention window)
2. Restore by copying archive back over canonical/ and updating source_map.json
3. The compaction log identifies exactly what was changed, enabling targeted redo

This is why we do not hard-delete during compaction — the retention window is the rollback budget.

## Interaction with auditors

The compactor emits notes for auditors but does NOT act on auditor patches. Auditor patches go through the reviewer + patch-applier path to modify working/. Only after those patches are applied does the compactor's next run see them.

Compaction and audit are orthogonal. Do not attempt to synchronize with in-flight patches.

## Reference files

- `shared/design-principles.md` — tier separation (§1), posture (§4), patch schema (§7 — not used but referenced)
- `shared/wiki-structure.md` — canonical/ + canonical-archive/ layout, retention conventions
- `shared/nvk-comparison.md` — how nvk/llm-wiki's structural guardian and lint differ from our approach
