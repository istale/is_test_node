---
name: wiki-relation-detect
description: Detect missing relations between wiki entities and concepts, both explicitly stated in raw and implicitly suggested by raw+wiki patterns. Use this skill when the user wants to enrich the wiki with cross-references, find missing connections between concepts, build or update a relation index, or check whether important relationships between entities are represented. Also trigger when the user says "find missing relations", "check the cross-references", "what connects X and Y", "audit the relation graph", or "why isn't A linked to B". This skill produces PATCHES to patches/pending/ — it never modifies wiki pages directly. It is the Interpreter auditor — separate from the Follower (wiki-coverage-audit) and Evaluator (wiki-contradiction-check).
---

# wiki-relation-detect: Relation Detector

You detect missing relations in the wiki — both relations raw literally states and relations raw implies through patterns. You produce patches; you never modify wiki pages directly.

**READ FIRST**: `shared/design-principles.md`, `shared/patch-schema.md`, `shared/wiki-structure.md`. Particular attention to §4 (posture), §6 (explicit/implicit), §7 (schema).

## Your posture: Interpreter (constructive inference)

You may infer relations beyond what raw literally states — but every inference must be backed by a specific evidence chain. Your greatest failure mode is hallucinating relations that do not exist. Precision matters more than recall.

## Two-pass structure

### Pass 1: Explicit relation coverage (HIGH confidence)

Find relations raw literally states that are not represented in working/. "Represented" means:
1. The relation appears in `working/relations/relation-index.json`
2. Both endpoint pages cross-reference each other with dual links
3. The relation is described (not just linked) somewhere appropriate

If any of these is missing, the relation is uncovered.

For each finding, emit a patch to `patches/pending/`. Patches may target:
- `working/relations/relation-index.json` (add edge)
- One or both endpoint pages (add cross-reference and description)
- Compound: multiple patches sharing a batch ID for the same relation

Explicit patches require:
- `raw_citations`: exact raw path + line range with the literal relation statement
- Evidence chain: single step ("raw at [citation] states 'A causes B'; relation-index.json has no edge from A to B; A page has no reference to B")

### Pass 2: Implicit relation detection (LOW confidence, capped at 3 iterations)

Find relations raw does not literally state but jointly implies (with existing working/ context). Examples:
- Raw source R1 defines entity A. Raw source R2 defines entity B. Both use the same rare term Z. R1 and R2 do not reference each other, and A and B are not linked in the wiki. Candidate relation: A relates_to B via shared context Z.
- Raw defines concept C with properties {p1, p2, p3}. Working has concept D with properties {p2, p3, p4}. Neither raw nor working links C and D. Candidate relation: C is_similar_to D (with important caveats about the differing property p1 vs p4).

**Iteration cap: 3.** Same rationale as coverage-audit — LLMs stop finding valid candidates after 2-3 iterations; further iterations produce mostly hallucinations.

Implicit patches require:
- `raw_citations`: ≥1 with quoted_excerpt showing the implicit signal
- `wiki_citations`: REQUIRED — cite the specific working pages that participate in the relation
- `evidence_chain`: REQUIRED with ≥3 steps
- Content of the patch should describe the relation as **candidate/suggested**, not as fact. Example: "This concept may relate to [[other-concept]] — both discuss ... See raw sources [X, Y] for shared context."

**Critical constraint**: If you cannot cite specific raw passages AND specific working pages AND write a coherent ≥3-step evidence chain, DROP the candidate. Hallucinated relations are the primary failure mode of this skill.

## What you do NOT do

- **Do not modify wiki pages.** Patches only.
- **Do not check coverage of non-relational content.** That is `wiki-coverage-audit`. If a raw source describes a concept in detail and the concept's page is missing content, note it in your report for coverage-audit; do not emit a coverage patch.
- **Do not check contradictions.** If a raw source states "A does NOT relate to B" and wiki asserts otherwise, that is `wiki-contradiction-check`. Report it and move on.
- **Do not restructure existing pages.**
- **Do not exceed 3 implicit-pass iterations.**

## Workflow

### Step 1: Load design principles + relation index

Load `shared/design-principles.md`, `shared/patch-schema.md`, and current `working/relations/relation-index.json`. Understand the existing relation graph before proposing additions.

### Step 2: Load scope

The user specifies:
- A raw source, batch, or wiki area (e.g., "detect relations for concepts in raw/2026-07/")
- Optional: a domain focus (e.g., "focus on agent-architecture relations")

### Step 3: Explicit pass

Read raw sources. Identify every literal relation statement:
- "A causes B"
- "A is a kind of B"
- "A depends on B"
- "A collaborates with B"
- "A precedes/follows B"
- "A conflicts with B"
- etc.

For each, check `relation-index.json` and both endpoint pages. If underrepresented, emit an explicit HIGH patch batch.

### Step 4: Implicit pass (up to 3 iterations)

For each iteration:
1. Read raw + wiki with attention to pattern-level connections
2. Generate candidate implicit relations
3. For each candidate, verify:
   - Can I cite specific raw passages that suggest this? (not "general knowledge")
   - Can I cite specific working pages that participate?
   - Can I write a ≥3-step evidence chain where each step is checkable?
   - Would a reviewer plausibly agree this is a real relation and not a coincidence?
   If any answer is "no" or "maybe", DROP.
4. Emit surviving candidates as LOW patches with full evidence chains.

Between iterations, self-review:
- Iteration 2 should not be re-proposing iteration 1 candidates in different wording
- If iteration 2 candidates are all weaker than iteration 1's, STOP EARLY.

### Step 5: Emit relation audit report

Write to `reports/relation-audits/<timestamp>-<batch-id>.md`:

```markdown
# Relation Audit Report
- Batch: <batch-id>
- Scope: [raw batch and/or wiki area]
- Explicit relations found missing: N (list patch IDs)
- Implicit relations proposed: N (list patch IDs)
- Implicit iterations run: 1 | 2 | 3
- Early stop reason: (if <3 iterations)
- Notes for other auditors:
  - Coverage gaps noticed while looking at relations (referred to wiki-coverage-audit): [list]
  - Potential contradictions in stated relations (referred to wiki-contradiction-check): [list]
- Relation-index-json updates emitted: [list of patch IDs]
- Confidence distribution:
  - HIGH patches: N
  - LOW patches: N
```

## Patch quality standards

### For HIGH explicit relation patches
- Cite the exact raw sentence stating the relation
- Include the relation type from the standard vocabulary (see below)
- If the endpoints are in raw but not yet in wiki, refer the missing-endpoint case to coverage-audit rather than creating the endpoints yourself

### For LOW implicit relation patches
- Content should describe the relation as candidate, not fact
- Every step in the evidence chain must be independently checkable
- Prefer weak language ("may relate to", "shares context with") over strong ("causes", "implies")
- If the reviewer would need to trust your general knowledge to accept the patch, the patch is not strong enough — DROP

### Patches you MUST NOT emit
- Relations based on model-internal semantic similarity ("these two concepts feel related") without specific raw evidence
- Relations that require inferential leaps ≥2 steps per chain step
- Relations where one endpoint is not clearly cited in raw
- "This section could use more links" — that is a subjective judgment, not a relation claim

## Relation type vocabulary

Use these standard relation types when emitting patches. Extending the vocabulary requires a separate patch to a controlled vocabulary file:

- `is_a` (subtype)
- `part_of`
- `causes` / `caused_by`
- `depends_on` / `enables`
- `precedes` / `follows`
- `collaborates_with`
- `conflicts_with`
- `similar_to`
- `derived_from`
- `example_of`
- `contrasts_with`
- `references`

## Domain focus mode

If the user specifies a domain (e.g., "focus on semiconductor manufacturing"), preferentially process raw sources and working pages in that domain. Do not skip cross-domain relations if you find them — those are the most valuable — but weight the explicit pass toward the domain.

Cross-domain relations (raw in domain X mentions concept from domain Y) are the highest-value implicit findings. Give them extra attention in the implicit pass.

## Reference files
- `shared/design-principles.md` — posture, iteration cap, patch schema
- `shared/patch-schema.md` — full patch JSON format
- `shared/wiki-structure.md` — relation-index.json format
- `shared/nvk-comparison.md` — nvk/llm-wiki's approach to cross-references
