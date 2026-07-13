# Patch Schema

This is the canonical patch schema. All auditors emit patches conforming to this schema. The `patch-applier` script validates and applies them. See `shared/design-principles.md` §7 for context.

## JSON Schema

```json
{
  "patch_id": "string (uuid v4)",
  "created_at": "string (ISO 8601)",
  "patch_type": "content | schema",
  "source_skill": "hermes-llm-wiki | wiki-coverage-audit | wiki-relation-detect | wiki-contradiction-check | schema-drift-audit",
  "pass": "explicit | implicit",
  "confidence": "HIGH | LOW",
  "target_page": "string (path relative to working/ for content patches, or domain-schema/ for schema patches)",
  "anchor": {
    "type": "section_heading | line_range | before_after",
    "value": "string (see anchor formats below)"
  },
  "operation": "insert_after | insert_before | replace | delete",
  "content": "string (markdown content, empty for delete)",
  "raw_citations": [
    {
      "raw_path": "string (path relative to raw/)",
      "line_range": [1, 10],
      "quoted_excerpt": "string (max 100 chars)"
    }
  ],
  "wiki_citations": [
    {
      "wiki_path": "string (path relative to working/)",
      "section": "string (heading text)",
      "issue": "string (why this location is relevant)"
    }
  ],
  "evidence_chain": ["string", "string", "string"],
  "reviewer_notes": "string (optional)",
  "review_status": "pending | approved | rejected",
  "reviewed_by": "string (optional)",
  "reviewed_at": "string ISO 8601 (optional)"
}
```

## Anchor formats

**section_heading**: value is the exact text of a markdown heading in `target_page`, e.g., `"## Type II Error Handling"`. The applier locates the heading and performs the operation relative to the section.

**line_range**: value is `"start:end"`, 1-indexed inclusive, e.g., `"42:58"`. The applier verifies the current content at those lines matches an included `expected_content_hash` field (required for line_range anchors). Fails safe if content has drifted.

**before_after**: value is a JSON object stringified:
```json
{"before": "text that precedes the target", "after": "text that follows"}
```
The applier locates the unique span between `before` and `after` and operates within it. Fails if the span is not unique.

## Operations

- `insert_after`: insert `content` after the anchor location
- `insert_before`: insert `content` before the anchor location
- `replace`: replace the anchor location (section, line range, or span) with `content`
- `delete`: remove the anchor location; `content` must be empty

## Validation rules

The applier REJECTS patches that:

1. Fail JSON schema validation
2. Reference a `target_page` that does not exist in the appropriate base (working/ for content patches, domain-schema/ for schema patches)
3. Reference a `raw_path` that does not exist in `raw/` (schema patches may omit raw_citations — see below)
4. Have `line_range` citations where the end < start or the range extends beyond the file
5. Have `confidence: LOW` but no `evidence_chain` or fewer than 3 chain steps
6. Have `pass: implicit` but no `wiki_citations`
7. Have `review_status != "approved"` (unauditable patches never apply)
8. Fail anchor location (drift since patch creation)
9. Have `patch_type: "schema"` but target a path outside `domain-schema/`
10. Have `patch_type: "content"` but target a path outside `working/`

## Schema patch specifics

Schema patches (`patch_type: "schema"`) differ from content patches:

- `target_page` is relative to `domain-schema/` (e.g., `"kinds/concept.md"`, `"expected-pages.md"`)
- `raw_citations` is OPTIONAL (schema evolution may be driven by patterns in wiki, not raw)
- `wiki_citations` is REQUIRED (schema changes must be justified by wiki state)
- Every schema patch, regardless of confidence, requires human review — no auto-approval
- Schema patches from `schema-drift-audit` typically have `confidence: LOW`; from `hermes-llm-wiki` proposing new expected pages, `confidence: HIGH` when raw explicitly introduces a new concept type

Example schema patch (writer proposing a new expected page):

```json
{
  "patch_id": "schema-patch-042",
  "created_at": "2026-07-07T14:22:11Z",
  "patch_type": "schema",
  "source_skill": "hermes-llm-wiki",
  "pass": "explicit",
  "confidence": "HIGH",
  "target_page": "expected-pages.md",
  "anchor": {
    "type": "section_heading",
    "value": "## Concepts"
  },
  "operation": "insert_after",
  "content": "\n- [ ] thermal-drift-compensation — technique for stabilizing PCM measurements against thermal drift\n",
  "raw_citations": [{
    "raw_path": "2026-07-05/pcm-thermal-notes.md",
    "line_range": [12, 34],
    "quoted_excerpt": "we now apply thermal drift compensation to all PCM..."
  }],
  "wiki_citations": [{
    "wiki_path": "domain-schema/expected-pages.md",
    "section": "## Concepts",
    "issue": "thermal-drift-compensation is a distinct concept introduced in recent raw but not listed"
  }],
  "evidence_chain": [
    "raw source explicitly introduces thermal-drift-compensation as a distinct technique",
    "no existing expected concept covers this",
    "concept-page kind is appropriate; proposing expected entry"
  ],
  "review_status": "pending"
}
```

Example schema patch (drift audit proposing new recommended section):

```json
{
  "patch_id": "schema-patch-101",
  "created_at": "2026-07-20T09:00:00Z",
  "patch_type": "schema",
  "source_skill": "schema-drift-audit",
  "pass": "implicit",
  "confidence": "LOW",
  "target_page": "kinds/concept.md",
  "anchor": {
    "type": "section_heading",
    "value": "recommended_sections:"
  },
  "operation": "insert_after",
  "content": "\n  - \"## Failure Modes\"\n",
  "raw_citations": [],
  "wiki_citations": [
    {"wiki_path": "working/concepts/observer-agent.md", "section": "## Failure Modes", "issue": "existing pattern"},
    {"wiki_path": "working/concepts/canonic-agent.md", "section": "## Failure Modes", "issue": "existing pattern"},
    {"wiki_path": "working/concepts/skeptic-agent.md", "section": "## Failure Modes", "issue": "existing pattern"}
  ],
  "evidence_chain": [
    "3 of 5 concept pages currently include a Failure Modes section",
    "these are not required by schema but are consistently produced by writer from raw",
    "promoting to recommended_sections reflects observed convention"
  ],
  "review_status": "pending"
}
```

## Example: explicit HIGH patch

```json
{
  "patch_id": "a3f4c8b0-...",
  "created_at": "2026-07-07T14:22:11Z",
  "source_skill": "wiki-coverage-audit",
  "pass": "explicit",
  "confidence": "HIGH",
  "target_page": "concepts/observer-agent.md",
  "anchor": {
    "type": "section_heading",
    "value": "## Failure Modes"
  },
  "operation": "insert_after",
  "content": "\n### Type III drift\n\nWhen the Observer starts to defer to the Skeptic's framing after N > 5 exchanges, its Type I error rate degrades sharply. See raw/2026-05-12/observer-skeptic-log.md lines 88-104.\n",
  "raw_citations": [{
    "raw_path": "2026-05-12/observer-skeptic-log.md",
    "line_range": [88, 104],
    "quoted_excerpt": "After exchange 6 the Observer began quoting the Skeptic..."
  }],
  "wiki_citations": [],
  "evidence_chain": ["raw explicitly names 'Type III drift' as a failure mode"],
  "review_status": "pending"
}
```

## Example: implicit LOW patch

```json
{
  "patch_id": "b8d2e1a4-...",
  "created_at": "2026-07-07T14:24:33Z",
  "source_skill": "wiki-relation-detect",
  "pass": "implicit",
  "confidence": "LOW",
  "target_page": "concepts/canonic-agent.md",
  "anchor": {
    "type": "section_heading",
    "value": "## Related Concepts"
  },
  "operation": "insert_after",
  "content": "\n- **Musical canon form** — The Leader/Follower/Evaluator triad is inspired by musical canon. See [[music-theory/canon-form]] for structural analogy.\n",
  "raw_citations": [{
    "raw_path": "2026-04-15/design-notes-canonic.md",
    "line_range": [12, 15],
    "quoted_excerpt": "inspired by musical canon form"
  }],
  "wiki_citations": [{
    "wiki_path": "concepts/canonic-agent.md",
    "section": "## Related Concepts",
    "issue": "section exists but does not mention musical canon origin"
  }, {
    "wiki_path": "music-theory/canon-form.md",
    "section": "(root)",
    "issue": "page exists but has no backlink from canonic-agent"
  }],
  "evidence_chain": [
    "raw/2026-04-15/design-notes-canonic.md L12-15 states the canonic agent is inspired by musical canon form",
    "wiki page music-theory/canon-form.md exists and describes the structural relationship of leader/follower voices",
    "canonic-agent.md's Related Concepts section does not mention this connection, creating an orphan cross-reference"
  ],
  "review_status": "pending"
}
```
