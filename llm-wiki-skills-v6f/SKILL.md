---
name: llm-wiki
description: "Karpathy's LLM Wiki, adapted for evidence preservation: build/query interlinked markdown KB with machine-verifiable provenance chains and verbatim expert-quote protection."
version: 4.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [wiki, knowledge-base, research, notes, markdown, rag-alternative, provenance]
    category: research
    related_skills: [obsidian, arxiv]
---

# LLM Wiki (Transport Edition)

═══════════════════════════════════════════════════════
## ⚠ TRANSPORT DISCIPLINE — HIGHEST PRIORITY
## (Overrides every other instruction in this file when they conflict)
═══════════════════════════════════════════════════════

**This wiki covers domains where we — the maintainers — do not have expertise.**

We are IT. We can guarantee that information present in the source ends up in the
wiki. We **cannot** verify domain explanations. A plausible-sounding but fabricated
explanation is invisible to us, will be trusted downstream, and causes real harm.

**Therefore the agent is a TRANSPORTER, not an author.**

### The three hard rules

**1. No statement, no sentence.**

Every substantive wiki line must cite a **statement** — an extracted, content-hashed
unit of source material (see Statement Layer below). If you are writing a sentence
you cannot back with an extracted statement — stop and delete it.

*Writing less is always better than writing without grounding.*

**2. Expert words are copied verbatim. Not one character changes.**

When a source contains a human expert's judgment, experience, or engineering
finding, transport it in a verbatim block, unchanged.

Forbidden, without exception:
- fixing typos (copy the typo)
- changing punctuation
- reordering words
- "polishing" or "making it clearer"
- summarizing or shortening
- translating

The only permitted operation is **copy and paste**. Verbatim integrity is
machine-checked by `tools/verify_wiki.py` — a substring test against the raw source
under a precisely defined canonical form (see SCHEMA template). Any alteration
fails the check.

*Why so strict:* experts choose words precisely. 「通常代表」≠「代表」.
"has already begun to degrade" ≠ "is degrading". You do not have the domain
knowledge to judge whether your rewrite distorts the meaning. **Rewriting an
expert's words destroys evidence.**

**3. Never fabricate to fill a structure.**

SCHEMA defines the *order and naming* of sections. It is not a fill-in-the-blank
exercise. If the source has no content for a section, **omit the section
entirely**. Do not write placeholder text. Do not write "TBD".

*An incomplete faithful record beats a complete fabrication.*

### Explicitly forbidden (these are real observed failures)

✗ **GHOST CITATION** — Writing content from your own knowledge, then attaching a
  citation marker so it looks grounded. **A false citation is worse than no
  citation: it deceives the human reviewer.** The statement layer makes this
  mechanically harder: a citation must resolve to an extracted statement, and the
  statement must trace to the source. Do not try to defeat this by forging
  statements — a forged verbatim statement fails the substring check, and a forged
  fact statement is a deliberate lie into an audit trail.

✗ **BENEVOLENT REWRITE** — Condensing an expert's "通常代表 seal 已經開始劣化"
  into "密封件劣化". You think you are tightening. You are distorting.

✗ **HELPFUL COMPLETION** — Source says "threshold: 400 ppm". You write
  "threshold: 400 ppm (a common industry safe limit)". The parenthetical is
  invented. Delete it.

✗ **GENERAL-KNOWLEDGE FILL** — A concept page has a "Definition" section and the
  source contains no definition, so you supply one from training data. Forbidden.
  No definition in source → no Definition section.

### Self-check after every paragraph

1. Does every substantive line cite a statement hash that exists in a statements
   file? → No: delete the line.
2. Did I add any causation, explanation, or evaluation the source did not state?
   → Yes: delete it.
3. Is every verbatim block character-for-character identical (canonical form) to
   the source? → No: fix my transcription (not the source).
4. Did I add anything to make the page look "complete" or "professional"?
   → Yes: delete it.
5. Does any citation point to a statement that does not actually contain that
   information? → That is a ghost citation. Delete it immediately.

═══════════════════════════════════════════════════════

Build and maintain a persistent, compounding knowledge base as interlinked markdown
files. Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f),
adapted for **evidence preservation** rather than knowledge synthesis.

Unlike traditional RAG (which rediscovers knowledge from scratch per query), the
wiki compiles knowledge once and keeps it current. Cross-references are already
there. Contradictions have already been flagged.

**Division of labor:** The human curates sources and supplies domain expertise.
The agent **extracts, transports, cross-references, files, and maintains
consistency**. The agent does not explain, interpret, or supplement.

## When This Skill Activates

Use this skill when the user:
- Asks to create, build, or start a wiki or knowledge base
- Asks to ingest, add, or process a source into their wiki
- Asks a question and an existing wiki is present at the configured path
- Asks to lint, audit, verify, or health-check their wiki
- References their wiki, knowledge base, or "notes" in a research context

## Wiki Location

**Location:** Set via `WIKI_PATH` environment variable (e.g. in `${HERMES_HOME:-~/.hermes}/.env`).
If unset, defaults to `~/wiki`.

```bash
WIKI="${WIKI_PATH:-$HOME/wiki}"
```

The wiki is just a directory of markdown files — open it in Obsidian, VS Code, or
any editor. No database required. The only tooling is `tools/verify_wiki.py`
(stdlib-only Python), installed into the wiki at init.

## Architecture: Four Layers

```
wiki/
├── SCHEMA.md           # Conventions, structure rules, domain config
├── index.md            # Sectioned content catalog with one-line summaries
├── log.md              # Chronological action log (append-only, rotated yearly)
├── tools/
│   └── verify_wiki.py  # Provenance-chain verifier (copied at init)
├── raw/                # Layer 1: Immutable source material
│   ├── articles/       # Web articles, clippings
│   ├── papers/         # PDFs, arxiv papers
│   ├── slides/         # Slide decks / training material (reviewed json, md)
│   ├── transcripts/    # Meeting notes, interviews
│   └── assets/         # Images, diagrams referenced by sources
├── statements/         # Layer 1.5: Extracted, content-hashed statements
│   └── (mirrors raw/ paths: statements/slides/foo.statements.md)
├── entities/           # Layer 2: Entity pages (people, orgs, products, models)
├── concepts/           # Layer 2: Concept/topic pages
├── analyses/           # Layer 2: Cross-domain scenario / root-cause pages
├── comparisons/        # Layer 2: Side-by-side analyses
└── queries/            # Layer 2: Filed query results worth keeping
```

**Layer 1 — Raw Sources:** Immutable bodies. The agent reads but never modifies.
**Layer 1.5 — Statements:** The extraction artifact. Every unit of information the
wiki is allowed to use, hashed and typed. This layer is what makes provenance
auditable instead of aspirational.
**Layer 2 — The Wiki:** Agent-owned markdown. Every substantive line cites a
statement hash.
**Layer 3 — The Schema:** `SCHEMA.md` defines structure, conventions, taxonomy, and
the provenance rules.

### The provenance chain

```
wiki line ──^[path#hash]──▶ statement ──substring check──▶ raw source body
             (resolvable)              (machine-verified
                                        for verbatim type)
```

A wiki line is grounded iff its citation resolves to a statement, and that
statement traces to the source. `verify_wiki.py` checks both links.

## Statement Layer — Extraction Artifacts

**This is the load-bearing change from v3.** Extraction is no longer an in-context
mental step; it produces a file that outlives the session and is auditable.

For every ingested raw source `raw/<sub>/<name>.md`, extraction writes
`statements/<sub>/<name>.statements.md`:

```markdown
---
source: raw/slides/co2-detector-training-042.md
source_sha256: <full digest of source canonical body at extraction time>
extracted: 2026-07-14
---

### stmt 3f9a1c2b8d4e | environmental-monitoring | verbatim | speaker: expert | loc: slide 12
> 這通常代表 seal 已經開始劣化,建議安排下次歲修時更換

### stmt 7b2e9f0a1c3d | environmental-monitoring | fact | loc: slide 12, table row 3
> threshold: 400 ppm

### stmt 9c4d2e1f0a3b | environmental-monitoring | verbatim | speaker: vlm | loc: slide 12 chart
> 判讀 (speaker: vlm): trend up
```

Header trailing segments are `key: value` pairs in any order. Known keys:

- `loc:` — where in the source (mandatory for `fact` type)
- `speaker:` — **who is talking**: `expert` (default; human domain expert),
  `vlm` (machine inference, e.g. chart interpretation), `vlm-approved`
  (machine inference confirmed in human review). Non-expert statements are
  transported with the same verbatim rigor, but may NEVER appear inside an
  `## Expert Finding (verbatim)` section — the verifier treats that as
  laundering machine inference into expert testimony (V3-LAUNDER).

**Statement types:**

- **verbatim** — expert words, copied exactly. The canonical text MUST be a
  character-for-character substring of the source canonical body.
  **Machine-verified. Hard guarantee.**
- **fact** — a value/specification assembled from source structure (a table cell
  plus its row label, a labeled diagram value). Cannot be a substring, so it
  carries a mandatory `loc:` hint precise enough for a human to find it in under
  a minute. **Hash-integrity only; human-verifiable via loc. Not a hard guarantee
  — be honest about this.**

Prefer `verbatim` whenever the source text allows it. Use `fact` only when the
information genuinely does not exist as contiguous source text.

**Canonical forms (normative — verify_wiki.py implements exactly this):**

- *Statement/block canonical text:* take the blockquote lines; strip one leading
  `>` and at most one following space from each line; strip trailing whitespace
  per line; join with `\n`; strip leading/trailing whitespace of the whole.
  No Unicode normalization — copy the source's exact codepoints.
- *Source canonical body:* everything after the closing `---` of the raw file's
  frontmatter (or the whole file if no frontmatter); `\r\n` and `\r` → `\n`.
- *Statement hash:* first 12 hex chars of SHA-256 over the UTF-8 canonical text.
  Compute with `python tools/verify_wiki.py hash --text "..."` or `--stdin`.

**Citation format (breaking change from v3):**

```
^[raw/slides/co2-detector-training-042.md#3f9a1c2b8d4e]
```

Path identifies the source, hash identifies the statement. A bare `^[path]` with
no hash is a v3 legacy marker — the linter flags it for migration.

Statements files are **append-only**: re-ingests may add statements, never edit or
delete existing ones (a wrong statement gets a correcting entry in the wiki page,
and is simply never cited again).

## Slide JSON Pipeline (rendered sources)

Sources arrive as per-slide JSON (schema: `summary`, `vlmInsight`, `table`,
`chart`) through a three-stage pipeline:

```
slide_script_extracted json → vlm_enriched json → human_reviewed json  ← SOT
```

**The human_reviewed json is the Source of Truth.** Humans edit the json fields
directly during review; whatever survives review is curated content, worth
transporting in full. Commit ALL THREE stages to Gitea — the diff between
vlm_enriched and human_reviewed is a free audit trail of what the human
corrected.

Do NOT extract from the JSON directly. JSON escaping (`\n`, `\uXXXX`, quoted strings) makes the
verbatim substring check meaningless. Instead:

**① Render deterministically:** `tools/render_slide.py` projects each slide JSON
into a markdown file in `raw/slides/`. The renderer is a pure script (not an
LLM), NFC-normalizes all text, and is **total** — every field except `summary`
appears in the body. Field mapping:

| JSON field   | Rendered as                          | Evidence status |
|--------------|--------------------------------------|-----------------|
| `vlmInsight` | `## vlmInsight (speaker: expert)`    | Expert words — verbatim-protected, the core asset |
| `table`      | `## table`, one plain line per row   | Verbatim-eligible facts (what experts report to managers) |
| `chart` axes | `## chart`, one line per axis        | Verbatim-eligible facts |
| `chart` 判讀 | `判讀 (speaker: vlm): ...`           | Rendered for completeness, **NOT extracted by default** — readers dig into the original slides for interpretation. The speaker tag remains as a safety net if one is ever extracted. |
| `summary`    | **frontmatter only**                 | Model-generated; structurally excluded from the canonical body → can never be cited. Usable for index one-liners. |

```bash
python tools/render_slide.py raw/slides/json/*.json --wiki "$WIKI" --out-dir raw/slides
```

**② Extract statements from the rendered md** (never from the JSON) — and for
this pipeline, extraction is DETERMINISTIC, no LLM involved:

```bash
python tools/extract_statements.py raw/slides/pcm-training-p012.md \
    --wiki "$WIKI" --domain equipment-maintenance
```

The script writes the statements file (append-only, hashes pre-computed) and
prints a **citation cheat sheet** — ready-made `^[path#hash]` strings the
executor model COPIES into wiki pages. The model never extracts, never hashes.
Extraction rules the script implements:

- **vlmInsight: extract 100%, always** — it is expert words that survived human
  curation. Machine-checked by V9.
- **table: extract every row** — tables on slides are what experts report to
  managers; every row is a clue. Machine-checked by V9.
- **chart axes: extract; chart 判讀: skip by default** — the wiki carries
  clues, not interpretation.
- **Prioritize correlation language** when writing wiki pages: any sentence
  relating two features (相關 / 影響 / 隨著 / 同時發生 / correlates / when X, Y)
  is the wiki\'s core payload. A cross-domain reader searching for "did A and B
  ever co-occur" must be able to hit it.

**③ The chain gains two machine-checked segments:**

```
wiki line ─V1─▶ statement ─V2/V3─▶ rendered md ─V7─▶ slide JSON ─(human review)─▶ slide
```

`verify --rerender` re-runs the renderer on each `source_json` and diffs the
body — hand-edits to rendered md and upstream JSON tampering are both caught.

**Purpose framing (drives all trade-offs here):** this wiki is a **finding
aid**, not a replacement for the original reports. Humans will re-read the
original when precision matters; what they fear is information existing but
being unfindable. Therefore: every rendered md carries `deck` + `page` in
frontmatter, every wiki page's Sources section points back to deck/page, and
verify enforces **coverage** (V8) — a rendered source with no statements file
is a findability gap and gets flagged. Fidelity of what is transported is
machine-guaranteed; completeness of transport is coverage-checked; the original
report remains the authority.

## Resuming an Existing Wiki (CRITICAL — do this every session)

When the user has an existing wiki, **always orient yourself before doing anything**:

① **Read `SCHEMA.md`** — understand the domain, conventions, tag taxonomy, and the
   domain knowledge-level table (which domains you may synthesize vs. must transport verbatim).
② **Read `index.md`** — learn what pages exist and their summaries.
③ **Scan recent `log.md`** — read the last 20-30 entries to understand recent activity.

```bash
WIKI="${WIKI_PATH:-$HOME/wiki}"
read_file "$WIKI/SCHEMA.md"
read_file "$WIKI/index.md"
read_file "$WIKI/log.md" offset=<last 30 lines>
```

Only after orientation should you ingest, query, or lint. This prevents duplicate
pages, missed cross-references, schema violations, and repeated work.

For large wikis (100+ pages), also run a quick `search_files` for the topic at hand
before creating anything new.

## Initializing a New Wiki

1. Determine the wiki path (from `$WIKI_PATH`, or ask; default `~/wiki`)
2. Create the directory structure above
3. Copy `tools/verify_wiki.py`, `tools/render_slide.py`, and `tools/extract_statements.py` from this skill into `$WIKI/tools/`; keep `EXECUTOR.md` at the wiki root for the executor model
4. Ask the user what domain(s) the wiki covers — **and critically, for each domain,
   ask whether they have expertise in it**. This drives the knowledge-level table.
5. Write `SCHEMA.md` customized to the domain (template below)
6. Write initial `index.md` with sectioned header
7. Write initial `log.md` with creation entry
8. Confirm the wiki is ready and suggest first sources to ingest

### SCHEMA.md Template

```markdown
# Wiki Schema

## Domain
[What this wiki covers]

## Domain Knowledge Levels  ← DRIVES TRANSPORT BEHAVIOR

For each domain, declare whether the maintainer has expertise. This determines
how the agent is allowed to transport content from that domain.

| Domain | Knowledge Level | Agent may... |
|--------|-----------------|--------------|
| company-product | authoritative | Synthesize statements into readable prose, cite at paragraph level. Maintainer can review. |
| process-engineering | reference-only | Transport statements verbatim only. One statement per line. NO elaboration. |
| environmental-monitoring | reference-only | Transport verbatim only. NO elaboration. |
| equipment-maintenance | reference-only | Transport verbatim only. NO elaboration. |
| (unknown / untagged) | reference-only | Default. The safe, non-elaborating default. |

**authoritative** — we have real knowledge here. The agent may reorganize and
connect statements into prose, because we can catch it if it goes wrong.
Even here it may NOT add facts absent from the cited statements.
⚠ Known, accepted trade-off: paragraph-level citation in authoritative domains is
where residual fabrication risk lives — the verifier can prove the cited
statements exist, but not that the prose says only what they say. This is
acceptable *only because* the maintainer can review these domains. Do not extend
paragraph-level citation to any reference-only domain.

**reference-only** — we lack domain knowledge. The agent records what the source
says, verbatim, and stops. It must NOT explain why a threshold is what it is, must
NOT add "which is the standard limit", must NOT supply general knowledge. **We
cannot verify domain claims here; a fabricated explanation is invisible harm.**
Reference-only wiki lines must be the statement's canonical text, unchanged —
the verifier checks equality.

If a bare value is all the source gives ("threshold: 400 ppm"), the wiki line is
that bare value plus its citation. That is complete and correct. Do not
"improve" it.

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `transformer-architecture.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages **when a genuine relationship exists
  in the sources**. Do not invent links to satisfy a quota — a link is a claim
  of relationship, and fabricated relationships are fabrications. Orphan pages
  are surfaced by lint for human review; an orphan is a prompt, not a violation.
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`

## Provenance Citations — MANDATORY, NO EXCEPTIONS

**Every substantive sentence or bullet carries a statement citation:**

    ^[raw/slides/co2-detector-training-042.md#3f9a1c2b8d4e]

The `sources:` field in frontmatter is **NOT sufficient** — it records which files
the page consulted; it does not prove that each line came from them.

Rules:
- Every bullet / every paragraph → must carry `^[path#hash]`
- A substantive line with no citation = violation → delete it
- The hash must resolve to a statement in the statements file, and the statement
  must actually contain that information. Citing a real-but-unrelated statement
  is a GHOST CITATION — the most serious violation, because it survives casual
  review.

## Verbatim Blocks — Expert Words

When a source contains a human expert's judgment, experience, or engineering
finding, preserve it unchanged:

    ## Expert Finding (verbatim)

    > [expert's exact words — not one character changed]

    ^[raw/slides/co2-detector-training-042.md#3f9a1c2b8d4e]

The block's canonical text must equal the cited verbatim statement's canonical
text — and therefore be a substring of the source. Both links are verified by
`tools/verify_wiki.py`.

**How to recognize expert words:**
- Sentences carrying judgment (「這通常代表...」, "in our experience...", "watch out for...")
- Sentences carrying causation (「因為...所以...」, "when X occurs, Y follows")
- Sentences carrying conditions (「除非...否則...」, "only if...")
- Sentences carrying experience/history (「過去三次事件都...」)
- Anything that reads like a person deliberately writing down a warning or finding

**When unsure whether something is expert words → treat it as expert words** and
use a verbatim block. Over-preserving is far safer than wrongly rewriting.

## Frontmatter

  ```yaml
  ---
  title: Page Title
  created: YYYY-MM-DD
  updated: YYYY-MM-DD
  type: entity | concept | analysis | comparison | query
  domains: [company-product, environmental-monitoring]   # from the table above
  tags: [from taxonomy below]
  sources: [raw/slides/co2-detector-training-042.md]
  has_verbatim: true | false      # does this page contain expert verbatim blocks
  # Optional quality signals:
  confidence: high | medium | low
  contested: true
  contradictions: [other-page-slug]
  ---
  ```

`domains:` matters — it tells a reader (and the linter) which parts of the page are
reference-only records vs. authoritative synthesis.

### raw/ Frontmatter

Raw sources ALSO get a small frontmatter block:

```yaml
---
source_url: https://example.com/article   # if applicable
ingested: YYYY-MM-DD
sha256: <hex digest of the canonical body below the frontmatter>
# added only on supersession:
superseded_by: raw/articles/example-v2.md
---
```

## Source Drift Policy

`raw/` bodies are immutable. When a re-ingest finds the live source changed
(recomputed sha256 ≠ recorded sha256 of the fetched content):

1. **Never edit the existing raw file's body.**
2. Save the new content as a NEW file with a version suffix
   (`example.md` → `example-v2.md`), with its own frontmatter and its own
   statements file.
3. Add `superseded_by:` to the OLD file's frontmatter. This is the ONLY permitted
   modification to an existing raw file, and it touches metadata, not the body.
4. **Existing wiki citations keep pointing at the old version.** They record what
   the evidence said when the page was written — retargeting them would rewrite
   history.
5. Lint reports pages citing superseded sources so the human decides whether the
   page needs updating against the new version.

If verify finds a raw body whose sha256 no longer matches its own frontmatter,
that is **tampering with Layer 1** — a CRITICAL finding, not a drift event.

## Tag Taxonomy
[Define 10-20 top-level tags for the domain. Add new tags here BEFORE using them.]

Rule: every tag on a page must appear in this taxonomy. If a new tag is needed,
add it here first, then use it. This prevents tag sprawl.

## Page Thresholds
- **Create a page** when an entity/concept appears in 2+ sources OR is central to one source
- **Add to existing page** when a source mentions something already covered
- **DON'T create a page** for passing mentions, minor details, or things outside the domain
- **Split a page** when it exceeds ~200 lines
- **Archive a page** when fully superseded — move to `_archive/`, remove from index

## Page Templates

⚠ **Sections are conditional on source content.** If the source contains nothing
for a section, **omit the section entirely**. Never write placeholder text. Never
fill a section from general knowledge.

### Entity Pages
Required:
- `## Sources` — the source list

Include ONLY if the source provides it:
- `## Expert Finding (verbatim)` — expert's own words, unchanged (highest priority section)
- `## Facts` — one statement per line, each with `^[path#hash]`
- `## Relationships` — `[[wikilinks]]` to related entities
- `## Description` — ONLY if the source actually describes the entity. Do not write
  an overview from your own knowledge.

### Concept Pages
Required:
- `## Sources`

Include ONLY if the source provides it:
- `## Expert Finding (verbatim)` — expert's own words, unchanged
- `## Definition` — **ONLY if the source explicitly defines the concept.** Do not
  supply a textbook definition from training data. No definition in source → no
  Definition section.
- `## Facts` — one per line, each with `^[path#hash]`
- `## Related` — `[[wikilinks]]`

**Removed from the old template (they invited fabrication, do not reintroduce):**
- ~~"Current state of knowledge"~~ — asks the agent to synthesize a field it does not know
- ~~"Open questions or debates"~~ — if the source didn't say it, the agent doesn't know it
- ~~"explanation"~~ — we transport; we do not explain

### Analysis Pages (cross-domain scenarios, root-cause records)
Required:
- `## Scenario` — the situation, from the source
- `## Data Points` — observations grouped by domain, each with `^[path#hash]`:

      - **company-product**: [may be synthesized] ^[path#hash]
      - **process-engineering** [reference-only]: statement text unchanged ^[path#hash]
      - **environmental-monitoring** [reference-only]: statement text unchanged ^[path#hash]

- `## Sources`

Include ONLY if the source provides it:
- `## Expert Finding (verbatim)` — the expert's analysis, unchanged. **This is
  usually the most valuable part of an analysis page.**
- `## Observed Correlation` — the relationship the human recorded. Mark whether it
  is stated in the source or is human experience. Never invent one.
- `## Root Cause` — ONLY if the source records one. If unknown, say so. **It is not
  the wiki's job to infer a root cause.**

### Comparison Pages
- What is being compared and why (from source)
- Dimensions of comparison (table; every cell with `^[path#hash]`)
- Sources

Do NOT write a "verdict" unless the source states one.

## Update Policy
When new information conflicts with existing content:
1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and citations
3. Mark in frontmatter: `contradictions: [page-name]`
4. Flag for user review in the lint report

Never silently overwrite. Never pick a winner in a reference-only domain — you lack
the knowledge to adjudicate.
```

### index.md Template

```markdown
# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: YYYY-MM-DD | Total pages: N

## Entities
<!-- Alphabetical within section -->

## Concepts

## Analyses

## Comparisons

## Queries
```

**Scaling rule:** When any section exceeds 50 entries, split into sub-sections. When
the index exceeds 200 entries, create `_meta/topic-map.md` grouping pages by theme.

### log.md Template

```markdown
# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, extract, update, query, lint, verify, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [YYYY-MM-DD] create | Wiki initialized
- Domain: [domain]
- Structure created with SCHEMA.md, index.md, log.md, tools/verify_wiki.py
```

## Core Operations

### 1. Ingest

When the user provides a source (URL, file, slide deck, paste):

① **Capture the raw source:**
   - URL → `web_extract` to markdown, save to `raw/articles/`
   - PDF → `web_extract`, save to `raw/papers/`
   - Slides / reviewed json → save to `raw/slides/`
   - Pasted text → appropriate `raw/` subdirectory
   - Name descriptively: `raw/slides/co2-detector-training-042.md`
   - **Add raw frontmatter** (`source_url`, `ingested`, `sha256` of the canonical
     body). On re-ingest: recompute, compare, skip if identical; if changed,
     follow the Source Drift Policy (new versioned file, never edit in place).

② **Discuss takeaways** with the user. (Skip in automated/cron contexts.)

③ **Check what already exists** — search `index.md` and `search_files` for existing
   pages covering the mentioned entities/concepts. This is the difference between a
   growing wiki and a pile of duplicates.

④ **EXTRACT TO FILE BEFORE YOU WRITE** ⚠ *(this ordering is mandatory and the
   extraction is a file, not a thought — this is what prevents ghost citations)*

   Write `statements/<sub>/<name>.statements.md` per the Statement Layer spec:

   a. Read the source and extract its substantive statements — values,
      specifications, facts, and expert quotes.
   b. **Identify expert words** → type `verbatim`, copied exactly.
   c. Everything assembled from structure (tables, labeled values) → type `fact`
      with a mandatory `loc:` hint.
   d. Tag each statement with its domain (from SCHEMA's knowledge-level table).
   e. Compute each hash: `python tools/verify_wiki.py hash --stdin`
   f. **Run `python tools/verify_wiki.py statements <statements-file>`** — this
      confirms every verbatim statement is a true substring of the source and
      every hash is correct, BEFORE any wiki prose exists.

   Only now do you write wiki content — and the wiki page is a **container for
   these extracted statements**, not a fresh composition.

   **The order matters absolutely.** Writing prose first and attaching citations
   afterwards is exactly how ghost citations are born. Statements come first;
   sentences are built from them.

⑤ **Write or update wiki pages:**
   - **Expert words → verbatim blocks** citing their verbatim statement.
   - **reference-only domain statements** → one per line, the statement's
     canonical text unchanged, each with `^[path#hash]`. **No elaboration.**
   - **authoritative domain statements** → may be synthesized into prose, with
     `^[path#hash]` citations on each paragraph. Still may not add facts absent
     from the cited statements.
   - **Omit any section the source does not support.**
   - **New entities/concepts:** create pages only if they meet the Page Thresholds
   - **Existing pages:** add new information, bump `updated`. On conflict, follow
     the Update Policy — never silently overwrite.
   - **Cross-reference** where genuine relationships exist (no quota)
   - **Tags:** only from the SCHEMA taxonomy
   - **Frontmatter:** set `domains:` and `has_verbatim:` accurately

⑥ **Verify, then self-audit:**
   - Run `python tools/verify_wiki.py verify --wiki "$WIKI"` and fix every
     CRITICAL/HIGH finding before finishing.
   - Run the five self-check questions from the Transport Discipline section.
   - It is normal and correct for a page to be short.

⑦ **Update navigation:**
   - Add new pages to `index.md` under the correct section, alphabetically
   - Update "Total pages" count and "Last updated" date
   - Append to `log.md`: `## [YYYY-MM-DD] ingest | Source Title`

⑧ **Report what changed** — list every file created or updated, and explicitly
   report: how many statements were extracted (verbatim vs fact), the verify
   result, and whether any section was omitted for lack of source content (this
   is a feature, report it plainly).

A single source can trigger updates across 5-15 wiki pages. This is normal and
desired — it's the compounding effect.

### 2. Query

① **Read `index.md`** to identify relevant pages.
② **For wikis with 100+ pages**, also `search_files` across all `.md` files.
③ **Read the relevant pages** using `read_file`.
④ **Answer from the wiki's compiled knowledge.** Cite the pages you drew from:
   "Based on [[page-a]] and [[page-b]]..."

   ⚠ **When answering from reference-only domain content:** report what the wiki
   records and stop. Do not explain the mechanism, do not add interpretation. If the
   user needs an explanation the wiki does not contain, say so plainly: "The wiki
   records X from [[page]], but contains no explanation of why. That knowledge lives
   with the domain expert."

   ⚠ **Quote expert verbatim blocks as quotes.** Do not paraphrase them in your
   answer. The exact wording is the value.

⑤ **File valuable answers back** — substantial comparisons or syntheses go in
   `queries/` or `comparisons/`. Filed pages obey all provenance rules (they cite
   statements, not other wiki pages, for substantive claims). Don't file trivial
   lookups.
⑥ **Update log.md** with the query and whether it was filed.

### 3. Verify (machine checks — run first, it's cheap)

```bash
python "$WIKI/tools/verify_wiki.py" verify --wiki "$WIKI"
```

The verifier checks the full provenance chain:

- **V1 — citation resolution:** every `^[path#hash]` resolves to a statement in
  the matching statements file. Unresolvable citation = CRITICAL.
- **V2 — verbatim statement integrity:** every `verbatim` statement's canonical
  text is a substring of its source's canonical body. Failure = CRITICAL
  (evidence was altered at extraction).
- **V3 — verbatim block integrity:** every `## Expert Finding (verbatim)` block's
  canonical text equals its cited verbatim statement. Failure = CRITICAL
  (evidence was altered at transport).
- **V4 — hash integrity:** every statement's recorded hash matches its text.
- **V5 — raw immutability:** every raw file's canonical body matches its own
  frontmatter `sha256`. Mismatch = CRITICAL (Layer 1 tampering), unless the file
  is marked `superseded_by` and untouched otherwise.
- **V6 — legacy markers:** bare `^[path]` citations without a hash (v3 format) —
  flagged for migration.
- **V7 — render integrity** (rendered sources): the `source_json` exists and its
  sha256 matches; with `--rerender`, the renderer is re-run and the body diffed.
  Mismatch = CRITICAL (hand-edited rendered md, or upstream JSON tampering).
- **V8 — extraction coverage:** every raw source has a statements file. A
  rendered-but-unextracted source is invisible to the wiki — a findability gap.
  MEDIUM.
- **V9 — extraction completeness** (rendered sources): every non-empty line in
  the `vlmInsight` and `table` sections of a rendered source is covered by a
  statement. The human-reviewed JSON is the SOT — everything in it survived
  curation, so a missed line is a lost clue, the primary failure this wiki
  exists to prevent. HIGH.
- **V3-LAUNDER:** an `## Expert Finding (verbatim)` block citing a
  `speaker: vlm` / `vlm-approved` statement — machine inference presented as
  expert words. HIGH.
- **V10 — orphan expert statements:** a `speaker: expert` verbatim statement
  cited by no wiki page. The clue exists in `statements/` but is invisible to
  a reader browsing the wiki — the typical omission-drift of a small executor
  model. MEDIUM.

### 4. Lint (agent judgment + heuristics — run after verify)

① **Orphan pages** (no inbound `[[wikilinks]]`) — surfaced for human review, not
   auto-fixed. Never add links just to clear this finding.
② **Broken wikilinks:** `[[links]]` pointing to nonexistent pages.
③ **Index completeness:** every wiki page appears in `index.md`.
④ **Frontmatter validation:** required fields present; tags in taxonomy.
⑤ **Provenance completeness:** every substantive line carries a `^[path#hash]`
   citation. A "substantive line" = a bullet or paragraph with more than a few
   words of real content. Headings, blank lines, and `[[wikilink]]`-only lines
   are exempt. Uncited substantive lines must be sourced or deleted.
⑥ **Ghost-citation screen (heuristic):** for cited lines in authoritative-domain
   prose, check lexical overlap between the line and its cited statements.
   **Tokenization must be script-aware:** character bigrams for CJK runs,
   lowercase word tokens for Latin runs, union for mixed text. Naive
   space-delimited word overlap is useless on Chinese content — do not use it.
   Near-zero overlap = likely fabrication → flag for human review.

   ⚠ This check is a **filter, not a proof**. False positives (legitimate
   paraphrase) and false negatives (hallucination reusing source vocabulary) both
   occur. Only V2/V3 and reference-only equality are hard guarantees.
⑦ **Reference-only equality:** lines in reference-only domain sections must equal
   their cited statement's canonical text. Deterministic — any difference is a
   violation.
⑧ **Fabrication-prone sections:** flag pages containing "Current state of
   knowledge", "Open questions", "Overview", or similar — removed from templates
   because they invite general-knowledge fill.
⑨ **Superseded-source citations:** pages citing a raw file marked
   `superseded_by:` — the human decides whether to update against the newer
   version.
⑩ **Stale content:** pages whose `updated` is >90 days older than the most recent
   source mentioning the same entities.
⑪ **Contradictions:** surface all pages with `contested: true` or `contradictions:`.
⑫ **Page size:** flag pages over 200 lines.
⑬ **Tag audit:** flag tags not in the SCHEMA taxonomy.
⑭ **Log rotation:** rotate if log.md exceeds 500 entries.

⑮ **Report findings** grouped by severity:

   **CRITICAL** — any verify failure (V1-V5), missing provenance (⑤), reference-only inequality (⑦)
   **HIGH** — high-confidence ghost citations (⑥), broken links (②)
   **MEDIUM** — orphans (①), fabrication-prone sections (⑧), superseded citations (⑨), contested pages (⑪), legacy markers (V6)
   **LOW** — stale content, page size, tags, index gaps

   Verbatim tampering and missing provenance outrank everything else. A broken
   wikilink is cosmetic; a rewritten expert quote is destroyed evidence.

⑯ **Append to log.md:** `## [YYYY-MM-DD] lint | N issues (C:n H:n M:n L:n)`

## Working with the Wiki

### Searching

```bash
search_files "transformer" path="$WIKI" file_glob="*.md"          # by content
search_files "*.md" target="files" path="$WIKI"                    # by filename
search_files "tags:.*alignment" path="$WIKI" file_glob="*.md"      # by tag
read_file "$WIKI/log.md" offset=<last 20 lines>                    # recent activity
```

### Bulk Ingest

1. Read all sources first
2. **Write statements files for all sources** (step ④) and verify them, before
   writing any wiki content
3. Identify all entities and concepts across all sources
4. Check existing pages for all of them (one search pass, not N)
5. Create/update pages in one pass
6. Run verify once at the end; fix findings
7. Update index.md once at the end
8. Write a single log entry covering the batch

The extract-before-write rule applies to batches too. Extract everything, then write.

### Migrating a v3 wiki

1. Run verify — it flags every bare `^[path]` legacy marker (V6).
2. Per source, extract a statements file covering the content its wiki pages cite.
3. Rewrite legacy markers to `^[path#hash]`, checking each line actually matches
   a statement. **Lines that match nothing are suspected v3-era ghost citations —
   list them for the human; do not invent a statement to legitimize them.**
4. Migrate incrementally, page by page. Log each migration.

### Archiving

1. Create `_archive/` if needed
2. Move the page preserving its path (`_archive/entities/old-page.md`)
3. Remove from `index.md`
4. Update pages that linked to it — replace wikilink with plain text + "(archived)"
5. Log the archive action

**Never archive a page containing verbatim expert blocks without asking the user.**
Those blocks are primary evidence; superseding the surrounding analysis does not
make the expert's words worthless.

### Obsidian Integration

The wiki directory works as an Obsidian vault out of the box: `[[wikilinks]]` render
as clickable links, Graph View visualizes the network, YAML frontmatter powers
Dataview, and `raw/assets/` holds images referenced via `![[image.png]]`.

For best results:
- Set Obsidian's attachment folder to `raw/assets/`
- Enable "Wikilinks" in settings (usually on by default)
- Install Dataview for queries like `TABLE domains FROM "concepts" WHERE has_verbatim = true`

If using the Obsidian skill alongside this one, set `OBSIDIAN_VAULT_PATH` to the same
directory as the wiki path.

### Untrusted Executor (small local models)

This skill may be executed by a small local model (e.g. a ~27B model on an
air-gapped machine). **The architecture assumes the executor drifts.** Drift is
handled in three layers:

**Detect — the verifier is the trust anchor, not the model.** Everything that
matters is machine-checked (V1-V10) and gated in CI. A drifting executor
produces rejected commits, not corrupted wikis. Never rely on the model's
self-checks: agent-side lint is executed by the same model that drifts.
Anything load-bearing must live in `verify_wiki.py`, not in prose instructions.

**Reduce — shrink the judgment surface.** Every step removed from the model is
drift that cannot happen:

- Extraction is scripted (`extract_statements.py`) — the model never extracts,
  never computes hashes, only COPIES ready-made citations from the cheat sheet.
- Feed the model `EXECUTOR.md` (the condensed operator card), NOT this file.
  This file is the spec for humans and audits; a small model given 700 lines
  will lose the discipline section by the time it writes page 3.
- Per-task minimal context: one source's cheat sheet + the few relevant
  existing pages. Never the whole wiki.
- Greedy decoding / temperature 0 for all transport work.

**Retry loop — bounded, then escalate:**

```
render → extract (script) → model composes pages → verify
   └─ findings? feed the finding list back to the model, max 3 retries
        └─ still failing? park the ingest in a branch, escalate to human
```

The model fixes ONLY what findings name, by re-copying from the cheat sheet.

**Canary regression:** keep a small fixture (source + expected statements +
expected verify result) in the repo. Run the executor through it periodically
— catches model-version or prompt drift over time, independent of live ingests.

### Gitea (air-gapped deployment)

The wiki lives on an air-gapped machine with a local Gitea service. Both tools
are stdlib-only Python by design — no pip, no npm, no network needed. The local
Obsidian desktop app works offline as a reader; do NOT use Obsidian Sync or any
cloud service.

**Repo layout:** the wiki directory is the repo. Commit all three JSON pipeline
stages (`slide_script_extracted`, `vlm_enriched`, `human_reviewed`) alongside
`raw/`, `statements/`, and the wiki pages — the diff between stages is the audit
trail of human review.

**verify as a CI gate (this is how findings get an owner):**

```yaml
# .gitea/workflows/verify.yml — CRITICAL findings block the merge
on: [push, pull_request]
jobs:
  verify:
    runs-on: local
    steps:
      - uses: actions/checkout@v4
      - run: python3 tools/verify_wiki.py verify --wiki . --rerender
```

An ingest commit that fails verify never reaches the main branch. Nobody
triages a report queue; bad transports simply cannot land. If Gitea Actions is
unavailable on the air-gapped box, the same command in a `pre-receive` hook
achieves the identical gate.

**Enforcing the append-only / immutability rules via Git:** protect the main
branch, and add a CI step that fails if a diff modifies or deletes existing
lines in `statements/**` or touches bodies under `raw/**` (additions of new
files are fine). What SKILL.md declares as discipline, the repo then enforces
as mechanism.

## Pitfalls

**Transport violations (the ones that actually hurt):**

- **Never rewrite expert words** — not even to fix a typo. Copy them exactly. If you
  "improved" an expert's sentence, you destroyed evidence — and V2/V3 will catch you.
- **Never cite a statement that doesn't contain the content** — a ghost citation
  looks compliant and passes casual review. It is the single most damaging thing
  this agent can do.
- **Never forge a statement to legitimize prose you already wrote** — that is a
  ghost citation with extra steps, and a lie planted directly into the audit trail.
- **Never fill a section from general knowledge** — if the source has no definition,
  the page has no Definition section. Omission is correct.
- **Never explain a reference-only domain** — record the statement; stop. The
  maintainer cannot check your explanation, which is exactly why you must not offer one.
- **Never write prose first and cite afterwards** — statements file first, then
  sentences built from statements. The order is the safeguard.
- **A short page is not a failure** — it is an honest one. Do not pad.

**Wiki hygiene:**

- **Never modify raw/ bodies** — sources are immutable. Corrections go in wiki
  pages; drift goes through the Source Drift Policy.
- **Statements files are append-only** — bad statements are abandoned, not edited.
- **Always orient first** — read SCHEMA + index + recent log before any operation.
- **Always update index.md and log.md** — they are the navigational backbone.
- **Don't create pages for passing mentions** — follow the Page Thresholds.
- **Link on genuine relationships, not quotas** — orphan review belongs to lint.
- **Frontmatter is required** — it enables search, filtering, staleness detection.
- **Tags must come from the taxonomy** — add new tags to SCHEMA.md first.
- **Keep pages scannable** — split pages over 200 lines.
- **Ask before mass-updating** — confirm scope if an ingest would touch 10+ pages.
- **Rotate the log** — rename to `log-YYYY.md` past 500 entries.
- **Handle contradictions explicitly** — note both claims with dates, mark in
  frontmatter, flag for review. Never adjudicate a reference-only domain yourself.

## What This Skill Guarantees (and what it doesn't)

**Hard guarantees (deterministic, verified by `tools/verify_wiki.py`):**
- Verbatim statements are character-for-character substrings of their source
  (canonical form, precisely defined). (V2)
- Wiki verbatim blocks equal their cited verbatim statements — hence trace,
  unaltered, all the way to the source. (V3)
- Every citation resolves to a real extracted statement. (V1)
- Reference-only wiki lines equal their cited statements. (lint ⑦)
- Raw source bodies have not been altered since ingest. (V5)
- Rendered sources faithfully reflect their slide JSON, and the JSON itself is
  unaltered since render. (V7, with `--rerender`)
- Every ingested source has been extracted — no silent findability gaps. (V8)
- Every vlmInsight and table line in a rendered source has been transported —
  no lost clues. (V9)
- Machine inference (speaker: vlm) cannot be presented as expert findings. (V3-LAUNDER)
- Every expert statement surfaces in at least one wiki page — no orphaned clues. (V10)

**Structural safeguards (reduce but do not eliminate risk):**
- Extract-to-file-before-write makes ghost citations require deliberate forgery
  rather than mere sloppiness
- Mandatory per-line statement citations remove the "frontmatter is enough" loophole
- Removed fabrication-prone section templates remove the invitation to invent
- Reference-only domain rules forbid elaboration where the maintainer cannot check

**No guarantee (heuristic or human-dependent):**
- `fact`-type statements are hash-stable and locatable via `loc:`, but their
  faithfulness to the source is human-verified, not machine-verified.
- Authoritative-domain prose provably cites real statements, but whether the prose
  says *only* what the statements say is checked heuristically (lint ⑥) and by
  the maintainer. This residual risk is confined, by design, to domains the
  maintainer can review.

Be honest about this boundary when reporting to the user. Claiming a clean verify
means "nothing is fabricated" would itself be a fabrication — it means "every
verbatim chain is intact and every citation resolves", no more, no less.

## Related Tools

[llm-wiki-compiler](https://github.com/atomicmemory/llm-wiki-compiler) is a Node.js
CLI that compiles sources into a concept wiki with the same Karpathy inspiration.
It's Obsidian-compatible. Trade-offs: it owns page generation (replacing agent
judgment on page creation) and is tuned for small corpora, and it does **not**
implement verbatim preservation or mandatory provenance. Use this skill when
evidence fidelity matters; use llmwiki for batch compile of a source directory where
synthesis is acceptable.
