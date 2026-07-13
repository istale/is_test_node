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
├── domain-schema/          # mutable via approved SCHEMA patches only; see §Domain Schema
│   ├── kinds/
│   │   ├── concept.md
│   │   ├── entity.md
│   │   ├── decision.md
│   │   ├── project.md
│   │   └── relation.md
│   ├── expected-pages.md   # domain-level list of expected pages
│   ├── expected-relations.md   # expected relation patterns per kind
│   └── schema-evolution.md # log of schema changes with rationale
│
├── working/                # mutable via approved CONTENT patches only
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
├── patches/                # patch queue (both content and schema patches)
│   ├── pending/
│   │   ├── content/        # patches to working/
│   │   └── schema/         # patches to domain-schema/
│   ├── approved/
│   │   ├── content/
│   │   └── schema/
│   ├── applied/
│   │   ├── content/
│   │   └── schema/
│   └── rejected/
│       ├── content/
│       └── schema/
│
├── reports/                # non-patch outputs (contradictions, audits, drift reports)
│   ├── contradictions/
│   ├── compaction-logs/
│   ├── coverage-audits/
│   ├── relation-audits/
│   ├── schema-drift/       # from schema-drift-audit
│   └── compilation-logs/
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

## Domain schema layout

`domain-schema/` describes what the wiki is EXPECTED to look like for the current domain. It is content-authoritative for structure, not for facts.

### domain-schema/kinds/

One file per page kind. Each file describes the expected shape of pages of that kind.

Example `domain-schema/kinds/concept.md`:
```markdown
---
kind: concept
required_sections:
  - "# {title}"
  - "## Definition"
  - "## Sources"
recommended_sections:
  - "## Failure Modes"
  - "## Related Concepts"
  - "## Examples"
required_frontmatter:
  - title
  - kind
  - raw_sources
  - confidence
typical_relations:
  - is_a
  - part_of
  - similar_to
---

# Concept pages

Concept pages describe a technical or design concept that recurs across projects.

## When to create a concept page

- Term is used more than once across raw sources
- Term has a specific meaning within the domain
- Term is not a synonym for an existing concept

...
```

### domain-schema/expected-pages.md

Domain-level list of pages the wiki is expected to have. Grouped by kind. Example:

```markdown
# Expected Pages

## Concepts
- [ ] process-control-monitoring — PCM basics
- [x] canonic-agent — three-role architecture
- [ ] d-optimal-design — experimental design method

## Entities
- [x] hermes-agent
- [ ] openclaw-platform

## Decisions
- [x] adopt-three-tier-storage
```

Checkboxes indicate whether the page currently exists in `working/`. Maintained by writer (marks off on creation) and `schema-drift-audit` (verifies alignment).

### domain-schema/expected-relations.md

Expected relation patterns per kind. Example:

```markdown
# Expected Relations

## For concept pages
- Should reference at least 1 raw source
- Should have at least 1 outgoing relation to another concept OR entity
- If confidence: high, should have at least 2 raw sources

## For decision pages
- Must have a decision date
- Should reference the entities/concepts affected by the decision
```

### domain-schema/schema-evolution.md

Chronological log of schema changes. Each entry:
```markdown
## 2026-07-15 — Added `## Failure Modes` as recommended section for concept pages
- Rationale: multiple concept pages ingested from raw material now include failure discussions
- Proposed by: wiki-coverage-audit implicit pass
- Reviewed by: human reviewer
- Patch ID: schema-patch-042
```

## Domain schema frontmatter

Schema files use frontmatter with `schema_version` field to enable safe evolution:

```yaml
---
schema_version: 2026-07-01
kind: concept
last_updated: 2026-07-07T14:22:11Z
last_patch_id: schema-patch-042
---
```

Working pages may pin to a specific schema version via `schema_version` in frontmatter. If they omit it, they follow the current version.

## Bootstrap files (recommended starting content)

When creating a new wiki, bootstrap `domain-schema/` with:

```
domain-schema/
├── kinds/
│   ├── concept.md          (start with just required_sections: title, Sources)
│   ├── entity.md           (same)
│   └── decision.md         (same, plus decision_date frontmatter)
├── expected-pages.md       (empty [] list, ready to fill)
├── expected-relations.md   (start with minimum viable: "should cite raw")
└── schema-evolution.md     (empty log)
```

Then hand-add expected pages you already know about before running the writer on your first raw batch.
