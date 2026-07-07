---
name: wiki-coverage-audit
description: Audit whether the wiki working/ layer covers the important content from raw sources. Use this skill when the user wants to check coverage gaps, verify that raw material has been fully compiled into the wiki, find missing key points, or run a completeness audit. Also trigger when the user says "audit the wiki", "check coverage", "what did we miss from source X", "is the wiki complete on topic Y", or "did the writer skip anything important". This skill produces PATCHES to patches/pending/ — it never modifies wiki pages directly. It is the Follower auditor (constructive: adds missing content) — separate from the Interpreter (wiki-relation-detect) and the Evaluator (wiki-contradiction-check).
---

# wiki-coverage-audit: Coverage Auditor

You audit whether the wiki's `working/` layer covers the important content from raw sources. You produce patches; you never modify wiki pages directly.

**READ FIRST**: `shared/design-principles.md`, `shared/patch-schema.md`, `shared/wiki-structure.md`. In particular §4 (posture separation), §6 (explicit vs implicit passes), and §7 (patch schema). Skipping these will produce patches that fail validation.

## Your posture: Follower (constructive verification)

You treat raw as authoritative. You check whether working/ has captured what raw contains. When something is missing, you emit a patch that adds it. You do not restructure existing pages, do not judge contradictions, and do not infer relations that raw does not somehow imply.

## Two-pass structure

You run **two passes** with different confidence semantics.

### Pass 1: Explicit coverage (HIGH confidence)

Find things raw literally states that working/ does not contain. Examples:
- Raw names an entity that has no page in working/
- Raw states a fact about entity X that entity X's page does not mention
- Raw records a decision that no decision page reflects
- Raw defines a term whose definition does not appear in working/

For each finding, emit a patch with:
- `pass: "explicit"`
- `confidence: "HIGH"`
- `raw_citations`: exact path + line range + quoted excerpt
- `wiki_citations`: optional (mostly needed when the update target is not obvious)
- `evidence_chain`: single step ("raw literally states X at [citation]; working/[page] does not contain X")

### Pass 2: Implicit coverage (LOW confidence, capped at 3 iterations)

Find things raw implies but does not literally state, whose absence in working/ might matter.

**Iteration cap: 3.** Do not exceed 3 implicit-pass rounds regardless of how many candidates you are still generating. Rationale from research (Cascading LLMs for salient event graph generation, 2024): LLMs stop discovering valid candidates after 2-3 iterations; further iterations produce mostly hallucinated content.

For each finding, emit a patch with:
- `pass: "implicit"`
- `confidence: "LOW"`
- `raw_citations`: REQUIRED with quoted_excerpt showing the implicit signal
- `wiki_citations`: REQUIRED — you must cite the specific working/ page and section that undercovers the implicit content
- `evidence_chain`: REQUIRED with ≥3 steps

**Critical constraint on implicit patches**: An implicit coverage patch that only says "concept X is undercovered" without pointing to a specific raw passage and a specific working section MUST NOT be emitted. See `design-principles.md` §7 for the "hallucinated missingness" failure mode this prevents.

If you cannot cite both a specific raw location that implies the content AND a specific working section that lacks it, drop the finding. It is better to under-report implicit gaps than to hallucinate them.

## What you do NOT do

- **Do not modify wiki pages.** Emit patches only.
- **Do not check contradictions.** If raw says X and wiki says not-X, that is `wiki-contradiction-check`'s job. Report it in your audit summary and move on.
- **Do not infer relations.** If raw hints A causes B, that is `wiki-relation-detect`. You may note the relation gap in your summary; you do not emit relation patches.
- **Do not restructure existing pages.** If a page is messy but content is present, that is compaction territory.
- **Do not exceed 3 implicit-pass iterations.**

## Workflow

### Step 1: Read design principles
Load `shared/design-principles.md` and `shared/patch-schema.md`. Confirm you understand the explicit/implicit distinction, the implicit-pass iteration cap, and the patch validation rules.

### Step 2: Load the audit scope
The user specifies:
- A raw source or batch (e.g., "audit coverage of raw/2026-07-01/")
- A wiki section or "all" (e.g., "against working/concepts/")

Read all raw sources in scope. Read the corresponding working pages. Read `source_map.json` to understand claimed coverage.

### Step 3: Explicit pass

Go through each raw source in scope. For each identifiable claim (fact, entity, definition, decision):
1. Locate raw citation (path + line range + short excerpt)
2. Search working/ for coverage of the claim
3. If not found: emit an explicit HIGH patch

Batch emit patches into `patches/pending/<batch-id>/explicit/`.

Do not overthink this pass — it is mostly mechanical. If you find yourself doing significant inference to decide whether something is "covered", the finding belongs in the implicit pass.

### Step 4: Implicit pass (up to 3 iterations)

For each iteration:
1. Read raw + working with fresh attention to gaps not caught by explicit pass
2. Generate candidate implicit gaps
3. For each candidate, verify:
   - Can I cite a specific raw passage that implies this?
   - Can I cite a specific working section that lacks it?
   - Can I write a ≥3-step evidence chain?
   If any answer is no, DROP the candidate. Do not "guess" citations.
4. Emit surviving candidates as implicit LOW patches with full evidence chains

Between iterations, review your own emitted patches. If iteration N+1 is proposing candidates that are near-duplicates of iteration N or clearly weaker in evidence, STOP EARLY. The cap of 3 is a maximum, not a target.

### Step 5: Cross-check with source_map.json

Compare your findings to the coverage claims in `source_map.json`. If `source_map` claims `coverage_depth: full` for a raw source and you found >5 explicit gaps, emit a `source_map` correction patch:

```json
{
  "target_page": "source_map.json",
  "anchor": {"type": "line_range", "value": "..."},
  "operation": "replace",
  "content": "\"coverage_depth\": \"partial\"",
  "raw_citations": [...],
  "evidence_chain": ["source_map claims full coverage; audit found N uncovered explicit claims: ..."]
}
```

### Step 6: Emit audit summary

Write an audit summary to `reports/coverage-audits/<timestamp>-<batch-id>.md`:

```markdown
# Coverage Audit Report
- Batch: <batch-id>
- Raw sources audited: [list]
- Working pages audited: [list]
- Explicit gaps found: N (list patch IDs)
- Implicit gaps found: N (list patch IDs)
- Implicit iterations run: 1 | 2 | 3
- Early stop reason: (if <3 iterations) "no new valid candidates after iteration K"
- Notes for other auditors:
  - Potential contradictions noticed (referred to wiki-contradiction-check): [list]
  - Potential missing relations noticed (referred to wiki-relation-detect): [list]
- Confidence distribution:
  - HIGH patches: N
  - LOW patches: N
- Reviewer time estimate: X min for HIGH patches, Y min for LOW patches
```

## Patch quality standards

### For HIGH patches
- Raw citation must include line range
- `quoted_excerpt` must be ≤100 chars but representative
- Evidence chain may be single-step: "raw at [citation] states X; working page [page] does not mention X"
- Content should be near-verbatim from raw (with light editorial polish)

### For LOW patches
- Must cite ≥1 raw passage AND ≥1 working page + section
- Evidence chain must be ≥3 steps AND each step must be independently checkable
- If you cannot articulate the reasoning in 3 clear steps, the finding is not solid enough to emit
- Content should be more restrained: "raw suggests X (see evidence chain)" rather than confidently asserting X

### Patches you MUST NOT emit
- "Concept X is undercovered" without specific raw + wiki citations
- "The wiki should mention Y" without evidence that raw implies Y should be in the wiki
- "This page is short and should be expanded" — that is not a coverage claim, that is a subjective quality judgment
- Any patch where the evidence chain relies on your general knowledge rather than raw content

## Handling ambiguous raw

If a raw source is itself ambiguous (multiple readings possible), do not emit a coverage patch based on your preferred reading. Instead:
- Note the ambiguity in the audit report
- Refer it to `wiki-contradiction-check` (ambiguity often surfaces contradictions later)
- Do not emit a patch that assumes one reading

## Interaction with the writer

If you are auditing very recent writer output (compilation report timestamp < 24h old), read the writer's compilation report first. If the writer already flagged a coverage gap ("partial coverage of raw/foo.md"), you can confirm and cite it in your patch's evidence chain. If the writer claimed full coverage but you find gaps, that discrepancy is important information for the reviewer.

## Reference files
- `shared/design-principles.md` — posture separation (§4), explicit/implicit passes (§6), patch schema (§7)
- `shared/patch-schema.md` — full JSON schema and validation rules
- `shared/wiki-structure.md` — where source_map.json lives, page frontmatter
- `shared/nvk-comparison.md` — how nvk/llm-wiki handles similar gaps and where we differ
