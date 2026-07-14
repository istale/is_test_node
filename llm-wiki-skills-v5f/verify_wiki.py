#!/usr/bin/env python3
"""verify_wiki.py — provenance-chain verifier for the LLM Wiki (Transport Edition).

Stdlib only. Python 3.9+.

Commands:
  hash        --text "..." | --stdin      Print the 12-hex statement hash.
  statements  <statements-file>           Verify one statements file (V2, V4).
  verify      --wiki <path>               Verify the whole wiki (V1-V6).

Canonical forms (normative — SKILL.md refers here):
  * Blockquote canonical text: for each line, strip one leading '>' and at most
    one following space; strip trailing whitespace; join with '\n'; strip the
    whole. No Unicode normalization.
  * Source canonical body: content after the closing '---' of YAML frontmatter
    (or the whole file if none); '\r\n' and '\r' normalized to '\n'.
  * Statement hash: first 12 hex chars of SHA-256 over UTF-8 canonical text.

Exit codes: 0 = clean, 1 = findings, 2 = usage/IO error.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

HASH_LEN = 12

# ^[raw/slides/foo.md#3f9a1c2b8d4e]  — v4 citation
CITE_RE = re.compile(r"\^\[([^\]#]+)#([0-9a-f]{%d})\]" % HASH_LEN)
# ^[raw/slides/foo.md]               — v3 legacy marker (no hash)
LEGACY_CITE_RE = re.compile(r"\^\[([^\]#]+)\](?!\()")
# ### stmt 3f9a1c2b8d4e | domain | verbatim
# ### stmt 3f9a1c2b8d4e | domain | fact | loc: slide 12
# ### stmt 3f9a1c2b8d4e | domain | verbatim | speaker: vlm | loc: slide 12 chart
# Trailing segments are 'key: value' pairs in any order. Known keys: loc, speaker.
# speaker: expert (default) | vlm | vlm-approved
STMT_HEADER_RE = re.compile(
    r"^###\s+stmt\s+([0-9a-f]{%d})\s*\|\s*([^|]+?)\s*\|\s*(verbatim|fact)"
    r"((?:\s*\|\s*[a-zA-Z_]+:\s*[^|]*)*)\s*$" % HASH_LEN
)
STMT_KV_RE = re.compile(r"\|\s*([a-zA-Z_]+):\s*([^|]*)")
VALID_SPEAKERS = ("expert", "vlm", "vlm-approved")

WIKI_CONTENT_DIRS = ("entities", "concepts", "analyses", "comparisons", "queries")
SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


# ---------------------------------------------------------------- canonical

def canon_lines(lines):
    """Blockquote canonical text from a list of raw lines."""
    out = []
    for ln in lines:
        ln = ln.rstrip("\r\n")
        if ln.startswith(">"):
            ln = ln[1:]
            if ln.startswith(" "):
                ln = ln[1:]
        out.append(ln.rstrip())
    return "\n".join(out).strip()


def canon_body(text):
    """Source canonical body: strip YAML frontmatter, normalize newlines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            nl = text.find("\n", end + 1)
            return text[nl + 1:] if nl != -1 else ""
    return text


def stmt_hash(canonical_text):
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()[:HASH_LEN]


def body_sha256(text):
    return hashlib.sha256(canon_body(text).encode("utf-8")).hexdigest()


def frontmatter_fields(text):
    """Minimal 'key: value' scan of the YAML frontmatter. No nesting support."""
    fields = {}
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---\n"):
        return fields
    end = text.find("\n---", 4)
    if end == -1:
        return fields
    for ln in text[4:end].split("\n"):
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", ln)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip("'\"")
    return fields


# ---------------------------------------------------------------- parsing

def parse_statements_file(path):
    """Yield dicts: {hash, domain, type, loc, text, line}. Blockquote lines
    following each header form the statement body."""
    stmts, cur, cur_quote = [], None, []

    def flush():
        if cur is not None:
            cur["text"] = canon_lines(cur_quote)
            stmts.append(cur)

    for i, raw in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        m = STMT_HEADER_RE.match(raw)
        if m:
            flush()
            kv = {k.strip(): v.strip()
                  for k, v in STMT_KV_RE.findall(m.group(4) or "")}
            cur = {"hash": m.group(1), "domain": m.group(2).strip(),
                   "type": m.group(3), "loc": kv.get("loc", ""),
                   "speaker": kv.get("speaker", "expert"), "line": i}
            cur_quote = []
        elif cur is not None and raw.lstrip().startswith(">"):
            cur_quote.append(raw.lstrip())
        elif cur is not None and raw.strip() == "" and not cur_quote:
            continue  # blank line between header and quote
        elif cur is not None and cur_quote and raw.strip() == "":
            flush()
            cur, cur_quote = None, []
    flush()
    return stmts


def statements_path_for(wiki, source_rel):
    """raw/slides/foo.md -> statements/slides/foo.statements.md"""
    p = Path(source_rel)
    if p.parts and p.parts[0] == "raw":
        p = Path(*p.parts[1:])
    return wiki / "statements" / p.parent / (p.stem + ".statements.md")


def extract_verbatim_blocks(text):
    """Yield (canonical_text, cite_path, cite_hash, header_line) for each
    '## Expert Finding (verbatim)' block. The citation is the first ^[path#hash]
    at/after the block's quote."""
    lines = text.split("\n")
    i, blocks = 0, []
    while i < len(lines):
        if re.match(r"^##\s+Expert Finding \(verbatim\)", lines[i]):
            header = i + 1
            j = i + 1
            quote = []
            while j < len(lines) and not lines[j].lstrip().startswith(">"):
                if lines[j].startswith("## "):
                    break
                j += 1
            while j < len(lines) and lines[j].lstrip().startswith(">"):
                quote.append(lines[j].lstrip())
                j += 1
            cite = None
            for k in range(j, min(j + 4, len(lines))):
                m = CITE_RE.search(lines[k])
                if m:
                    cite = (m.group(1), m.group(2))
                    break
            blocks.append((canon_lines(quote), cite, header))
            i = j
        else:
            i += 1
    return blocks


def _section_lines(text, prefixes):
    """Yield (section, lineno, stripped_line) for non-empty content lines under
    '## <prefix>...' headers of a rendered source body."""
    cur = None
    for i, ln in enumerate(text.split("\n"), 1):
        if ln.startswith("## "):
            name = ln[3:].strip()
            cur = next((p for p in prefixes if name.startswith(p)), None)
            continue
        if ln.startswith("# "):
            cur = None
            continue
        if cur and ln.strip():
            yield cur, i, ln.strip()


# ---------------------------------------------------------------- findings

class Report:
    def __init__(self):
        self.findings = []

    def add(self, sev, code, where, msg):
        self.findings.append((sev, code, where, msg))

    def dump(self):
        if not self.findings:
            print("CLEAN — all provenance chains intact.")
            return 0
        self.findings.sort(key=lambda f: (SEVERITY_ORDER[f[0]], f[1], f[2]))
        counts = {}
        for sev, code, where, msg in self.findings:
            counts[sev] = counts.get(sev, 0) + 1
            print(f"[{sev}] {code} {where}\n    {msg}")
        summary = " ".join(f"{s}:{counts.get(s, 0)}" for s in SEVERITY_ORDER)
        print(f"\n{len(self.findings)} finding(s) — {summary}")
        return 1


# ---------------------------------------------------------------- commands

def cmd_hash(args):
    text = sys.stdin.read() if args.stdin else args.text
    if text is None:
        print("hash: provide --text or --stdin", file=sys.stderr)
        return 2
    print(stmt_hash(canon_lines(text.split("\n"))))
    return 0


def verify_statements_file(wiki, spath, rpt):
    """V2 (verbatim substring) + V4 (hash integrity) for one statements file.
    Returns {hash: stmt} for citation resolution."""
    rel = spath.relative_to(wiki)
    try:
        stmts = parse_statements_file(spath)
    except OSError as e:
        rpt.add("CRITICAL", "V4-READ", str(rel), f"cannot read: {e}")
        return {}

    fm = frontmatter_fields(spath.read_text(encoding="utf-8"))
    source_rel = fm.get("source", "")
    source_body = None
    if source_rel:
        sfile = wiki / source_rel
        if sfile.exists():
            source_body = canon_body(sfile.read_text(encoding="utf-8"))
        else:
            rpt.add("CRITICAL", "V2-NOSRC", str(rel),
                    f"declared source missing: {source_rel}")
    else:
        rpt.add("CRITICAL", "V2-NOSRC", str(rel), "no 'source:' in frontmatter")

    by_hash = {}
    for s in stmts:
        if not s["text"]:
            rpt.add("CRITICAL", "V4-EMPTY", f"{rel}:{s['line']}",
                    f"stmt {s['hash']} has no blockquote body")
            continue
        actual = stmt_hash(s["text"])
        if actual != s["hash"]:
            rpt.add("CRITICAL", "V4-HASH", f"{rel}:{s['line']}",
                    f"recorded {s['hash']} != computed {actual}")
        if s["type"] == "verbatim" and source_body is not None:
            if s["text"] not in source_body:
                rpt.add("CRITICAL", "V2-SUBSTR", f"{rel}:{s['line']}",
                        f"verbatim stmt {s['hash']} is NOT a substring of "
                        f"{source_rel} — evidence altered at extraction")
        if s["type"] == "fact" and not s["loc"]:
            rpt.add("HIGH", "V4-NOLOC", f"{rel}:{s['line']}",
                    f"fact stmt {s['hash']} lacks mandatory 'loc:' hint")
        if s["speaker"] not in VALID_SPEAKERS:
            rpt.add("HIGH", "V4-SPEAKER", f"{rel}:{s['line']}",
                    f"stmt {s['hash']} has unknown speaker '{s['speaker']}' "
                    f"(valid: {', '.join(VALID_SPEAKERS)})")
        by_hash[s["hash"]] = s
    return by_hash


def cmd_statements(args):
    spath = Path(args.file).resolve()
    wiki = Path(args.wiki).resolve() if args.wiki else _infer_wiki(spath)
    rpt = Report()
    verify_statements_file(wiki, spath, rpt)
    return rpt.dump()


def _infer_wiki(spath):
    for p in spath.parents:
        if p.name == "statements":
            return p.parent
    return spath.parent


def cmd_verify(args):
    wiki = Path(args.wiki).resolve()
    if not wiki.is_dir():
        print(f"verify: not a directory: {wiki}", file=sys.stderr)
        return 2
    rpt = Report()

    # --- V2/V4: all statements files
    stmt_index = {}  # source_rel -> {hash: stmt}
    sdir = wiki / "statements"
    if sdir.is_dir():
        for spath in sorted(sdir.rglob("*.statements.md")):
            fm = frontmatter_fields(spath.read_text(encoding="utf-8"))
            src = fm.get("source", str(spath.relative_to(wiki)))
            stmt_index.setdefault(src, {}).update(
                verify_statements_file(wiki, spath, rpt))

    # --- V5 / V7 / V8: raw immutability, render integrity, extraction coverage
    render_mod = None
    if args.rerender:
        render_py = wiki / "tools" / "render_slide.py"
        if render_py.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("render_slide", render_py)
            render_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(render_mod)
        else:
            print("--rerender: tools/render_slide.py not found; skipping V7-RENDER",
                  file=sys.stderr)

    rdir = wiki / "raw"
    if rdir.is_dir():
        for rfile in sorted(rdir.rglob("*.md")):
            rrel = rfile.relative_to(wiki)
            text = rfile.read_text(encoding="utf-8", errors="replace")
            fm = frontmatter_fields(text)

            recorded = fm.get("sha256")
            if recorded and recorded != body_sha256(text):
                rpt.add("CRITICAL", "V5-TAMPER", str(rrel),
                        "raw body sha256 mismatch — Layer 1 was modified")

            # V7: rendered-from-JSON provenance
            src_json = fm.get("source_json")
            if src_json:
                jfile = wiki / src_json
                if not jfile.exists():
                    rpt.add("CRITICAL", "V7-NOJSON", str(rrel),
                            f"source_json missing: {src_json}")
                else:
                    actual = hashlib.sha256(jfile.read_bytes()).hexdigest()
                    if fm.get("json_sha256") and actual != fm["json_sha256"]:
                        rpt.add("CRITICAL", "V7-JSONTAMPER", str(rrel),
                                "source JSON sha256 mismatch — upstream evidence "
                                "was modified after render")
                    elif render_mod is not None:
                        import json as _json
                        data = _json.loads(jfile.read_text(encoding="utf-8"))
                        regen = render_mod.render(
                            data, fm.get("deck", ""),
                            fm.get("page", ""), actual, src_json)
                        if canon_body(regen) != canon_body(text):
                            rpt.add("CRITICAL", "V7-RENDER", str(rrel),
                                    "re-rendered body differs — rendered md was "
                                    "hand-edited, or renderer version changed")

            # V8: coverage — rendered/ingested but never extracted = findability gap
            spath = statements_path_for(wiki, str(rrel))
            if not spath.exists():
                rpt.add("MEDIUM", "V8-COVERAGE", str(rrel),
                        "source has no statements file — its content is invisible "
                        "to the wiki (findability gap)")

            # V9: full extraction of clue-bearing sections. The human-reviewed
            # JSON is the SOT — everything in vlmInsight and table survived
            # human curation, so 100% of it must be transported. A missed line
            # is a lost clue, the primary failure this wiki exists to prevent.
            # (chart interpretation is intentionally NOT required — readers dig
            # into the original slides for interpretation.)
            if src_json and spath.exists():
                texts = [s["text"] for s in
                         stmt_index.get(str(rrel), {}).values()]
                for sec, lineno, lntext in _section_lines(
                        text, ("vlmInsight", "table")):
                    if not any(lntext in st for st in texts):
                        rpt.add("HIGH", "V9-UNEXTRACTED", f"{rrel}:{lineno}",
                                f"[{sec}] line not covered by any statement — "
                                f"a clue was not transported into the wiki")

    # --- V1/V3/V6: wiki pages
    for d in WIKI_CONTENT_DIRS:
        cdir = wiki / d
        if not cdir.is_dir():
            continue
        for page in sorted(cdir.rglob("*.md")):
            rel = page.relative_to(wiki)
            text = page.read_text(encoding="utf-8", errors="replace")

            for lineno, ln in enumerate(text.split("\n"), 1):
                for m in CITE_RE.finditer(ln):
                    src, h = m.group(1), m.group(2)
                    if h not in stmt_index.get(src, {}):
                        rpt.add("CRITICAL", "V1-RESOLVE", f"{rel}:{lineno}",
                                f"citation ^[{src}#{h}] does not resolve to any "
                                f"extracted statement")
                for m in LEGACY_CITE_RE.finditer(ln):
                    if not CITE_RE.search(m.group(0)):
                        rpt.add("MEDIUM", "V6-LEGACY", f"{rel}:{lineno}",
                                f"legacy v3 marker ^[{m.group(1)}] — migrate to "
                                f"^[path#hash]")

            for block_text, cite, header_line in extract_verbatim_blocks(text):
                where = f"{rel}:{header_line}"
                if cite is None:
                    rpt.add("CRITICAL", "V3-NOCITE", where,
                            "verbatim block has no ^[path#hash] citation")
                    continue
                src, h = cite
                stmt = stmt_index.get(src, {}).get(h)
                if stmt is None:
                    rpt.add("CRITICAL", "V3-RESOLVE", where,
                            f"verbatim block cites unresolvable ^[{src}#{h}]")
                elif stmt["type"] != "verbatim":
                    rpt.add("CRITICAL", "V3-TYPE", where,
                            f"verbatim block cites a '{stmt['type']}' statement")
                elif stmt["speaker"] != "expert":
                    rpt.add("HIGH", "V3-LAUNDER", where,
                            f"'Expert Finding' block cites a speaker:"
                            f"{stmt['speaker']} statement — machine inference "
                            f"presented as expert words")
                elif block_text != stmt["text"]:
                    rpt.add("CRITICAL", "V3-ALTERED", where,
                            f"block text != statement {h} — expert words altered "
                            f"at transport")

    return rpt.dump()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("hash", help="compute a statement hash")
    p.add_argument("--text")
    p.add_argument("--stdin", action="store_true")
    p.set_defaults(fn=cmd_hash)

    p = sub.add_parser("statements", help="verify one statements file")
    p.add_argument("file")
    p.add_argument("--wiki")
    p.set_defaults(fn=cmd_statements)

    p = sub.add_parser("verify", help="verify the whole wiki (V1-V8)")
    p.add_argument("--wiki", required=True)
    p.add_argument("--rerender", action="store_true",
                   help="re-run render_slide.py on each source_json and diff "
                        "bodies (V7-RENDER)")
    p.set_defaults(fn=cmd_verify)

    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
