#!/usr/bin/env python3
"""render_slide.py — deterministic slide-JSON → markdown renderer.

RENDERER VERSION: 1.0  (bump on ANY output-format change; verify --rerender
                        compares bodies, so format changes invalidate old checks)

Input JSON schema (per slide page):
  summary     : model-generated intro           → frontmatter ONLY (index hint,
                                                  structurally excluded from the
                                                  evidence chain / canonical body)
  vlmInsight  : human domain-expert comments    → body, speaker: expert
  table       : {headers, rows} | [ {...}, ... ]→ body, one row per line
  chart       : axes + VLM interpretation       → body, axes as facts;
                                                  interpretation as speaker: vlm

Determinism rules:
  * All strings NFC-normalized (unicodedata) — kills NFC/NFD substring failures
  * Unknown dict keys serialized in sorted order; list order preserved
  * The renderer is TOTAL: every field except `summary` appears in the body.
    Silent data loss would create findability gaps, which is the one thing the
    wiki exists to prevent.

Usage:
  python render_slide.py page.json --deck pcm-training --page 12 -o raw/slides/pcm-training-p012.md
  python render_slide.py raw/slides/json/*.json --out-dir raw/slides   # batch;
      deck/page parsed from filenames like <deck>-p<NNN>.json

Pure function `render(data, deck, page, json_sha, json_relpath)` is importable —
verify_wiki.py uses it for --rerender integrity checks.
"""

import argparse
import datetime
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

RENDERER_VERSION = "1.0"
FNAME_RE = re.compile(r"^(?P<deck>.+?)[-_]p(?P<page>\d+)$")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def _clean(s):
    """NFC + newline normalization for body text."""
    return nfc(str(s)).replace("\r\n", "\n").replace("\r", "\n").strip()


# ---------------------------------------------------------------- sections

def render_insight(v):
    """vlmInsight: string or list of strings. Expert words — untouched except
    NFC + newline normalization."""
    if v is None:
        return []
    items = v if isinstance(v, list) else [v]
    items = [_clean(x) for x in items if _clean(x)]
    if not items:
        return []
    out = ["## vlmInsight (speaker: expert)", ""]
    for it in items:
        out.append(it)
        out.append("")
    return out


def _kv_line(d):
    """dict → '- k: v | k: v' with keys in sorted order (determinism)."""
    return " | ".join(f"{nfc(str(k))}: {_clean(v)}"
                             for k, v in sorted(d.items(), key=lambda kv: str(kv[0])))


def render_table(t):
    """table: {'headers':[...],'rows':[[...]]} or [ {...}, ... ].
    One row per line → each row is verbatim-eligible source text."""
    if not t:
        return []
    lines = ["## table", ""]
    if isinstance(t, dict) and "headers" in t and "rows" in t:
        hdrs = [nfc(str(h)) for h in t["headers"]]
        for row in t["rows"]:
            cells = [_clean(c) for c in row]
            pairs = [f"{h}: {c}" for h, c in zip(hdrs, cells)]
            pairs += cells[len(hdrs):]  # extra cells beyond headers: keep, don't drop
            lines.append(" | ".join(pairs))
    elif isinstance(t, list):
        for row in t:
            lines.append(_kv_line(row) if isinstance(row, dict)
                         else _clean(row))
    else:  # unknown shape — total rendering, never drop
        lines.append(_clean(json.dumps(t, ensure_ascii=False, sort_keys=True)))
    lines.append("")
    return lines


CHART_AXIS_KEYS = {
    "x": ("x_axis", "xAxis", "x", "x軸"),
    "y": ("y_axis", "yAxis", "y", "y軸"),
}
CHART_INSIGHT_KEYS = ("insight", "interpretation", "vlm_insight", "vlmInterpretation",
                      "trend", "判讀")


def render_chart(c):
    """chart: axes are structural facts; VLM interpretation is machine inference
    and MUST carry speaker: vlm so it can never be laundered into expert words."""
    if not c:
        return []
    charts = c if isinstance(c, list) else [c]
    lines = ["## chart", ""]
    for ch in charts:
        if not isinstance(ch, dict):
            lines.append(_clean(ch))
            continue
        used = set()
        for label, keys in CHART_AXIS_KEYS.items():
            for k in keys:
                if k in ch:
                    lines.append(f"{label}軸: {_clean(ch[k])}")
                    used.add(k)
                    break
        for k in CHART_INSIGHT_KEYS:
            if k in ch:
                vals = ch[k] if isinstance(ch[k], list) else [ch[k]]
                for v in vals:
                    lines.append(f"判讀 (speaker: vlm): {_clean(v)}")
                used.add(k)
        rest = {k: v for k, v in ch.items() if k not in used}
        if rest:  # total rendering: unknown keys serialized, sorted
            lines.append(_kv_line(rest))
        lines.append("")
    return lines


# ---------------------------------------------------------------- render

def render(data, deck, page, json_sha, json_relpath):
    """Pure deterministic render. Returns full md text (frontmatter + body)."""
    summary = _clean(data.get("summary", "")).replace("\n", " ")
    fm = [
        "---",
        f"deck: {nfc(deck)}",
        f"page: {page}",
        f"source_json: {json_relpath}",
        f"json_sha256: {json_sha}",
        f"renderer: render_slide.py v{RENDERER_VERSION}",
        f"rendered: {datetime.date.today().isoformat()}",
        # summary lives in FRONTMATTER only: usable for index one-liners,
        # structurally excluded from canon_body → can never be cited as evidence
        f"summary: {json.dumps(summary, ensure_ascii=False)}",
        "---",
        "",
    ]
    body = [f"# {nfc(deck)} — slide {page}", ""]
    body += render_insight(data.get("vlmInsight"))
    body += render_table(data.get("table"))
    body += render_chart(data.get("chart"))
    known = {"summary", "vlmInsight", "table", "chart"}
    rest = {k: v for k, v in data.items() if k not in known}
    if rest:  # total rendering for schema drift
        body += ["## other fields", ""]
        body.append(_clean(json.dumps(rest, ensure_ascii=False, sort_keys=True)))
        body.append("")
    return "\n".join(fm + body).rstrip() + "\n"


def render_file(json_path, deck, page, out_path, json_relpath):
    raw = json_path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    md = render(data, deck, page, hashlib.sha256(raw).hexdigest(), json_relpath)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="slide json file(s)")
    ap.add_argument("--deck")
    ap.add_argument("--page", type=int)
    ap.add_argument("-o", "--output", help="output md (single input only)")
    ap.add_argument("--out-dir", help="output directory (batch)")
    ap.add_argument("--wiki", default=".", help="wiki root, for relative json path in frontmatter")
    args = ap.parse_args()

    wiki = Path(args.wiki).resolve()
    for inp in args.inputs:
        jp = Path(inp).resolve()
        deck, page = args.deck, args.page
        if deck is None or page is None:
            m = FNAME_RE.match(jp.stem)
            if not m:
                print(f"skip {jp.name}: cannot parse deck/page from filename; "
                      f"pass --deck/--page", file=sys.stderr)
                continue
            deck, page = m.group("deck"), int(m.group("page"))
        try:
            rel = str(jp.relative_to(wiki))
        except ValueError:
            rel = str(jp)
        if args.output and len(args.inputs) == 1:
            out = Path(args.output)
        else:
            base = Path(args.out_dir or jp.parent)
            out = base / f"{deck}-p{page:03d}.md"
        render_file(jp, deck, page, out, rel)
        print(f"rendered {jp.name} -> {out}")


if __name__ == "__main__":
    main()
