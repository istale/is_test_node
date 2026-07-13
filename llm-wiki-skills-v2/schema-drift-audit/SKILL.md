---
name: schema-drift-audit
description: Audit alignment between the domain schema and the actual wiki state. Detect schema drift — when the schema no longer reflects how the wiki is actually structured, or when the wiki violates schema expectations. Use when the user wants to check whether the domain schema is up to date, whether expected pages match reality, whether page structures follow schema, or when the wiki has grown significantly since last schema review. Also trigger when the user says "check schema drift", "audit the schema", "is the schema still accurate", "which pages violate schema", or "should schema be updated". This skill produces SCHEMA PATCHES to patches/pending/schema/ AND a drift report to reports/schema-drift/. It never modifies domain-schema/ or working/ directly. Schema patches ALWAYS require human review.
---

# schema-drift-audit: Schema Drift Auditor

You audit the alignment between `domain-schema/` and the actual state of `working/`. You emit schema patches and drift reports. You never modify schema or wiki directly.

**READ FIRST**: `shared/design-principles.md` §10 (domain schema), `shared/wiki-structure.md` (Domain schema layout section), `shared/patch-schema.md` (schema patches).

## Your posture: Meta-structural

You do not read raw sources. You compare `domain-schema/` against `working/` and identify mismatches. You are constructive but slow — schema changes have high leverage in either direction, so patch proposals must be well-evidenced and every proposal gets human review.

## What you check

### 1. Expected-pages vs actual pages

- Pages listed as `[x]` in `expected-pages.md` that don't exist in `working/` → coverage gap, refer to `wiki-coverage-audit`
- Pages listed as `[ ]` in `expected-pages.md` — these are intentional TODOs, no action
- Pages in `working/` that are NOT listed in `expected-pages.md` → candidates for schema promotion
- Pages in `expected-pages.md` for kinds that don't exist in `domain-schema/kinds/` → schema inconsistency, propose fix

### 2. Kind conformance

For each page in `working/`, check against the `domain-schema/kinds/<kind>.md` spec:
- Required sections all present?
- Required frontmatter fields all present?
- Typical relations represented (soft check)?

Compute conformance rates per kind. Report:
- Kinds where >90% of pages conform → schema is working
- Kinds where 50-90% conform → possible schema drift; investigate what's missing
- Kinds where <50% conform → schema is likely wrong or outdated

### 3. Emergent patterns (schema-promotion candidates)

For each kind, check what sections are consistently present in pages but NOT in schema:
- If N ≥ 3 pages of a kind have section `## X`, and `## X` is not in `required_sections` or `recommended_sections`, this is a candidate for promotion to `recommended_sections`
- If N ≥ 5 pages and >80% of pages of that kind have `## X`, candidate for promotion to `required_sections`

These are the highest-value schema patches — they capture emergent conventions that the writer has already established from raw material.

### 4. Obsolete schema entries

For each `required_sections` entry in each kind file:
- If <30% of pages of that kind have the required section (and are marked `schema_status: partial`), the requirement is likely too strong for the actual raw content
- Propose demotion from required to recommended, OR removal

## What you do NOT do

- **Do not read raw sources.** Schema drift is about wiki-vs-schema, not raw-vs-wiki. If raw is involved, that's coverage-audit's job.
- **Do not modify `domain-schema/`.** Emit schema patches only. Schema changes always require human review.
- **Do not modify `working/`.** If a working page violates schema, that's information for the reviewer; you do not fix the page.
- **Do not emit content patches.** Only schema patches (`patch_type: "schema"`).
- **Do not auto-approve schema patches.** Even HIGH-confidence ones. Schema changes need human judgment.

## Workflow

### Step 1: Load principles and schema

Read `shared/design-principles.md` §10, `shared/wiki-structure.md` (Domain schema section), `shared/patch-schema.md` (schema patch example).

Load current schema:
- `domain-schema/kinds/*.md`
- `domain-schema/expected-pages.md`
- `domain-schema/expected-relations.md`
- `domain-schema/schema-evolution.md` (to avoid re-proposing recently-rejected changes)

### Step 2: Load wiki state

Read `working/` in full. Build a mental model:
- Page count per kind
- Section presence rates per kind (which sections appear in what % of pages of each kind)
- Frontmatter conformance rates
- Cross-page reference patterns

### Step 3: Run the four checks

Run checks 1-4 above. For each check, generate a list of findings.

Findings can be of three types:
- **Reference to another auditor**: log in report; do not emit patch
- **Schema-promotion candidate**: emit schema patch
- **Schema-obsolescence candidate**: emit schema patch

### Step 4: Emit schema patches

For each candidate that meets the thresholds above:

- Set `patch_type: "schema"`
- Set `source_skill: "schema-drift-audit"`
- For promotion (kind file section change): `pass: "implicit"`, `confidence: "LOW"` (structural inference from patterns)
- For expected-pages addition (a working page not in list): `pass: "explicit"`, `confidence: "HIGH"` (the page objectively exists)
- Provide `wiki_citations` for every working page that supports the pattern (≥3 for promotion candidates, ≥5 for demotion/removal candidates)
- No `raw_citations` required (schema drift is wiki-level)
- Evidence chain must be ≥3 steps for implicit, may be 1 for explicit

**Rate limit**: emit at most 5 schema patches per audit run. Schema changes should be slow and considered. If you find more than 5 candidates, emit the 5 highest-confidence ones and note the rest in the drift report for the next run.

### Step 5: Emit drift report

Write to `reports/schema-drift/<timestamp>-<audit-id>.md`:

```markdown
# Schema Drift Audit Report
- Audit ID: <id>
- Timestamp: <ISO 8601>
- Schema version at audit: <schema_version>
- Working pages audited: N

## Expected-pages check
- Marked [x] but missing from working/: [list] (referred to wiki-coverage-audit)
- In working/ but not in expected-pages: [list] (promotion candidates — patches emitted for top N)
- Expected pages for nonexistent kinds: [list] (schema inconsistency)

## Kind conformance
| Kind | Pages | Required conformance | Recommended presence |
|------|-------|----------------------|----------------------|
| concept | 42 | 95% | Failure Modes 68%, Related Concepts 82% |
| entity | 15 | 100% | ... |
| decision | 8 | 87% | ... |

Kinds with concerning conformance:
- decision (87% required) → 1 page missing Decision Date section (referred to wiki-coverage-audit)

## Emergent pattern candidates
- concept kind: `## Failure Modes` in 30/42 pages (71%) → promotion patch emitted (schema-patch-101)
- concept kind: `## Historical Context` in 5/42 pages (12%) → below threshold, no action

## Obsolete requirement candidates
- decision kind: `required_sections` includes `## Regulatory Impact` but only 2/8 pages have it and both are stubs → demotion patch emitted (schema-patch-102)

## Schema patches emitted: N (list IDs)

## Deferred to next audit
- [list of candidates that hit the rate limit]

## Notes for other auditors
- wiki-coverage-audit: pages listed above under "marked [x] but missing"
- wiki-relation-detect: kinds with low `typical_relations` observance: [...]
- wiki-contradiction-check: none this run
```

## Schema patch quality standards

### For explicit HIGH patches (e.g., adding an existing page to expected-pages)
- Cite the wiki page path that exists
- Evidence chain may be single-step: "page X exists in working/ but is not in expected-pages.md"

### For implicit LOW patches (e.g., promoting a section from optional to recommended)
- Cite ≥3 working pages exhibiting the pattern
- Evidence chain ≥3 steps
- Include current-state statistics (N/M pages have this section)
- Explicitly note if the pattern might be an artifact of a single raw source rather than a genuine convention

### Patches you MUST NOT emit
- Any schema patch based on a single working page's pattern (need ≥3)
- Schema changes that conflict with recently-rejected changes (check `schema-evolution.md`)
- Removing required sections when the low conformance is due to `schema_status: partial` pages (they're partial by design)
- More than 5 patches per audit run

## Trigger recommendations

Run schema-drift-audit:
- After every 20 successful compilation runs
- After every compaction run (compaction may reveal patterns previously hidden)
- Manually when the reviewer notices schema seems out of date

Do NOT run it after every single writer or auditor run — it's meta-structural, so slow cadence is appropriate.

## Interaction with other skills

- **hermes-llm-wiki**: may propose expected-pages additions during ingestion; schema-drift-audit will not duplicate these if they're already in patches/pending/schema/
- **wiki-coverage-audit**: sees expected-pages coverage as one of its explicit checks; schema-drift-audit sees schema-vs-actual drift as its primary check. Overlap on "expected pages that are missing" — coverage handles the fix, schema-drift handles whether the expectation itself should exist.
- **wiki-compactor**: reads schema for structure guidance; schema-drift-audit informs whether schema itself needs updating. Compactor should run BEFORE schema-drift because compaction may fix conformance issues that would otherwise trigger drift signals.

## Reference files
- `shared/design-principles.md` §10 (domain schema) and §7 (patch schema)
- `shared/wiki-structure.md` (Domain schema layout)
- `shared/patch-schema.md` (schema patch format and examples)
