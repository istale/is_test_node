# LLM-Wiki Skill Suite: Design Principles

This file is referenced by all skills in the suite. Read it before working on any wiki task so shared assumptions stay consistent across skills.

## 1. Storage Tiers

The wiki has three storage tiers with strictly different mutation policies:

```
raw/         (IMMUTABLE — see §3)
  ↓ hermes-llm-wiki
working/     (mutable via approved patches only)
  ↓ wiki-compactor (periodic)
canonical/   (reader-facing, produced fresh each compaction)
```

**Never write directly to `working/` outside the sanctioned pipeline.** All mutations to `working/` flow through the patch queue and the deterministic `patch-applier` script. This is what gives us an auditable provenance chain.

**Never write to `canonical/` from any skill except `wiki-compactor`.** Reader agents read `canonical/` — if writers touch it, reads become non-reproducible.

## 2. The Six Skills and One Script

| Component | Type | Reads | Writes | Purpose |
|-----------|------|-------|--------|---------|
| `hermes-llm-wiki` | Skill (Writer) | raw + working + schema | working + schema-patches | Convert raw material into wiki pages |
| `wiki-coverage-audit` | Skill (Follower) | raw + working + schema | patch queue | Check raw key points are covered; check expected pages exist |
| `wiki-relation-detect` | Skill (Interpreter) | raw + wiki-global | patch queue | Detect missing relations, explicit + implicit |
| `wiki-contradiction-check` | Skill (Evaluator) | raw + working | contradiction report | Find wiki-vs-raw conflicts |
| `wiki-compactor` | Skill (Structural) | working + schema | canonical | Restructure working into clean canonical (respecting schema) |
| `schema-drift-audit` | Skill (Meta-structural) | working + schema | schema-patches + drift report | Audit alignment between wiki and schema |
| `patch-applier` | Script (deterministic) | patch queue | working or schema | Apply approved patches (both content and schema) |

**No skill applies its own patches.** Patch application is a deterministic script step (see §6). This prevents auditors from doubling as writers, and prevents LLM-induced drift during patch application.

## 3. Raw Immutability

`raw/` is genuinely immutable. Not by convention — by enforcement.

**Minimum**: `raw/` is a separate git repository or subtree with a pre-commit hook that rejects modifications to files older than 1 minute. New raw files can be added; existing raw files cannot be changed.

**Better**: `raw/` is filesystem-level read-only (`chattr +i` on Linux, `chflags uchg` on macOS) after ingestion. Additions happen through a staging directory that gets moved into `raw/` and locked.

**Best**: `raw/` is content-addressed (files named by hash) and stored in an object store where overwrites are impossible.

Every wiki page must cite raw sources by path + line range or by content hash. If raw could change silently, the entire audit chain becomes untrustworthy. This is not optional infrastructure.

## 4. Posture Separation

Each skill has a distinct mental posture. Mixing postures in one skill degrades all of them.

- **Writer (hermes-llm-wiki)**: constructive compilation. Reads raw as authoritative, produces working as faithful synthesis. Does not question raw.
- **Follower (wiki-coverage-audit)**: constructive verification. Assumes raw is authoritative, checks if working covers it. Does not question raw.
- **Interpreter (wiki-relation-detect)**: constructive inference. May go beyond what raw literally says to infer relations. Must produce evidence chains.
- **Evaluator (wiki-contradiction-check)**: adversarial checking. Questions whether working is consistent with raw. Independent execution — see §5.
- **Structural (wiki-compactor)**: coherence-focused. Reads only wiki content, never raw. Does not judge facts, only structure.

## 5. Independent Execution for Contradiction Check

`wiki-contradiction-check` MUST run in an execution context that has not just processed coverage or relation patches. Rationale: an LLM that has just spent context reinforcing coverage of the current wiki is primed to accept the wiki's framing, which degrades its ability to challenge that framing.

Practical rule: never run `wiki-contradiction-check` in the same session as the writer or the other auditors on the same raw material batch. Either:
- Different LLM instance, cold-started
- Same LLM, but different session with only §1-§7 of this file as prompt context (no prior turn history)

## 6. Explicit vs Implicit Passes

Every auditor runs two passes with different confidence semantics.

**Pass 1: Explicit (HIGH confidence)**
- Coverage: raw literally states X; check working contains X
- Relation: raw literally states "A causes B"; check working contains this edge
- Contradiction: raw literally states not-X; check working does not state X

Explicit patches must cite exact raw location (path + line range).

**Pass 2: Implicit (LOW confidence)**
- Coverage: raw implies X but does not literally state it
- Relation: raw + working global pattern suggests A relates to B
- Contradiction: raw + working jointly entail a contradiction

Implicit patches MUST include a full evidence chain — see §7.

**Implicit-pass iteration cap: 3.** After 3 rounds, the pass stops even if new candidates are still being generated. Rationale: research (Sun et al. 2026 on salient event graph generation) shows LLMs typically stop discovering new valid relations after 2-3 iterations; further iterations produce mostly hallucinated candidates.

## 7. Patch Schema

All patches use this schema. `patch-applier` will reject patches that do not conform.

```json
{
  "patch_id": "uuid",
  "source_skill": "wiki-coverage-audit | wiki-relation-detect | wiki-contradiction-check",
  "pass": "explicit | implicit",
  "confidence": "HIGH | LOW",
  "target_page": "working/path/to/page.md",
  "anchor": {
    "type": "section_heading | line_range | before_after",
    "value": "..."
  },
  "operation": "insert_after | insert_before | replace | delete",
  "content": "...",
  "raw_citations": [
    {
      "raw_path": "raw/2026-01-15/interview-notes.md",
      "line_range": [42, 58],
      "quoted_excerpt": "... (max 100 chars, for reviewer verification)"
    }
  ],
  "wiki_citations": [
    {
      "wiki_path": "working/concepts/observer-agent.md",
      "section": "## Type II Error Handling",
      "issue": "concept X mentioned here without link to concept Y"
    }
  ],
  "evidence_chain": [
    "raw citation 1 says X",
    "wiki citation A says Y",
    "therefore Z should be added to page P"
  ],
  "reviewer_notes": "optional freeform"
}
```

### Field requirements by patch type

| Field | Explicit HIGH | Implicit LOW |
|-------|---------------|--------------|
| `raw_citations` | Required, ≥1 | Required, ≥1 with quoted_excerpt |
| `wiki_citations` | Optional | Required, ≥1 |
| `evidence_chain` | Optional | Required, ≥3 steps |
| `reviewer_notes` | Optional | Recommended |

### Critical: implicit coverage patches

An implicit coverage patch that only says "concept X is undercovered" without pointing to specific raw + wiki locations MUST be rejected. Rationale: LLMs asked to find gaps will hallucinate gaps when none exist (Vaidya et al. 2026 on hydropower extraction). The evidence chain requirement forces the auditor to ground its claim.

## 8. Reviewer Standards

Different confidence levels warrant different reviewer standards, adopted from GenRES (Cabot 2024):

**HIGH-confidence explicit patches**: Reviewer verifies against exact raw text. If the raw citation supports the patch content verbatim (or nearly so), approve.

**LOW-confidence implicit patches**: Reviewer accepts soft matching but requires evidence chain to be plausible. Reject if:
- Evidence chain has fewer than 3 steps
- Any citation in the chain is unverifiable
- The chain requires more than one inferential leap per step

## 10. Domain Schema

The wiki has a `domain-schema/` directory that describes the **expected shape** of the wiki for a given domain. Writer and auditors read it to know:
- What page kinds exist (concept, entity, decision, project, ...) and their expected sections
- What specific pages the domain is expected to contain
- What relations are typical for each kind

Schema is content-authoritative for STRUCTURE, not for FACTS. Facts come from raw. If schema says "every concept page has a Failure Modes section" but raw has no failure mode information for concept X, the writer creates page X without that section and flags it as `schema-partial`. Auditors decide if this matters.

### Schema is versioned wiki content

Domain schema is not a prompt or a config file. It is markdown in `domain-schema/`, tracked in the same repository as `working/` and `canonical/`. Reasons:
- Versioned + diffable
- Reviewable via the same patch mechanism
- Discoverable by all skills without any special loading

### Schema evolution

Schema updates flow through the same patch queue as content, distinguished by `patch_type`:
- `patch_type: "content"` — modifies `working/` pages (default; existing schema)
- `patch_type: "schema"` — modifies `domain-schema/` files

Three sources of schema patches:
1. **Human-authored**: reviewer directly edits schema (bootstrap, curated changes)
2. **Writer-proposed**: `hermes-llm-wiki` encounters raw content that suggests a new page kind or expected page not currently in schema; emits a `patch_type: schema` proposal
3. **Audit-triggered**: `schema-drift-audit` detects mismatch between schema and actual wiki state; proposes schema updates OR flags working pages that violate schema

Schema patches ALWAYS require human review — no auto-approval. Rationale: schema is a governance artifact; drift here is high-leverage in either direction.

### Schema does NOT constrain implicit passes

Auditor implicit passes are still allowed to propose content beyond schema. Schema is a floor (structure expected) not a ceiling (nothing else allowed). If raw material implies content that doesn't fit any existing kind, the writer creates the page and the auditor may propose a new schema kind — but the content still lands.

### Bootstrap vs mature phase

- **Bootstrap** (empty or nearly empty wiki): human writes `domain-schema/expected-pages.md` listing the known-required pages before ingesting raw. Writer uses this as target.
- **Mature** (established wiki): schema is mostly self-maintaining via writer proposals and drift audits. Human review shifts from writing to approving.

See `shared/wiki-structure.md` for the concrete layout and `schema-drift-audit/SKILL.md` for the audit skill.

## 11. Divergences from nvk/llm-wiki

(This section was §9 in v1; renumbered to §11 in v2 to accommodate the domain schema section.)

The nvk/llm-wiki project on GitHub is the closest publicly available prior art. We converge with it on:
- Immutable raw layer
- Separate librarian/audit skills (their `/wiki:librarian` and `/wiki:audit`)
- Confidence scoring on articles
- Coverage tracking for uncompiled sources

We diverge from nvk/llm-wiki on:
- **Three separate audit skills** (coverage, relation, contradiction) instead of one combined audit. Rationale: distinct postures, see §4.
- **Explicit/implicit pass separation** with different confidence semantics. Rationale: hallucination in implicit inference is a known failure mode; separating passes lets reviewers apply appropriate scrutiny.
- **Deterministic patch-applier script**, not an LLM applying patches. Rationale: Planner-Auditor decoupling literature (Wu et al. 2026) shows deterministic validation catches LLM-induced drift.
- **Three-tier storage** (raw / working / canonical) with soft-delete window in compaction. Rationale: patch-drift vs rewrite-drift tradeoff, addressed via hybrid incremental+periodic-recompile pattern (Streaming Knowledge Compilation, 2026).

Read `shared/nvk-comparison.md` for detail on where to steal ideas vs where to hold the line.
