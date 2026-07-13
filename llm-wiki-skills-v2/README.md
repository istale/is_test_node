# LLM-Wiki Skill Suite v2

Six skills + one deterministic script for building and maintaining an LLM-compiled wiki with strict posture separation between writers, auditors, and schema governance.

**What changed from v1**: added `domain-schema/` as a wiki-governed structure specification, added `schema-drift-audit` skill, added `patch_type: content | schema` to distinguish content patches from schema patches, updated writer and coverage auditor to read schema.

## What's in this package

```
llm-wiki-skills/
├── README.md                          (this file)
├── shared/                            (referenced by all skills — read first)
│   ├── design-principles.md           (§1-11 — see especially §10 for schema)
│   ├── patch-schema.md                (JSON schema, content vs schema patches)
│   ├── wiki-structure.md              (directory layout including domain-schema/)
│   └── nvk-comparison.md              (delta vs nvk/llm-wiki prior art)
│
├── hermes-llm-wiki/                   (Writer — reads schema, may propose schema)
│   └── SKILL.md
├── wiki-coverage-audit/               (Follower — also checks expected-pages coverage)
│   └── SKILL.md
├── wiki-relation-detect/              (Interpreter — unchanged from v1)
│   └── SKILL.md
├── wiki-contradiction-check/          (Evaluator — independent execution, unchanged)
│   └── SKILL.md
├── wiki-compactor/                    (Structural — respects schema in canonical)
│   └── SKILL.md
├── schema-drift-audit/                (NEW — audits schema alignment with wiki)
│   └── SKILL.md
│
└── scripts/
    └── patch_applier.py               (Deterministic patch application, v2)
```

## The pipeline (v2)

```
raw material (immutable)
    ↓
hermes-llm-wiki ─────────► working/ pages (structure follows domain-schema/)
    │                              │
    │                              └► may emit schema patch (new expected page / kind)
    │
    ├─► wiki-coverage-audit ──► content patch queue
    │       │  (also checks expected-pages coverage)
    │       └► may refer to schema-drift-audit for schema issues
    │
    ├─► wiki-relation-detect ─► content patch queue
    │
    └─► wiki-contradiction-check ► contradiction report (independent execution)

    Independently:
    schema-drift-audit ─► schema patch queue + drift report
                        (audits wiki vs schema alignment)
                                        │
                        reviewer approves (content or schema)
                                        │
                                        ▼
                                patch-applier (script, routes by patch_type)
                                        │
                            ┌───────────┴───────────┐
                            ▼                       ▼
                       working/ update         domain-schema/ update
                            │
                    [trigger: patch count / structural score / schedule]
                            │
                            ▼
                     wiki-compactor  ─► canonical/  ─► reader agents
                                    └► canonical-archive/ (30d retention)
```

## Domain schema at a glance

The wiki has a `domain-schema/` directory that describes the EXPECTED shape of the wiki. It is:
- **Not a prompt** — it's markdown in the repo, versioned, diffable
- **Not one-time bootstrap** — it evolves via schema patches
- **Not a facts source** — raw remains authoritative for facts; schema is only about structure

Bootstrap flow:
1. Hand-author `domain-schema/kinds/{concept,entity,decision,project}.md` with required + recommended sections for each kind
2. Hand-author `domain-schema/expected-pages.md` with the pages you know your domain needs
3. Ingest raw with `hermes-llm-wiki` — writer follows schema for structure, cites raw for content

Evolution flow:
1. Writer encounters new content that doesn't fit schema → proposes schema patch
2. `schema-drift-audit` periodically checks alignment → proposes schema patches for emergent patterns / obsolete requirements
3. Reviewer approves schema patches → `patch_applier` applies them to `domain-schema/`
4. `schema-evolution.md` logs the change

Schema patches ALWAYS require human review. No auto-approval, even for HIGH confidence.

## Design principles you must understand before using

1. **Three storage tiers**: `raw/` (immutable) → `working/` (patch-mutated content) → `canonical/` (reader-facing, produced by compaction). Read `shared/design-principles.md` §1.

2. **Domain schema as governed structure**: `domain-schema/` describes expected wiki shape; changes go through schema patches with mandatory human review. See §10.

3. **Posture separation**: Writer, Follower, Interpreter, Evaluator, Structural, Meta-structural — six postures, six skills. Mixing degrades all of them. See §4.

4. **Contradiction check needs independent execution**: never run in the same session as the writer or other auditors on the same batch. See §5.

5. **Explicit vs implicit passes**: every auditor runs two passes with different confidence semantics. Implicit passes cap at 3 iterations. See §6.

6. **Deterministic patch application**: `patch_applier.py` is a script, not an LLM. Approved patches apply mechanically. Content patches modify `working/`; schema patches modify `domain-schema/`. See §7 and `patch-schema.md`.

## Bootstrap a new wiki

```bash
# Create directory structure
mkdir -p my-wiki/{raw,working,canonical,canonical-archive}
mkdir -p my-wiki/domain-schema/kinds
mkdir -p my-wiki/patches/pending/content my-wiki/patches/pending/schema
mkdir -p my-wiki/patches/approved/content my-wiki/patches/approved/schema
mkdir -p my-wiki/patches/applied/content my-wiki/patches/applied/schema
mkdir -p my-wiki/patches/rejected/content my-wiki/patches/rejected/schema
mkdir -p my-wiki/reports/contradictions my-wiki/reports/coverage-audits
mkdir -p my-wiki/reports/relation-audits my-wiki/reports/schema-drift
mkdir -p my-wiki/reports/compaction-logs my-wiki/reports/compilation-logs
echo '{}' > my-wiki/source_map.json

# Bootstrap minimal schema (edit these for your domain)
cat > my-wiki/domain-schema/kinds/concept.md << 'EOF'
---
schema_version: 2026-07-07
kind: concept
---
# Concept pages
## required_sections
- "# {title}"
- "## Sources"
EOF

cat > my-wiki/domain-schema/expected-pages.md << 'EOF'
# Expected Pages
## Concepts
- [ ] your-first-concept
EOF

cat > my-wiki/domain-schema/schema-evolution.md << 'EOF'
# Schema Evolution Log
## 2026-07-07 — Initial bootstrap
EOF

# Make raw/ immutable (Linux; use chflags on macOS)
chattr +i my-wiki/raw
```

Then start with `hermes-llm-wiki` to ingest your first batch. It will read `domain-schema/` for structure guidance.

## Installation

These SKILL.md files are portable — they work with any LLM agent system that supports skill loading (Claude Code, Claude.ai skills, custom agent frameworks).

**For Claude Code / Claude.ai**: Package each skill directory as a `.skill` archive and install via your skill management interface.

**For custom agent systems**: Point your agent runtime at the `SKILL.md` files. Ensure `shared/` is accessible to every skill.

**For the patch applier script**: Requires Python 3.9+, no external dependencies. Run: `python scripts/patch_applier.py --wiki-root /path/to/wiki --apply`

## Testing status (v2 smoke tests)

The included `scripts/patch_applier.py` was smoke-tested against:
- Valid explicit HIGH content patch: applied to `working/`, `source_map.json` updated
- Valid implicit LOW schema patch: applied to `domain-schema/`, `source_map.json` NOT updated
- Content patch missing `raw_citations`: rejected with correct reason
- Schema patch missing `wiki_citations`: rejected with correct reason
- Content patch with insufficient evidence chain: rejected (v1 behavior preserved)
- Applied patches routed to `patches/applied/{content,schema}/`
- Rejected patches routed to `patches/rejected/{content,schema}/`
- V1 flat `patches/approved/` layout still supported for backward compatibility

## When to run what

| When | What |
|------|------|
| New raw arrives | `hermes-llm-wiki` |
| After ingestion batch | `wiki-coverage-audit` (Pass 1a raw-to-wiki, Pass 1b expected-pages) |
| Weekly (or after batch) | `wiki-relation-detect` |
| Weekly, independent session | `wiki-contradiction-check` |
| After ~20 ingestion batches | `wiki-compactor` |
| After ~20 ingestion batches, after compaction | `schema-drift-audit` |
| After reviewer approves patches | `patch_applier.py --apply` |

## Where this design came from

This suite was designed through iterative conversation about failure modes in LLM-wiki systems: patch-drift-vs-rewrite-drift, framing-bias-in-audit, hallucination in implicit inference, and now: bootstrap vs emergent schema. The final architecture converges with `nvk/llm-wiki`'s published work in most respects but diverges on:

- Six skills, not one omnibus (posture separation)
- Explicit/implicit pass separation with iteration cap
- Deterministic patch application (not LLM-driven lint fix)
- Three-tier storage with soft-delete retention
- **Domain schema as governed wiki content** (not prompt, not config) — new in v2

See `shared/nvk-comparison.md` for the full comparison.

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
- Schema evolution in incremental KG construction (Ilyas et al. 2022, Saga)

## License

MIT-style: use, modify, redistribute. Attribution appreciated but not required.

## Migration from v1

If you have a v1 wiki:

1. Create `domain-schema/` directory (see bootstrap above); hand-write your kinds and expected-pages
2. Reorganize `patches/` subdirs into `content/` and `schema/` (v2 patch_applier accepts flat v1 layout as fallback, so this is optional)
3. Update any custom tooling to include `patch_type: "content"` in patches — v1 patches without this field will be REJECTED by the v2 validator since `patch_type` is now a required field. Add it to any patches queued during v1
4. Install the new `schema-drift-audit` skill
5. Run `schema-drift-audit` once to bootstrap the drift report; use findings to refine your schema

Existing v1 skills (`hermes-llm-wiki`, `wiki-coverage-audit`) are replaced by v2 versions that read schema. Other three skills are unchanged.
