#!/usr/bin/env python3
"""
patch_applier.py — Deterministic patch application for the llm-wiki suite.

This is a SCRIPT, not a skill. It runs mechanically on approved patches.
See shared/patch-schema.md for the patch format and shared/design-principles.md
for the design rationale.

Usage:
    python patch_applier.py --wiki-root /path/to/wiki --dry-run
    python patch_applier.py --wiki-root /path/to/wiki --apply
    python patch_applier.py --wiki-root /path/to/wiki --patch-id <uuid>

Behavior:
    - Reads patches from patches/approved/
    - Validates each against the schema
    - Applies to working/ atomically (all or nothing per patch)
    - Moves successful patches to patches/applied/
    - Moves failed patches to patches/rejected/ with a failure reason
    - Updates source_map.json to reflect provenance changes

This script MUST remain deterministic. Do not add LLM calls or inference here.
Any ambiguity in a patch is a patch bug, not a runtime problem.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
REQUIRED_FIELDS = {
    "patch_id",
    "created_at",
    "source_skill",
    "pass",
    "confidence",
    "target_page",
    "anchor",
    "operation",
    "content",
    "raw_citations",
    "review_status",
}
VALID_SOURCE_SKILLS = {
    "hermes-llm-wiki",
    "wiki-coverage-audit",
    "wiki-relation-detect",
    "wiki-contradiction-check",  # only for report-derived patches after human resolution
}
VALID_PASS = {"explicit", "implicit"}
VALID_CONFIDENCE = {"HIGH", "LOW"}
VALID_OPERATIONS = {"insert_after", "insert_before", "replace", "delete"}
VALID_ANCHOR_TYPES = {"section_heading", "line_range", "before_after"}


@dataclass
class ApplyResult:
    patch_id: str
    success: bool
    reason: str
    applied_path: Path | None = None


def load_patch(path: Path) -> dict[str, Any]:
    """Load a patch JSON file; raise ValueError on parse failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path.name}: {exc}") from exc


def validate_schema(patch: dict[str, Any]) -> list[str]:
    """Return list of validation errors; empty list = valid."""
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(patch.keys())
    if missing:
        errors.append(f"missing required fields: {sorted(missing)}")
        return errors  # further checks depend on presence

    if patch["source_skill"] not in VALID_SOURCE_SKILLS:
        errors.append(f"invalid source_skill: {patch['source_skill']}")
    if patch["pass"] not in VALID_PASS:
        errors.append(f"invalid pass: {patch['pass']}")
    if patch["confidence"] not in VALID_CONFIDENCE:
        errors.append(f"invalid confidence: {patch['confidence']}")
    if patch["operation"] not in VALID_OPERATIONS:
        errors.append(f"invalid operation: {patch['operation']}")
    if patch["review_status"] != "approved":
        errors.append(f"review_status must be 'approved', got '{patch['review_status']}'")

    anchor = patch.get("anchor", {})
    if not isinstance(anchor, dict) or "type" not in anchor or "value" not in anchor:
        errors.append("anchor must be an object with 'type' and 'value'")
    elif anchor["type"] not in VALID_ANCHOR_TYPES:
        errors.append(f"invalid anchor.type: {anchor['type']}")

    if patch["operation"] == "delete" and patch["content"]:
        errors.append("delete operation must have empty content")

    # LOW confidence patches require evidence chain of >=3 steps
    if patch["confidence"] == "LOW":
        chain = patch.get("evidence_chain", [])
        if not isinstance(chain, list) or len(chain) < 3:
            errors.append("LOW confidence patches require evidence_chain with >=3 steps")

    # implicit patches require wiki_citations
    if patch["pass"] == "implicit":
        wiki_cits = patch.get("wiki_citations", [])
        if not isinstance(wiki_cits, list) or len(wiki_cits) < 1:
            errors.append("implicit patches require >=1 wiki_citations")

    # raw citations must have raw_path and line_range
    raw_cits = patch.get("raw_citations", [])
    if not isinstance(raw_cits, list) or len(raw_cits) < 1:
        errors.append("patch must have >=1 raw_citations")
    else:
        for i, cit in enumerate(raw_cits):
            if not isinstance(cit, dict):
                errors.append(f"raw_citations[{i}] must be object")
                continue
            if "raw_path" not in cit:
                errors.append(f"raw_citations[{i}] missing raw_path")
            if "line_range" in cit:
                lr = cit["line_range"]
                if not (isinstance(lr, list) and len(lr) == 2 and lr[0] >= 1 and lr[1] >= lr[0]):
                    errors.append(f"raw_citations[{i}].line_range invalid: {lr}")

    return errors


def verify_paths_exist(patch: dict[str, Any], wiki_root: Path) -> list[str]:
    """Verify target_page and raw_citations reference existing files."""
    errors: list[str] = []
    target = wiki_root / "working" / patch["target_page"]
    # target_page may not exist yet for new-file operations; check operation
    # However, patch-applier only handles existing-file edits by design.
    # New files come directly from the writer without going through this path.
    if not target.exists():
        errors.append(f"target_page not found: working/{patch['target_page']}")
    for cit in patch.get("raw_citations", []):
        raw = wiki_root / "raw" / cit["raw_path"]
        if not raw.exists():
            errors.append(f"raw citation not found: raw/{cit['raw_path']}")
    return errors


def locate_anchor(text: str, anchor: dict[str, Any]) -> tuple[int, int] | None:
    """Return (start_offset, end_offset) of anchor in text, or None if not found.

    For section_heading: span covers just the heading line.
    For line_range: span covers the specified lines (1-indexed inclusive).
    For before_after: span covers the unique gap between before/after markers.
    """
    atype = anchor["type"]
    val = anchor["value"]

    if atype == "section_heading":
        # Escape regex meta and match the exact heading line
        pattern = re.compile(r"^" + re.escape(val) + r"\s*$", re.MULTILINE)
        m = pattern.search(text)
        if not m:
            return None
        # Ensure uniqueness — a duplicate heading is an ambiguity error
        remainder = text[m.end():]
        if pattern.search(remainder):
            return None  # ambiguous, caller reports as "ambiguous anchor"
        return (m.start(), m.end())

    if atype == "line_range":
        # value format: "start:end"
        try:
            parts = val.split(":")
            start_line = int(parts[0])
            end_line = int(parts[1])
        except (ValueError, IndexError):
            return None
        lines = text.split("\n")
        if start_line < 1 or end_line > len(lines) or end_line < start_line:
            return None
        # Compute offsets
        # Sum of lengths of lines 1..start_line-1 plus (start_line-1) newlines
        start_offset = sum(len(lines[i]) + 1 for i in range(start_line - 1))
        end_offset = start_offset + sum(len(lines[i]) + 1 for i in range(start_line - 1, end_line))
        # end_offset includes the trailing newline of the last line
        return (start_offset, end_offset)

    if atype == "before_after":
        try:
            spec = json.loads(val) if isinstance(val, str) else val
            before = spec["before"]
            after = spec["after"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return None
        # Find unique span with `before` immediately preceding and `after` immediately following
        idx_before = text.find(before)
        if idx_before < 0 or text.find(before, idx_before + 1) >= 0:
            return None  # not found or not unique
        span_start = idx_before + len(before)
        idx_after = text.find(after, span_start)
        if idx_after < 0:
            return None
        return (span_start, idx_after)

    return None


def apply_operation(
    text: str, anchor_span: tuple[int, int], operation: str, content: str
) -> str:
    """Return new text with operation applied at anchor_span."""
    start, end = anchor_span
    if operation == "insert_after":
        # Insert content immediately after the anchor span
        # For section_heading anchors, add a newline separator if not present
        sep = "" if content.startswith("\n") else "\n"
        return text[:end] + sep + content + text[end:]
    if operation == "insert_before":
        sep = "" if content.endswith("\n") else "\n"
        return text[:start] + content + sep + text[start:]
    if operation == "replace":
        return text[:start] + content + text[end:]
    if operation == "delete":
        return text[:start] + text[end:]
    raise ValueError(f"unknown operation: {operation}")


def apply_patch(patch: dict[str, Any], wiki_root: Path, dry_run: bool) -> ApplyResult:
    """Apply a single patch to working/. Returns ApplyResult."""
    patch_id = patch["patch_id"]
    target = wiki_root / "working" / patch["target_page"]

    try:
        with open(target, "r", encoding="utf-8") as f:
            original = f.read()
    except OSError as exc:
        return ApplyResult(patch_id, False, f"cannot read target: {exc}")

    span = locate_anchor(original, patch["anchor"])
    if span is None:
        return ApplyResult(patch_id, False, "anchor not found or ambiguous")

    try:
        new_text = apply_operation(
            original, span, patch["operation"], patch["content"]
        )
    except ValueError as exc:
        return ApplyResult(patch_id, False, f"operation failed: {exc}")

    if dry_run:
        return ApplyResult(patch_id, True, "dry-run OK (not written)")

    # Atomic write: write to temp file then rename
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(new_text)
        tmp.replace(target)
    except OSError as exc:
        if tmp.exists():
            tmp.unlink()
        return ApplyResult(patch_id, False, f"write failed: {exc}")

    return ApplyResult(patch_id, True, "applied", target)


def update_source_map(patch: dict[str, Any], wiki_root: Path) -> None:
    """Update source_map.json to reflect raw → working provenance for this patch."""
    smpath = wiki_root / "source_map.json"
    if smpath.exists():
        with open(smpath, "r", encoding="utf-8") as f:
            source_map = json.load(f)
    else:
        source_map = {}

    target = patch["target_page"]  # relative to working/
    for cit in patch.get("raw_citations", []):
        raw_path = cit["raw_path"]  # relative to raw/
        key = f"raw/{raw_path}"
        entry = source_map.setdefault(key, {
            "referenced_by_working": [],
            "referenced_by_canonical": [],
            "coverage_depth": "partial",
        })
        target_key = f"working/{target}"
        if target_key not in entry["referenced_by_working"]:
            entry["referenced_by_working"].append(target_key)

    with open(smpath, "w", encoding="utf-8") as f:
        json.dump(source_map, f, indent=2, sort_keys=True)


def move_patch(patch_path: Path, dest_dir: Path, reason: str | None = None) -> None:
    """Move a patch file to a destination dir, optionally annotating with reason."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / patch_path.name
    if reason is not None:
        # Annotate the patch with the rejection reason before moving
        with open(patch_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["applier_note"] = reason
        data["applier_processed_at"] = datetime.now(timezone.utc).isoformat()
        with open(patch_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    shutil.move(str(patch_path), str(dest))


def process_all(wiki_root: Path, dry_run: bool, patch_id: str | None) -> int:
    """Process all approved patches. Returns exit code."""
    approved_dir = wiki_root / "patches" / "approved"
    applied_dir = wiki_root / "patches" / "applied"
    rejected_dir = wiki_root / "patches" / "rejected"

    if not approved_dir.exists():
        print(f"No approved/ directory at {approved_dir}", file=sys.stderr)
        return 1

    patches = sorted(approved_dir.glob("*.json"))
    if patch_id is not None:
        patches = [p for p in patches if p.stem == patch_id]
        if not patches:
            print(f"Patch {patch_id} not found in approved/", file=sys.stderr)
            return 1

    total = len(patches)
    ok = 0
    fail = 0
    for patch_path in patches:
        try:
            patch = load_patch(patch_path)
        except ValueError as exc:
            print(f"[REJECT] {patch_path.name}: {exc}")
            if not dry_run:
                move_patch(patch_path, rejected_dir, reason=str(exc))
            fail += 1
            continue

        schema_errors = validate_schema(patch)
        if schema_errors:
            reason = "; ".join(schema_errors)
            print(f"[REJECT] {patch_path.name}: {reason}")
            if not dry_run:
                move_patch(patch_path, rejected_dir, reason=reason)
            fail += 1
            continue

        path_errors = verify_paths_exist(patch, wiki_root)
        if path_errors:
            reason = "; ".join(path_errors)
            print(f"[REJECT] {patch_path.name}: {reason}")
            if not dry_run:
                move_patch(patch_path, rejected_dir, reason=reason)
            fail += 1
            continue

        result = apply_patch(patch, wiki_root, dry_run)
        if result.success:
            print(f"[OK]     {patch_path.name}: {result.reason}")
            if not dry_run:
                update_source_map(patch, wiki_root)
                move_patch(patch_path, applied_dir)
            ok += 1
        else:
            print(f"[REJECT] {patch_path.name}: {result.reason}")
            if not dry_run:
                move_patch(patch_path, rejected_dir, reason=result.reason)
            fail += 1

    print()
    print(f"Total: {total}, applied: {ok}, rejected: {fail} (dry_run={dry_run})")
    return 0 if fail == 0 else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--wiki-root", required=True, type=Path, help="Path to wiki root")
    parser.add_argument("--dry-run", action="store_true", help="Validate and simulate without writing")
    parser.add_argument("--apply", action="store_true", help="Actually apply (default is dry-run)")
    parser.add_argument("--patch-id", type=str, default=None, help="Process only a specific patch by ID")
    args = parser.parse_args()

    if not args.apply and not args.dry_run:
        # Default to dry-run for safety
        args.dry_run = True
        print("(no --apply flag; running in dry-run mode)\n")

    dry_run = args.dry_run and not args.apply
    if not args.wiki_root.exists():
        print(f"Wiki root not found: {args.wiki_root}", file=sys.stderr)
        return 1

    return process_all(args.wiki_root, dry_run, args.patch_id)


if __name__ == "__main__":
    sys.exit(main())
