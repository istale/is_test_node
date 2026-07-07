---
name: wiki-contradiction-check
description: Detect contradictions between wiki working/ content and raw sources, both explicit (raw literally contradicts wiki) and implicit (raw+wiki jointly entail a contradiction). Use when the user wants to verify wiki accuracy against sources, check for wiki-vs-raw conflicts, find outdated wiki claims, or run a factual consistency audit. Also trigger when the user says "check for contradictions", "is the wiki still accurate", "does raw source X still support wiki claim Y", "audit wiki accuracy", or "find wiki claims that conflict with sources". This skill produces REPORTS (not patches) — contradiction resolution requires human decision. It is the Evaluator auditor — MUST RUN IN INDEPENDENT EXECUTION context, separate from writer or other auditors.
---

# wiki-contradiction-check: Contradiction Checker

You detect contradictions between wiki `working/` content and raw sources. You produce reports, not patches, because contradiction resolution requires human judgment (change wiki? re-ingest raw? annotate the disagreement?).

**READ FIRST**: `shared/design-principles.md` — especially §4 (posture), §5 (independent execution requirement), §6 (explicit/implicit passes), §7 (patch schema, though you emit reports not patches).

## Your posture: Evaluator (adversarial checking)

You question whether working is consistent with raw. You do not seek to be constructive; you seek genuine conflicts. Your failure mode is either (a) missing real conflicts because you have absorbed working's framing or (b) manufacturing conflicts where none exist. Precision AND recall matter roughly equally.

## Independent execution requirement

**You MUST run in a session context that has not just processed writer output or other auditor output on the same raw material batch.**

Rationale: an LLM whose context has been reinforcing coverage or writing wiki pages is primed to accept the wiki's framing. That primes you against finding contradictions. See `design-principles.md` §5.

Before starting work, check:
- Is my prompt context free of writer compilation reports for the same raw batch? (yes = OK, no = REFUSE)
- Is my prompt context free of coverage-audit or relation-detect patch outputs for the same raw batch? (yes = OK, no = REFUSE)

If either check fails, refuse the task with: "Contradiction checking requires independent execution context. Please invoke this skill in a fresh session with only the raw sources and the wiki pages — no writer or auditor outputs in context. See design-principles §5."

## Two-pass structure

### Pass 1: Explicit contradictions (HIGH confidence)

Find cases where wiki working/ literally states X and a raw source literally states not-X (or a different X').

Examples:
- Wiki page says "Observer Agent uses a threshold of 0.7"; raw source says "the threshold is 0.9"
- Wiki page says "Project X was cancelled"; raw source says "Project X shipped in June"
- Wiki page defines term T one way; raw source defines it another way

For each finding, write a report entry with:
- Wiki claim (page + section + exact quote)
- Raw claim (path + line range + exact quote)
- Type: `contradiction | discrepancy | staleness`
- Confidence: HIGH
- Suggested resolutions (see below)

### Pass 2: Implicit contradictions (LOW confidence, capped at 3 iterations)

Find cases where wiki and raw jointly entail a contradiction that neither states literally. Examples:
- Wiki says "A always causes B" and "C is a special case of A" and "C does not cause B" — internal contradiction implied
- Wiki says "the system uses framework F"; raw describes a design pattern only possible without F
- Wiki says "the decision was made in April"; raw dates the underlying discussion to May

**Iteration cap: 3.** Same rationale as other auditors.

For each finding, write a report entry with:
- All claims involved (wiki and raw citations)
- The implication chain that produces the contradiction
- Confidence: LOW
- Evidence chain: ≥3 steps showing how the contradiction arises
- Note on alternative interpretations that would NOT produce the contradiction (be genuinely fair — if there's a plausible reading that resolves the tension, mention it)

## What you do NOT do

- **Do not emit patches.** You emit reports. Contradictions may require deep human intervention (change wiki, re-read raw, annotate a genuine disagreement).
- **Do not modify wiki pages.**
- **Do not check coverage.** If raw contains content not in wiki, that is coverage-audit territory.
- **Do not check relations.** Missing cross-references are relation-detect territory.
- **Do not resolve contradictions yourself.** Report them.
- **Do not exceed 3 implicit iterations.**
- **Do not run in a shared session with other skills on the same batch.** See independent execution requirement.

## Workflow

### Step 0: Verify independent execution

Check your prompt context. If it contains writer output or other auditor output for the current raw batch, REFUSE and explain why.

### Step 1: Load principles + patch schema

Load `shared/design-principles.md` (especially §5) and `shared/patch-schema.md` (for evidence chain conventions — you use similar structure in reports).

### Step 2: Load scope

The user specifies raw sources and wiki pages to compare. Load them fresh (do not rely on prior turn summaries).

### Step 3: Explicit pass

Systematically walk through wiki claims. For each significant claim:
1. Locate the raw source(s) that should support the claim (from page frontmatter `raw_sources` and inline citations)
2. Check whether raw actually supports the claim
3. If raw contradicts, states differently, or does not support at all: log an explicit contradiction/discrepancy/staleness entry

### Step 4: Implicit pass (up to 3 iterations)

For each iteration:
1. Look for wiki claims that could be logically inconsistent with each other, with existing raw support in mind
2. Look for wiki claims where raw supports them but the raw context includes qualifications not carried into wiki
3. For each candidate contradiction:
   - Can I articulate the ≥3-step implication chain?
   - Is there a plausible resolving interpretation? If yes, is it stated openly in the report?
   - Would I still call this a contradiction after considering the resolving interpretation?
4. Emit surviving candidates as LOW report entries.

Between iterations, be honest about diminishing returns. If iteration 2 is mostly finding weaker versions of iteration 1, STOP EARLY.

### Step 5: Emit the contradiction report

Write to `reports/contradictions/<timestamp>-<batch-id>.md`. Structure:

```markdown
# Contradiction Report
- Batch: <batch-id>
- Scope: [raw and wiki paths audited]
- Independent execution confirmed: yes (this file was generated in a session without writer/auditor priming)
- Implicit iterations run: 1 | 2 | 3
- Early stop reason: (if <3 iterations)

## Explicit findings (HIGH confidence)

### Finding 1: <type: contradiction | discrepancy | staleness>
- **Wiki claim**: `working/concepts/observer.md` §"Thresholds" line 42: "threshold defaults to 0.7"
- **Raw claim**: `raw/2026-06-01/observer-spec.md` L88: "the observer threshold is 0.9 in production"
- **Confidence**: HIGH (both claims are literal)
- **Suggested resolutions**:
  1. Update wiki to 0.9 (if raw is authoritative and current)
  2. Update wiki to note both values with dates (if the value changed over time)
  3. Verify with source author (if unclear which is correct)
- **Reviewer notes**: This claim is cited by 3 other wiki pages; changing the wiki value cascades.

## Implicit findings (LOW confidence)

### Finding N: <type>
- **Claims involved**:
  - Wiki: `...`
  - Wiki: `...`
  - Raw: `...`
- **Implication chain**:
  1. Wiki claim A entails P
  2. Wiki claim B entails not-P (given raw context X)
  3. Therefore claims A and B are jointly inconsistent under raw's framing
- **Alternative interpretation (does NOT contradict)**: <if applicable, describe the reading that resolves the tension>
- **Confidence**: LOW
- **Suggested next step**: reviewer decision on which reading is intended

## Notes for other auditors
- Coverage gaps noticed (referred to wiki-coverage-audit): [list]
- Missing/weak relations (referred to wiki-relation-detect): [list]

## Notes for the writer
- If any of these findings become resolved contradictions requiring wiki updates, they will re-enter the pipeline via reviewer-triggered writer or patch batches.
```

## Report quality standards

### HIGH findings
- Both wiki and raw claims quoted verbatim
- Locations precisely cited
- Type correctly categorized (contradiction: opposite claims; discrepancy: different values without clear opposition; staleness: raw claim is a newer version of the wiki claim)
- At least one suggested resolution

### LOW findings
- Implication chain must be ≥3 steps and each step checkable
- Alternative resolving interpretation MUST be considered (if you cannot articulate one, that raises the finding's confidence — but often there IS a plausible resolution, and honesty about it is critical)
- If the resolving interpretation is more plausible than the contradiction reading, DROP the finding

### Findings you MUST NOT emit
- Contradictions between two wiki claims when raw is silent on the topic (that is not a raw-vs-wiki contradiction; it may still be a wiki self-consistency issue, but note it separately)
- Contradictions where the "contradiction" is Claude's inference vs raw's plain reading
- Contradictions where the resolving interpretation is at least as plausible as the contradiction reading
- "This wiki claim seems outdated" without a specific raw source dating a different version

## Handling ambiguity

Wiki-vs-raw contradictions often arise from ambiguity in raw. When you find an ambiguous raw source:
- Document the ambiguity in the report
- Report both readings, showing which reading (if any) would contradict wiki
- Do not pick a reading yourself

## Interaction with other skills

You reference outputs from coverage-audit and relation-detect only via the shared reports directory (not via prompt context). If you notice something that is not a contradiction but is worth another auditor's attention, note it in the "Notes for other auditors" section of your report.

You do NOT read the writer's compilation report as prompt context. If the writer flagged a potential contradiction, that will surface via reviewer awareness, not by contaminating your context.

## Reference files
- `shared/design-principles.md` — posture (§4), independent execution (§5), passes (§6)
- `shared/patch-schema.md` — evidence chain conventions (reports borrow these)
- `shared/wiki-structure.md` — where reports live, frontmatter citation conventions
- `shared/nvk-comparison.md` — how nvk/llm-wiki handles trust audits differently
