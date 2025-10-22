#!/usr/bin/env python3
"""
build_tool_index_json.py

產生結合環境設定與模組資訊的 TOOL_INDEX.json。
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---- 常數 ----
BASE_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = Path(__file__).resolve().parent / "TOOL_INDEX.json"
TOOL_DIR_PATTERN = "b??_*"
HEADER_MAP = {
    "概述（Overview）": "overview",
    "參數（Args）": "args",
    "回傳值（Returns）": "returns",
    "異常（Raises）": "raises",
    "副作用（Side Effects）": "side_effects",
    "限制（Constraints）": "constraints",
    "範例（Examples）": "examples",
    "LLM-META": "llm_meta",
}
PARAM_LINE_RE = re.compile(r"^-?\s*([a-zA-Z_]\w*)\s*\(([^)]+)\)\s*:\s*(.+)$")
RAISE_LINE_RE = re.compile(r"^-?\s*([a-zA-Z_]\w*)\s*:.*$")
META_LINE_RE = re.compile(r"^-+\s*([a-zA-Z_]\w*)\s*:\s*(.+)$")


@dataclass
class CallableInfo:
    symbol: str
    entrypoint: str
    source_path: str
    language: str
    parameters: List[Dict[str, Any]]
    returns: Optional[str]
    raises: List[str]
    doc_overview: str
    doc_example: str
    tags: List[str]
    front_matter: Dict[str, Any]


def load_env_config(file_path: Path) -> Dict[str, Any]:
    """讀取環境設定（支援 JSON 與極簡 YAML）。"""
    if not file_path.exists():
        raise FileNotFoundError(f"找不到環境設定檔案：{file_path}")
    raw_text = file_path.read_text(encoding="utf-8")
    stripped = raw_text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("環境設定需為 JSON 物件。")
        except json.JSONDecodeError as exc:
            raise ValueError(f"環境設定不是合法 JSON：{exc}") from exc

    lines = raw_text.splitlines()
    config: Dict[str, Any] = {}
    index = 0
    total = len(lines)

    def parse_scalar(token: str) -> str:
        token = token.strip()
        if token.startswith('"') and token.endswith('"'):
            return token[1:-1]
        if token.startswith("'") and token.endswith("'"):
            return token[1:-1]
        return token

    while index < total:
        raw_line = lines[index]
        stripped_line = raw_line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            index += 1
            continue
        if ":" not in raw_line:
            raise ValueError(f"環境設定存在無法解析的行：{raw_line!r}")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent != 0:
            raise ValueError(f"不支援縮排行為：{raw_line!r}")
        key, remainder = raw_line.split(":", 1)
        key = key.strip()
        value_part = remainder.strip()
        index += 1
        if value_part == "|":
            block_lines: List[str] = []
            while index < total:
                block_line = lines[index]
                if not block_line.strip():
                    block_lines.append("")
                    index += 1
                    continue
                block_indent = len(block_line) - len(block_line.lstrip(" "))
                if block_indent <= indent:
                    break
                block_lines.append(block_line[indent + 2 :])
                index += 1
            config[key] = "\n".join(block_lines)
        else:
            config[key] = parse_scalar(value_part)
    return config


def parse_docstring(doc: Optional[str]) -> Dict[str, str]:
    if not doc:
        return {}
    lines = [line.rstrip() for line in doc.strip().splitlines()]
    sections: Dict[str, str] = {}
    current = "overview"
    buffer: List[str] = []
    for line in lines:
        header_key = HEADER_MAP.get(line.strip())
        if header_key:
            if buffer:
                sections[current] = "\n".join(buffer).strip()
                buffer = []
            current = header_key
        else:
            buffer.append(line)
    if buffer:
        sections[current] = "\n".join(buffer).strip()
    return sections


def build_callable_info(module_path: Path, module_name: str, target_symbol: str) -> CallableInfo:
    src = module_path.read_text(encoding="utf-8")
    module_ast = ast.parse(src, filename=str(module_path))
    for node in module_ast.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target_symbol:
            sections = parse_docstring(ast.get_docstring(node))
            parameters = []
            param_descs: Dict[str, str] = {}
            args_section = sections.get("args", "")
            for line in args_section.splitlines():
                m = PARAM_LINE_RE.match(line.strip())
                if m:
                    param_descs[m.group(1)] = m.group(3).strip()
            for arg in node.args.args:
                if arg.arg == "self":
                    continue
                annotation = ast.unparse(arg.annotation) if arg.annotation is not None else None
                parameters.append(
                    {
                        "name": arg.arg,
                        "annotation": annotation,
                        "description": param_descs.get(arg.arg),
                    }
                )

            returns_annotation = ast.unparse(node.returns) if node.returns is not None else None
            raises_section = sections.get("raises", "")
            raises_names = []
            for line in raises_section.splitlines():
                m = RAISE_LINE_RE.match(line.strip())
                if m:
                    raises_names.append(m.group(1))

            llm_meta = {}
            if "llm_meta" in sections:
                for line in sections["llm_meta"].splitlines():
                    m = META_LINE_RE.match(line.strip())
                    if m:
                        llm_meta[m.group(1)] = m.group(2)

            tags = set()
            role = llm_meta.get("role")
            if role:
                tags.add(role.split("-", 1)[0])
            reliability = llm_meta.get("reliability")
            if reliability:
                tags.add(reliability)
            tags.add("demo")
            if "arithmetic" in module_name:
                tags.add("arithmetic")

            return CallableInfo(
                symbol=node.name,
                entrypoint=f"{module_name}:{node.name}",
                source_path=str(module_path.relative_to(BASE_DIR)),
                language="python",
                parameters=parameters,
                returns=returns_annotation or sections.get("returns"),
                raises=raises_names,
                doc_overview=sections.get("overview", ""),
                doc_example=sections.get("examples", ""),
                tags=sorted(tags),
                front_matter={},  # 可擴充 front-matter 支援
            )
    raise ValueError(f"在 {module_path} 找不到函式 {target_symbol}")


def gather_tools() -> List[Dict[str, Any]]:
    tools = []
    for tool_dir in sorted(BASE_DIR.glob(TOOL_DIR_PATTERN)):
        if not tool_dir.is_dir():
            continue
        name = tool_dir.name.split("_", 1)[-1]
        env_path_candidates = [
            tool_dir / "env_command_path.json",
            tool_dir / "env_executive_path.json",
            tool_dir / "env_command_path.yaml",
            tool_dir / "env_executive_path.yaml",
        ]
        env_path = None
        for candidate in env_path_candidates:
            if candidate.exists():
                env_path = candidate
                break
        if env_path is None:
            raise FileNotFoundError(f"{tool_dir} 中找不到環境設定檔案。")
        env_data = load_env_config(env_path)
        impl_module = env_data.get("impl_module")
        impl_attr = env_data.get("impl_attr")
        if not impl_module or not impl_attr:
            raise ValueError(f"環境設定 {env_path} 缺少 impl_module 或 impl_attr。")
        module_path = BASE_DIR / Path(impl_module.replace(".", "/")).with_suffix(".py")
        if not module_path.exists():
            raise FileNotFoundError(f"找不到模組檔案：{module_path}")
        callable_info = build_callable_info(module_path, impl_module, impl_attr)
        tool_entry = {
            "name": name,
            "package_root": str(tool_dir.relative_to(BASE_DIR)),
            "module": impl_module,
            "version": env_data.get("version"),
            "environment": {
                "path": str(env_path.relative_to(BASE_DIR)),
                **{k: v for k, v in env_data.items() if k not in {"impl_module", "impl_attr", "version"}},
                "impl_module": impl_module,
                "impl_attr": impl_attr,
            },
            "callables": [
                {
                    "symbol": callable_info.symbol,
                    "entrypoint": callable_info.entrypoint,
                    "source_path": callable_info.source_path,
                    "language": callable_info.language,
                    "parameters": callable_info.parameters,
                    "returns": callable_info.returns,
                    "raises": callable_info.raises,
                    "doc_overview": callable_info.doc_overview,
                    "doc_example": callable_info.doc_example,
                    "tags": callable_info.tags,
                    "front_matter": callable_info.front_matter,
                }
            ],
        }
        tools.append(tool_entry)
    return tools


def main() -> None:
    tools = gather_tools()
    index_doc = {
        "tools_index_version": "1.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "registry_meta": {
            "original_index": "a01_registry/TOOL_INDEX.json",
            "source_roots": [str(path.relative_to(BASE_DIR)) for path in sorted(BASE_DIR.glob(TOOL_DIR_PATTERN))],
            "scan_script": Path(__file__).name,
            "notes": [
                "工具清單與 a/b 模組結構對齊。",
                "callables 內容包含函式簽章與簡要描述。",
                "environment 直接內嵌對應環境設定的核心欄位。",
            ],
        },
        "tools": tools,
    }
    REGISTRY_PATH.write_text(json.dumps(index_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ 產生 {REGISTRY_PATH}, 工具數：{len(tools)}")


if __name__ == "__main__":
    main()
