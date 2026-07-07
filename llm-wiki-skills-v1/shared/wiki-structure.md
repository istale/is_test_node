# Wiki Directory Structure

The wiki lives in a repository (or shared location) with the following top-level structure:

```
wiki-root/
├── raw/                    # IMMUTABLE, see design-principles.md §3
│   ├── YYYY-MM-DD/
│   │   ├── source-slug.md
│   │   └── source-slug.metadata.json
│   └── coverage-index.md   # tracks ingestion depth per raw source
│
├── working/                # mutable via approved patches only
│   ├── concepts/
│   ├── entities/
│   ├── projects/
│   ├── decisions/
│   ├── relations/
│   │   ├── relation-index.json
│   │   └── cross-references.md
│   └── _index.md
│
├── canonical/              # reader-facing, produced by wiki-compactor
│   ├── concepts/
│   ├── entities/
│   ├── projects/
│   ├── decisions/
│   └── _index.md
│
├── canonical-archive/      # soft-deleted content during retention window
│   └── YYYY-MM-DD/
│       └── <compaction-run-id>/
│
├── patches/                # patch queue
│   ├── pending/
│   ├── approved/
│   ├── applied/
│   └── rejected/
│
├── reports/                # non-patch outputs (contradictions, audits)
│   ├── contradictions/
│   └── compaction-logs/
│
└── source_map.json         # raw ↔ working ↔ canonical provenance
```

## Directory rules

### raw/
- Write access: ingestion tools only, and only new files
- Read access: all skills
- Mutation: forbidden after ingestion (§3)
- Naming: `YYYY-MM-DD/source-slug.md` for date-organized sources; `hash/<sha256>.md` for content-addressed setups
- Every raw file has a `.metadata.json` sibling with: source_url, ingestion_time, ingested_by, sha256

### working/
- Write access: `patch-applier` script ONLY. No skill writes to `working/` directly.
- Read access: all skills
- Structure: mirrors the semantic organization the wiki uses (concepts, entities, projects, decisions, etc.)
- Every page has YAML frontmatter with: `raw_sources: [list of raw paths]`, `last_patch_id`, `confidence: high|medium|low`

### canonical/
- Write access: `wiki-compactor` ONLY
- Read access: reader agents (query, retrieval)
- Fully regenerated each compaction; do not accumulate patches here
- Every page has YAML frontmatter with: `working_source: <path>`, `compaction_run_id`, `working_last_patch_id_at_compaction`

### canonical-archive/
- Write access: `wiki-compactor` (soft-delete) and a hard-delete cron (after retention)
- Read access: audit-time queries only
- Retention: default 30 days; configurable per deployment
- Every archive entry preserves the canonical page it replaced, tagged with the compaction run that superseded it

### patches/
- `pending/`: newly emitted patches from auditors
- `approved/`: reviewer-approved, waiting for patch-applier
- `applied/`: successfully applied (kept for audit trail)
- `rejected/`: rejected with reviewer_notes
- Naming: `<patch_id>.json`

### reports/
- `contradictions/`: output from `wiki-contradiction-check`. These are reports, not patches — resolution requires human decision on whether to change wiki, re-ingest raw, or annotate
- `compaction-logs/`: output from `wiki-compactor` with before/after diff summary and semantic-preservation check

### source_map.json
- Global provenance index. Maintained by patch-applier and wiki-compactor.
- Structure:
  ```json
  {
    "raw/YYYY-MM-DD/source.md": {
      "referenced_by_working": ["concepts/foo.md", "entities/bar.md"],
      "referenced_by_canonical": ["concepts/foo.md", "entities/bar.md"],
      "coverage_depth": "full | partial | header-only"
    }
  }
  ```

## Frontmatter conventions

Every working and canonical page starts with YAML frontmatter:

```yaml
---
title: Observer Agent
kind: concept | entity | project | decision | relation
raw_sources:
  - raw/2026-05-12/observer-skeptic-log.md
  - raw/2026-04-01/soul-md-v13.md
confidence: high | medium | low
last_patch_id: a3f4c8b0-...
last_updated: 2026-07-07T14:22:11Z
aliases:
  - Observer
  - Type II Guardian
tags:
  - agent
  - error-handling
---
```

Canonical pages add:
```yaml
working_source: working/concepts/observer-agent.md
compaction_run_id: 2026-07-07-run-042
working_last_patch_id_at_compaction: a3f4c8b0-...
```

## Cross-references

All wiki pages use dual links (Obsidian + standard markdown):

```markdown
See [[observer-agent|Observer Agent]] ([Observer Agent](../concepts/observer-agent.md)) for the Type II handling logic.
```

This lets both Obsidian and generic markdown renderers work. This is stolen from nvk/llm-wiki.

## Relation index

`working/relations/relation-index.json` maintains a machine-readable relation graph:

```json
{
  "edges": [
    {
      "source": "concepts/observer-agent.md",
      "target": "concepts/skeptic-agent.md",
      "relation": "collaborates_with",
      "confidence": "high",
      "raw_source": "raw/2026-04-01/soul-md-v13.md",
      "raw_line_range": [42, 58]
    }
  ]
}
```

`wiki-relation-detect` reads and updates this index via patches. Canonical mirror gets rebuilt each compaction.
