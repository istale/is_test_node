# LLM-Wiki Skill Suite

Five skills + one deterministic script for building and maintaining an LLM-compiled wiki with strict posture separation between writers and auditors.

## What's in this package

```
llm-wiki-skills/
├── README.md                          (this file)
├── shared/                            (referenced by all skills — read first)
│   ├── design-principles.md           (posture separation, storage tiers, passes)
│   ├── patch-schema.md                (JSON schema for all patches)
│   ├── wiki-structure.md              (directory layout, frontmatter conventions)
│   └── nvk-comparison.md              (delta vs nvk/llm-wiki prior art)
│
├── hermes-llm-wiki/                   (Writer)
│   └── SKILL.md
├── wiki-coverage-audit/               (Follower auditor)
│   └── SKILL.md
├── wiki-relation-detect/              (Interpreter auditor)
│   └── SKILL.md
├── wiki-contradiction-check/          (Evaluator auditor — independent execution)
│   └── SKILL.md
├── wiki-compactor/                    (Structural agent)
│   └── SKILL.md
│
└── scripts/
    └── patch_applier.py               (Deterministic patch application)
```

## The pipeline

```
raw material (immutable)
    ↓
hermes-llm-wiki  ──────────────────────► working/ pages
    │
    ├─► wiki-coverage-audit    ─► patch queue ─┐
    ├─► wiki-relation-detect   ─► patch queue ─┤
    └─► wiki-contradiction-check ► contradiction reports
                                                │
                                        reviewer approves
                                                │
                                                ▼
                                    patch-applier (script)
                                                │
                                                ▼
                                            working/
                                                │
                                    [trigger: patch count / structural score / schedule]
                                                │
                                                ▼
                                       wiki-compactor  ─► canonical/  ─► reader agents
                                                        └► canonical-archive/ (30d retention)
```

## Design principles you must understand before using

1. **Three storage tiers**: `raw/` (immutable) → `working/` (patch-mutated) → `canonical/` (reader-facing). Read `shared/design-principles.md` §1.

2. **Posture separation**: Writer, Follower, Interpreter, Evaluator, Structural — each with a distinct mental posture. Mixing degrades all of them. See §4.

3. **Contradiction check needs independent execution**: never run in the same session as the writer or other auditors on the same batch. See §5.

4. **Explicit vs implicit passes**: every auditor runs two passes with different confidence semantics. Implicit passes cap at 3 iterations. See §6.

5. **Deterministic patch application**: `patch_applier.py` is a script, not an LLM. Approved patches apply mechanically. See §7 and `patch-schema.md`.

## Installation

These SKILL.md files are portable — they work with any LLM agent system that supports skill loading (Claude Code, Claude.ai skills, custom agent frameworks).

**For Claude Code / Claude.ai**:
- Package each skill directory as a `.skill` archive
- Install via your skill management interface

**For custom agent systems**:
- Point your agent runtime at the `SKILL.md` files
- Ensure `shared/` is accessible to every skill

**For the patch applier script**:
- Requires Python 3.9+
- No external dependencies (stdlib only)
- Run: `python scripts/patch_applier.py --wiki-root /path/to/wiki --apply`

## Bootstrap a new wiki

```bash
mkdir -p my-wiki/{raw,working,canonical,canonical-archive,patches/{pending,approved,applied,rejected},reports/{coverage-audits,relation-audits,contradictions,compaction-logs,compilation-logs}}
echo '{}' > my-wiki/source_map.json

# Make raw/ immutable (Linux; use chflags on macOS)
chattr +i my-wiki/raw  # or filesystem-level RO, or content-addressed store
```

Then start with `hermes-llm-wiki` to ingest your first batch.

## Testing the patch applier

The included `scripts/patch_applier.py` has been smoke-tested against:
- Valid explicit HIGH patches (accepts)
- LOW confidence patches with insufficient evidence chain (rejects)
- Patches with missing anchors (rejects)
- Unapproved patches (rejects)
- Missing target pages (rejects)
- Missing raw citations (rejects)

To smoke-test yourself:
```bash
python scripts/patch_applier.py --wiki-root /path/to/wiki --dry-run
```

## Where this design came from

This suite was designed through iterative conversation about a common failure mode in LLM-wiki systems: patch-drift-vs-rewrite-drift, framing-bias-in-audit, and hallucination in implicit inference. The final architecture converges with `nvk/llm-wiki`'s published work in most respects but diverges on:

- Three separate audit skills (posture separation)
- Explicit/implicit pass separation with iteration cap
- Deterministic patch application (not LLM-driven lint fix)
- Three-tier storage with soft-delete retention

See `shared/nvk-comparison.md` for a full comparison.

## References

Research that informed the design:
- Karpathy's LLM-wiki concept (April 2026)
- `nvk/llm-wiki` v0.12.0 (github.com/nvk/llm-wiki)
- Cascading LLMs for salient event graph generation (arXiv 2406.18449) — iteration cap
- Streaming Knowledge Compilation (arXiv 2606.09877) — incremental + periodic recompile
- Planner-Auditor decoupling (Wu et al. 2026) — deterministic validation
- Position paper on responsible LLM-MAS (arXiv 2502.01714) — knowledge drift
- Hydropower regulatory extraction (arXiv 2511.11821) — hallucinated missingness
- GenRES (arXiv 2402.10744) — soft vs strict matching per confidence

## License

MIT-style: use, modify, redistribute. Attribution appreciated but not required.

## Feedback

This is a v1 skill package. Expected failure modes to watch for:
- Reviewer bandwidth as bottleneck (may need patch pre-filtering)
- Compactor over-aggressive merging (soft-delete window is the escape hatch)
- Contradiction check running in shared context accidentally (the refusal check should catch this, but monitor)
- Implicit pass hallucination rate (if reviewer rejects most implicit patches, tighten prompt guidance)

Iterate the SKILL.md files based on real reviewer feedback rather than up-front polish.
