# Comparison with nvk/llm-wiki

`nvk/llm-wiki` (github.com/nvk/llm-wiki) is a working LLM-wiki system inspired by Karpathy's April 2026 post. It ships as Claude Code, Codex, and OpenCode plugins. Version 0.12.0 as of June 2026.

This skill suite converges with nvk/llm-wiki on several patterns and diverges on others. This document explains the deltas so future skill authors understand the reasoning.

## Where we adopt from nvk/llm-wiki

### 1. Immutable raw layer
Their principle: "Raw is immutable — once ingested, sources are never modified."

We adopt this and go further — see `design-principles.md` §3 for the three enforcement levels (git hook, filesystem-level, content-addressed). Convention alone is insufficient because a compromised or drift-prone writer skill can silently mutate raw and break the audit chain.

### 2. Split librarian vs audit
Their `/wiki:librarian` handles focused wiki maintenance (staleness, quality). Their `/wiki:audit` is broader — "answers whether the user can trust the current knowledge... allowed to follow evidence wherever it leads. Starts from local wiki state but does not stop there if the local evidence is weak, stale, contradictory, or missing."

Our `wiki-compactor` is closest to their librarian (structural coherence). Our three audit skills together fill the role of their audit. We split into three because different postures (Follower/Interpreter/Evaluator) need different guardrails.

### 3. Explicit uncompiled-source coverage tracking
Their v0.8.6 changelog: "creates an explicit uncompiled-source coverage reference instead of leaving raw coverage gaps as endless suggestions."

This is directly the problem our `wiki-coverage-audit` addresses. We adopt their pattern of maintaining a `coverage-index.md` (or equivalent) that tracks which raw sources have been ingested to what depth.

### 4. Confidence scoring
They rate articles high/medium/low based on source quality and corroboration. We rate patches HIGH/LOW based on explicit/implicit provenance. Compatible enough that we can eventually merge scoring semantics.

### 5. Structural guardian
Their principle: "Structural guardian — auto-checks wiki integrity after operations, fixes trivial issues silently."

Our `wiki-compactor` does this on a scheduled/triggered basis rather than after every operation. We prefer the batched approach because it prevents partial-state confusion in downstream readers.

## Where we diverge and why

### 1. Three audit skills, not one
nvk/llm-wiki has a single `/wiki:audit` that "follows evidence wherever it leads." This works because their audit is a *human-triggered* trust check, not part of a continuous ingestion pipeline. In an autonomous pipeline, a single omnibus auditor mixes postures that should stay separate:
- Coverage checks are constructive (should X be added?)
- Contradiction checks are adversarial (does X conflict with Y?)
- Relation checks are inferential (does A relate to B?)

When these run in the same LLM turn, the constructive framing bleeds into the adversarial check. See `design-principles.md` §4 for the posture-separation rationale.

### 2. Explicit / implicit pass separation
nvk/llm-wiki does not explicitly separate what raw literally says from what raw implies. Our two-pass structure exists because implicit inference is a distinct hallucination risk (Cascading LLMs for salient event graph generation, 2024): "LLMs tend to infer event relations without explicit linguistic cues or strong evidence for logical inference. Consequently, LLMs predict far more relations than the gold standards, leading to low precision."

Separating the passes lets reviewers apply different scrutiny (see `design-principles.md` §8).

### 3. Deterministic patch application
nvk/llm-wiki uses LLM-driven `/wiki:lint --fix` for repairs. This works for structural fixes (frontmatter, indexes) but is risky for content patches — the LLM applying the patch has latitude to interpret it, potentially introducing drift.

Our `patch-applier.py` is a deterministic script. Once a patch is approved, application is mechanical. Rationale from Planner-Auditor decoupling research (Wu et al., 2026): "Separates generation (LLM-driven Planner) from deterministic rule-based validation (Auditor)."

### 4. Three-tier storage
nvk/llm-wiki has raw + wiki (two tiers). We have raw + working + canonical (three tiers) because:
- Working accumulates patches (readable but potentially incoherent)
- Canonical is periodic compaction (coherent but lags by one compaction cycle)
- Readers read canonical; writers write working

This addresses the patch-drift vs rewrite-drift tradeoff explicitly (Streaming Knowledge Compilation, arXiv 2606.09877). A single wiki tier forces a choice between the two failure modes.

### 5. Soft-delete with retention window
Our compactor soft-deletes content during compaction and hard-deletes only after a retention window. nvk/llm-wiki uses git for rollback, which is fine for source-code-style workflows but doesn't gracefully handle "the wiki said X yesterday, cite that version" queries. Soft-delete with retention gives us a queryable history without git-archaeology.

## What we should watch nvk/llm-wiki for

Their `/wiki:audit` allows "fresh research when needed" — auditor may fetch external material to resolve uncertainty. We do not currently allow this. If our contradiction check consistently reports "cannot resolve" for claims that need external verification, we should reconsider.

Their v0.12.0 feedback curator captures "high-signal user corrections, preferences, approvals, and plan acceptance." This is a category we don't currently model — our reviewer approvals are ephemeral. Worth considering whether reviewer feedback should feed back into skill improvement.

Their session-capture and rehydration workflow is orthogonal to our design but useful. If we build a long-running wiki system, we should adopt something similar.

## References

- nvk/llm-wiki v0.12.0 documentation: github.com/nvk/llm-wiki
- Cascading LLMs for salient event graph generation: arXiv 2406.18449
- Planner-Auditor decoupling: Wu et al., "LLM Data Auditor Framework" (2026)
- Streaming Knowledge Compilation: arXiv 2606.09877
- Hydropower regulatory extraction (hallucinated missingness): arXiv 2511.11821
- GenRES (soft matching for recall, strict for precision): arXiv 2402.10744
