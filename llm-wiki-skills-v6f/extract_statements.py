#!/usr/bin/env python3
"""extract_statements.py — deterministic statement extraction for rendered
slide sources. NO LLM involved.

Rationale: the executor model (e.g. a small local model) is untrusted and will
drift. Every judgment removed from it is drift that cannot happen. For the
slide JSON pipeline, extraction requires zero judgment — vlmInsight paragraphs,
table rows, and chart axes are structurally delimited. This script:

  1. Parses the rendered md (from render_slide.py)
  2. Emits statements/<sub>/<name>.statements.md with correct hashes
     (append-only: existing statements are never modified; only new hashes
     are appended)
  3. Prints a CITATION CHEAT SHEET to stdout — ready-made ^[path#hash]
     strings the executor model COPIES into wiki pages, never computes

Extraction policy (matches SKILL.md):
  * vlmInsight  → one verbatim statement per paragraph, speaker: expert
  * table       → one verbatim statement per row
  * chart axes  → one verbatim statement per axis line
  * chart 判讀  → SKIPPED by default (wiki carries clues, not interpretation);
                  --include-chart-insight extracts them with speaker: vlm

Usage:
  python tools/extract_statements.py raw/slides/pcm-training-p012.md \
      --wiki . --domain equipment-maintenance
"""

import argparse
import datetime
import hashlib
import re
import sys
from pathlib import Path

HASH_LEN = 12
EXISTING_STMT_RE = re.compile(r"^###\s+stmt\s+([0-9a-f]{%d})\b" % HASH_LEN,
                              re.MULTILINE)


def stmt_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:HASH_LEN]


def frontmatter_fields(text):
    fields = {}
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return fields, text
    end = text.find("\n---", 4)
    if end == -1:
        return fields, text
    for ln in text[4:end].split("\n"):
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", ln)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip("'\"")
    nl = text.find("\n", end + 1)
    return fields, (text[nl + 1:] if nl != -1 else "")


def sections(body):
    """Yield (section_name, [lines])."""
    cur, buf = None, []
    for ln in body.split("\n"):
        if ln.startswith("## "):
            if cur:
                yield cur, buf
            cur, buf = ln[3:].strip(), []
        elif ln.startswith("# "):
            if cur:
                yield cur, buf
            cur, buf = None, []
        elif cur is not None:
            buf.append(ln)
    if cur:
        yield cur, buf


def paragraphs(lines):
    """Group lines into blank-line-separated paragraphs, canonical-stripped."""
    para, out = [], []
    for ln in lines:
        if ln.strip():
            para.append(ln.rstrip())
        elif para:
            out.append("\n".join(para).strip())
            para = []
    if para:
        out.append("\n".join(para).strip())
    return [p for p in out if p]


def extract(body, include_chart_insight=False):
    """Return list of (text, speaker) in document order."""
    stmts = []
    for name, lines in sections(body):
        if name.startswith("vlmInsight"):
            for p in paragraphs(lines):
                stmts.append((p, "expert"))
        elif name.startswith("table"):
            for ln in lines:
                if ln.strip():
                    stmts.append((ln.strip(), "expert"))
        elif name.startswith("chart"):
            for ln in lines:
                s = ln.strip()
                if not s:
                    continue
                if s.startswith("判讀"):
                    if include_chart_insight:
                        stmts.append((s, "vlm"))
                else:
                    stmts.append((s, "expert"))
    return stmts


def statements_path_for(wiki, source_rel):
    p = Path(source_rel)
    if p.parts and p.parts[0] == "raw":
        p = Path(*p.parts[1:])
    return wiki / "statements" / p.parent / (p.stem + ".statements.md")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+", help="rendered md file(s) under raw/")
    ap.add_argument("--wiki", default=".", help="wiki root")
    ap.add_argument("--domain", required=True,
                    help="domain tag from SCHEMA's knowledge-level table")
    ap.add_argument("--include-chart-insight", action="store_true")
    args = ap.parse_args()

    wiki = Path(args.wiki).resolve()
    today = datetime.date.today().isoformat()

    for src in args.sources:
        sfile = Path(src).resolve()
        try:
            src_rel = str(sfile.relative_to(wiki))
        except ValueError:
            print(f"skip {src}: not under wiki root {wiki}", file=sys.stderr)
            continue

        text = sfile.read_text(encoding="utf-8")
        fm, body = frontmatter_fields(text)
        deck, page = fm.get("deck", "?"), fm.get("page", "?")
        loc = f"deck {deck}, slide {page}"
        body_sha = hashlib.sha256(
            body.replace("\r\n", "\n").encode("utf-8")).hexdigest()

        out = statements_path_for(wiki, src_rel)
        existing = set()
        if out.exists():
            existing = set(EXISTING_STMT_RE.findall(
                out.read_text(encoding="utf-8")))

        new_blocks, cheat = [], []
        for stext, speaker in extract(body, args.include_chart_insight):
            h = stmt_hash(stext)
            cite = f"^[{src_rel}#{h}]"
            cheat.append((h, speaker, stext, cite))
            if h in existing:
                continue
            quoted = "\n".join("> " + ln for ln in stext.split("\n"))
            new_blocks.append(
                f"### stmt {h} | {args.domain} | verbatim | "
                f"speaker: {speaker} | loc: {loc}\n{quoted}\n")

        if not out.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                f"---\nsource: {src_rel}\nsource_sha256: {body_sha}\n"
                f"extracted: {today}\nextractor: extract_statements.py\n---\n\n"
                + "\n".join(new_blocks), encoding="utf-8")
        elif new_blocks:  # append-only
            with out.open("a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(new_blocks))

        # --- citation cheat sheet: the executor model COPIES these strings ---
        print(f"=== CITATION CHEAT SHEET — {src_rel} ({loc}) ===")
        print(f"statements file: {out.relative_to(wiki)} "
              f"({len(new_blocks)} new, {len(existing)} existing)")
        for h, speaker, stext, cite in cheat:
            one = stext.replace("\n", " ")
            tag = "" if speaker == "expert" else f"  [speaker: {speaker} — 機器推論,勿當專家結論]"
            print(f"\n{cite}{tag}\n    {one}")
        print()


if __name__ == "__main__":
    main()
