"""概述（Overview）
命令列執行器，讀取註冊表並依參數執行 Universal Flow Registry Framework 的示範管線。

參數（Args）
無。

回傳值（Returns）
無。

異常（Raises）
主程式會攔截常見錯誤並以使用者可讀訊息呈現，其餘錯誤以退出碼表達。

副作用（Side Effects）
從標準輸出列印執行紀錄；錯誤時輸出到標準錯誤。

限制（Constraints）
僅支援簡化為 JSON 風格的 YAML 結構與示範所需的算術工具。

範例（Examples）
$ python run_pipeline.py --a 3 --b 5 --c 10 --d 4
產出步驟紀錄並顯示 Final result: 20

LLM-META
- entrypoint: run_pipeline
- domain: pipeline-runner
- compliance: demo
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def parse_arguments() -> argparse.Namespace:
    """概述（Overview）
    解析命令列參數以取得管線執行所需的輸入數值與設定。

    參數（Args）
    無。

    回傳值（Returns）
    argparse.Namespace: 命令列參數對應的命名空間物件。

    異常（Raises）
    無。

    副作用（Side Effects）
    讀取並解析 sys.argv。

    限制（Constraints）
    僅支援 --a、--b、--c、--d、--pipeline、--registry 等選項。

    範例（Examples）
    >>> # 需於命令列環境使用，以下僅示意
    >>> args = parse_arguments()

    LLM-META
    - intent: parse-cli
    - audience: developer
    - format: argparse
    """
    parser = argparse.ArgumentParser(
        description="Universal Flow Registry Framework demo pipeline runner."
    )
    parser.add_argument("--a", type=float, required=True, help="第一個輸入值。")
    parser.add_argument("--b", type=float, required=True, help="第二個輸入值。")
    parser.add_argument("--c", type=float, required=True, help="第三個輸入值。")
    parser.add_argument("--d", type=float, required=True, help="第四個輸入值。")
    parser.add_argument(
        "--pipeline",
        type=str,
        default=None,
        help="自訂管線表示法，例如 '((add a b) (mul _ c) (div _ d))'。",
    )
    parser.add_argument(
        "--registry",
        type=str,
        default=None,
        help="TOOL_INDEX.yaml 的路徑；預設為專案內的 a01_registry/TOOL_INDEX.yaml。",
    )
    return parser.parse_args()


def parse_simple_yaml(file_path: Path) -> Any:
    """概述（Overview）
    讀取指定檔案並以極精簡 YAML 規範解析為 Python 資料結構。

    參數（Args）
    - file_path (Path): 目標 YAML 檔案的路徑。

    回傳值（Returns）
    Any: 解析後的 Python 資料結構。

    異常（Raises）
    ValueError: 當檔案格式不符預期或縮排錯誤時拋出。
    FileNotFoundError: 當檔案不存在時拋出。

    副作用（Side Effects）
    讀取檔案內容。

    限制（Constraints）
    僅支援以兩個空白縮排的層級、字串/數值/布林/Null、巢狀字典與清單。

    範例（Examples）
    >>> parse_simple_yaml(Path("example.yaml"))  # 需先建構檔案

    LLM-META
    - capability: parse-yaml
    - strategy: indentation-stack
    - safety: high
    """
    if not file_path.exists():
        raise FileNotFoundError(f"找不到檔案：{file_path}")
    raw_lines = file_path.read_text(encoding="utf-8").splitlines()
    filtered_lines: List[str] = []
    for raw_line in raw_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        filtered_lines.append(raw_line)

    # First attempt JSON parsing for JSON 風格檔案
    cleaned_text = "\n".join(filtered_lines)
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        pass

    tokens: List[Tuple[int, str]] = []
    for raw_line in filtered_lines:
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2 != 0:
            raise ValueError(f"縮排必須為 2 的倍數：{raw_line!r}")
        tokens.append((indent, raw_line[indent:].rstrip()))

    def parse_scalar(text: str) -> Any:
        lowered = text.lower()
        if lowered in {"null", "~"}:
            return None
        if lowered in {"true", "false"}:
            return lowered == "true"
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        if text.startswith("'") and text.endswith("'"):
            return text[1:-1].replace("\\'", "'").replace("\\\\", "\\")
        try:
            if "." in text:
                return float(text)
            return int(text)
        except ValueError:
            return text

    def parse_block(index: int, indent: int) -> Tuple[Any, int]:
        if index >= len(tokens):
            return {}, index
        current_indent, content = tokens[index]
        if current_indent < indent:
            return {}, index
        if content.startswith("-"):
            return parse_list(index, indent)
        return parse_mapping(index, indent)

    def parse_mapping(index: int, indent: int) -> Tuple[Dict[str, Any], int]:
        mapping: Dict[str, Any] = {}
        while index < len(tokens):
            current_indent, content = tokens[index]
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ValueError(f"縮排錯誤，預期 {indent} 空白：{content!r}")
            if content.startswith("-"):
                raise ValueError(f"未指定鍵值卻遇到清單項目：{content!r}")
            if ":" not in content:
                raise ValueError(f"無法辨識鍵值對：{content!r}")
            key, remainder = content.split(":", 1)
            key = key.strip()
            if not key:
                raise ValueError("鍵名稱不可為空字串。")
            value_part = remainder.strip()
            index += 1
            if not value_part:
                next_indent = indent + 2
                if index >= len(tokens) or tokens[index][0] < next_indent:
                    value = {}
                else:
                    value, index = parse_block(index, next_indent)
            elif value_part == "|":
                block_lines: List[str] = []
                base_indent = indent + 2
                while index < len(tokens):
                    next_indent, next_content = tokens[index]
                    if next_indent < base_indent:
                        break
                    indent_diff = max(0, next_indent - base_indent)
                    block_lines.append(" " * indent_diff + next_content)
                    index += 1
                value = "\n".join(block_lines)
            else:
                value = parse_scalar(value_part)
            mapping[key] = value
        return mapping, index

    def parse_list(index: int, indent: int) -> Tuple[List[Any], int]:
        sequence: List[Any] = []
        while index < len(tokens):
            current_indent, content = tokens[index]
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ValueError(f"清單項目的縮排不正確：{content!r}")
            if not content.startswith("-"):
                break
            item_content = content[1:].strip()
            index += 1
            if not item_content:
                next_indent = indent + 2
                if index >= len(tokens) or tokens[index][0] < next_indent:
                    sequence.append({})
                else:
                    value, index = parse_block(index, next_indent)
                    sequence.append(value)
            else:
                sequence.append(parse_scalar(item_content))
        return sequence, index

    parsed, end_index = parse_block(0, 0)
    if end_index != len(tokens):
        raise ValueError("YAML 解析未消耗所有內容，可能存在縮排錯誤。")
    return parsed


def load_registry(registry_path: Path) -> Dict[str, Any]:
    """概述（Overview）
    讀取並驗證註冊表 TOOL_INDEX.yaml 的整體資料結構。

    參數（Args）
    - registry_path (Path): 註冊表檔案的路徑。

    回傳值（Returns）
    Dict[str, Any]: 註冊表的結構化內容。

    異常（Raises）
    ValueError: 當檔案內容不是對應字典格式時拋出。
    FileNotFoundError: 當檔案不存在時拋出。

    副作用（Side Effects）
    讀取檔案內容。

    限制（Constraints）
    檔案須符合簡化的 YAML 結構，縮排以兩個空白為單位。

    範例（Examples）
    >>> registry = load_registry(Path("a01_registry/TOOL_INDEX.yaml"))

    LLM-META
    - responsibility: load-registry
    - requirement: mini-yaml
    - priority: high
    """
    data = parse_simple_yaml(registry_path)
    if not isinstance(data, dict):
        raise ValueError(f"註冊表 {registry_path} 必須為物件結構。")
    return data


def build_tool_catalog(registry_path: Path, registry_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """概述（Overview）
    根據註冊表載入工具模組與環境設定，建立呼叫目錄。

    參數（Args）
    - registry_path (Path): 註冊表檔案路徑，用於推導專案根目錄。
    - registry_data (Dict[str, Any]): 註冊表解析後的資料。

    回傳值（Returns）
    Dict[str, Dict[str, Any]]: 以 callable 名稱為鍵的工具資訊字典。

    異常（Raises）
    ValueError: 當註冊表或環境檔案格式不符期待時拋出。
    FileNotFoundError: 當環境檔案不存在時拋出。
    ImportError: 當模組載入失敗時拋出。

    副作用（Side Effects）
    可能修改 sys.path 以確保專案根目錄可被 Python 匯入。

    限制（Constraints）
    僅支援每個工具列出可呼叫名稱清單，並要求環境檔案中的 impl_attr 包含於其中。

    範例（Examples）
    >>> catalog = build_tool_catalog(Path("a01_registry/TOOL_INDEX.yaml"), registry)

    LLM-META
    - task: build-catalog
    - relation: registry-env
    - scope: dynamic-import
    """
    project_root = registry_path.parent.parent
    root_str = str(project_root.resolve())
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    tools = registry_data.get("tools")
    if not isinstance(tools, list) or not tools:
        raise ValueError("註冊表中缺少 tools 清單或格式錯誤。")

    catalog: Dict[str, Dict[str, Any]] = {}
    for tool in tools:
        if not isinstance(tool, dict):
            raise ValueError("tools 清單中的每個項目必須是物件。")
        name = tool.get("name")
        module_name = tool.get("module")
        env_rel_path = tool.get("env_file")
        callables = tool.get("callables")
        if not isinstance(name, str) or not name:
            raise ValueError("工具項目缺少有效的 name 欄位。")
        if not isinstance(module_name, str) or not module_name:
            raise ValueError(f"工具 {name} 缺少 module 定義。")
        if not isinstance(env_rel_path, str) or not env_rel_path:
            raise ValueError(f"工具 {name} 缺少 env_file 定義。")
        if not isinstance(callables, list) or not callables:
            raise ValueError(f"工具 {name} 缺少 callables 清單。")

        env_path = (project_root / env_rel_path).resolve()
        searched_paths: List[Path] = [env_path]
        if not env_path.exists():
            fallback_candidates: List[Path] = []
            if env_path.suffix.lower() != ".json":
                fallback_candidates.append(env_path.with_suffix(".json"))
            name_variants = [
                env_path.name.replace("executive", "command"),
                env_path.name.replace("executive_path", "command_path"),
            ]
            for variant in name_variants:
                if variant != env_path.name:
                    fallback_candidates.append(env_path.parent / variant)
                    fallback_candidates.append((env_path.parent / variant).with_suffix(".json"))
            fallback_candidates.append(env_path.parent / "env_command_path.json")
            fallback_candidates.append(env_path.parent / "env_executive_path.json")
            for candidate in fallback_candidates:
                candidate = candidate.resolve()
                if candidate not in searched_paths:
                    searched_paths.append(candidate)
                if candidate.exists():
                    env_path = candidate
                    break
        if not env_path.exists():
            tried = ", ".join(str(path) for path in searched_paths)
            raise FileNotFoundError(f"找不到工具 {name} 的環境檔案；已嘗試：{tried}")
        env_data = parse_simple_yaml(env_path)
        if not isinstance(env_data, dict):
            raise ValueError(f"環境檔案 {env_path} 必須是物件。")

        env_module = env_data.get("impl_module")
        env_attr = env_data.get("impl_attr")
        if env_module != module_name:
            raise ValueError(
                f"工具 {name} 的 registry 模組 {module_name} 與環境模組 {env_module} 不一致。"
            )
        if not isinstance(env_attr, str) or not env_attr:
            raise ValueError(f"環境檔案 {env_path} 缺少 impl_attr 欄位。")
        if env_attr not in callables:
            raise ValueError(
                f"環境檔案 {env_path} 的 impl_attr {env_attr} 未列於 callables 中。"
            )

        module = importlib.import_module(module_name)

        for callable_name in callables:
            if not isinstance(callable_name, str) or not callable_name:
                raise ValueError(f"工具 {name} 的 callables 項目必須為非空字串。")
            function = getattr(module, callable_name, None)
            if function is None or not callable(function):
                raise ValueError(
                    f"模組 {module_name} 缺少可呼叫的成員 {callable_name}。"
                )
            if callable_name in catalog:
                raise ValueError(f"偵測到重複 callable 名稱：{callable_name}")
            catalog[callable_name] = {
                "callable": function,
                "tool": tool,
                "environment": env_data,
                "env_path": str(env_path),
            }
    return catalog


def parse_pipeline(pipeline_text: str) -> List[List[str]]:
    """概述（Overview）
    將管線字串解析為步驟列表，每個步驟為函式名稱與其參數。

    參數（Args）
    - pipeline_text (str): 以括號表示的管線描述字串。

    回傳值（Returns）
    List[List[str]]: 每個子清單代表一個步驟，第一個元素為函式名稱。

    異常（Raises）
    ValueError: 當字串格式不正確或括號不匹配時拋出。

    副作用（Side Effects）
    無。

    限制（Constraints）
    僅支援以空白分隔的語彙；不支援具名參數或巢狀函式呼叫。

    範例（Examples）
    >>> parse_pipeline("((add a b) (mul _ c))")
    [['add', 'a', 'b'], ['mul', '_', 'c']]

    LLM-META
    - function: parse-pipeline
    - grammar: s-expression-lite
    - robustness: medium
    """
    if not isinstance(pipeline_text, str) or not pipeline_text.strip():
        raise ValueError("管線字串不可為空。")
    tokens: List[str] = []
    current: List[str] = []
    for char in pipeline_text.strip():
        if char in "()":
            if current:
                tokens.append("".join(current))
                current.clear()
            tokens.append(char)
        elif char.isspace():
            if current:
                tokens.append("".join(current))
                current.clear()
        else:
            current.append(char)
    if current:
        tokens.append("".join(current))

    stack: List[List[Any]] = []
    current_list: List[Any] = []
    for token in tokens:
        if token == "(":
            stack.append(current_list)
            new_list: List[Any] = []
            current_list.append(new_list)
            current_list = new_list
        elif token == ")":
            if not stack:
                raise ValueError("管線括號不匹配：過多的右括號。")
            current_list = stack.pop()
        else:
            current_list.append(token)
    if stack:
        raise ValueError("管線括號不匹配：缺少右括號。")
    if len(current_list) != 1 or not isinstance(current_list[0], list):
        raise ValueError("管線表示法必須包裹於一組外層括號。")
    steps = current_list[0]
    if not all(isinstance(step, list) and step for step in steps):
        raise ValueError("管線步驟格式錯誤，每個步驟需為非空清單。")
    return [list(map(str, step)) for step in steps]


def resolve_argument(token: str, variables: Dict[str, float], accumulator: Optional[float]) -> float:
    """概述（Overview）
    將管線中的參數語彙轉換為實際數值。

    參數（Args）
    - token (str): 原始語彙，可能為變數名稱、數值或底線表示累積值。
    - variables (Dict[str, float]): 命令列提供的數值映射。
    - accumulator (Optional[float]): 前一步的運算結果。

    回傳值（Returns）
    float: 解析後的數值。

    異常（Raises）
    ValueError: 當語彙無法解析或累積值不存在時拋出。

    副作用（Side Effects）
    無。

    限制（Constraints）
    僅支援 a、b、c、d、_ 或可轉換為 float 的字串。

    範例（Examples）
    >>> resolve_argument("a", {"a": 1.0}, None)
    1.0

    LLM-META
    - purpose: resolve-token
    - supports: accumulator
    - strictness: high
    """
    if token == "_":
        if accumulator is None:
            raise ValueError("管線在使用 '_' 前必須先產生累積值。")
        return float(accumulator)
    if token in variables:
        return float(variables[token])
    try:
        return float(token)
    except ValueError as exc:  # pragma: no cover - demo context
        raise ValueError(f"無法解析管線參數 '{token}'。") from exc


def evaluate_pipeline(
    steps: Sequence[Sequence[str]],
    tool_catalog: Dict[str, Dict[str, Any]],
    variables: Dict[str, float],
) -> Tuple[float, List[str]]:
    """概述（Overview）
    依序執行管線步驟，並收集每一步的文字紀錄。

    參數（Args）
    - steps (Sequence[Sequence[str]]): 解析後的步驟清單。
    - tool_catalog (Dict[str, Dict[str, Any]]): 可呼叫工具的查詢目錄。
    - variables (Dict[str, float]): 初始變數對應的數值。

    回傳值（Returns）
    Tuple[float, List[str]]: 最終結果與步驟紀錄列表。

    異常（Raises）
    ValueError: 當步驟定義缺失或工具未註冊時拋出。
    RuntimeError: 當工具執行失敗或回傳非數值時拋出。

    副作用（Side Effects）
    無。

    限制（Constraints）
    假設所有工具皆為同步且回傳數值。

    範例（Examples）
    >>> evaluate_pipeline([["add", "a", "b"]], {"add": {"callable": lambda x, y: x + y}}, {"a": 1.0, "b": 2.0})
    (3.0, ['[1] add(1, 2) -> 3'])

    LLM-META
    - engine: pipeline-executor
    - logging: stepwise
    - mode: synchronous
    """
    if not steps:
        raise ValueError("管線中沒有步驟可執行。")
    accumulator: Optional[float] = None
    logs: List[str] = []
    for index, step in enumerate(steps, start=1):
        if not step:
            raise ValueError(f"第 {index} 個步驟為空。")
        func_name = step[0]
        entry = tool_catalog.get(func_name)
        if entry is None:
            raise ValueError(f"工具目錄中找不到函式：{func_name}")
        function = entry["callable"]
        arguments = [resolve_argument(token, variables, accumulator) for token in step[1:]]
        try:
            result = function(*arguments)
        except Exception as exc:  # pragma: no cover - demo context
            raise RuntimeError(f"執行工具 '{func_name}' 時發生錯誤：{exc}") from exc
        if not isinstance(result, (int, float)):
            raise RuntimeError(f"工具 '{func_name}' 回傳非數值結果：{result!r}")
        accumulator = float(result)
        arg_text = ", ".join(format_number(value) for value in arguments)
        logs.append(f"[{index}] {func_name}({arg_text}) -> {format_number(accumulator)}")
    assert accumulator is not None  # 保證至少執行一個步驟
    return accumulator, logs


def format_number(value: float) -> str:
    """概述（Overview）
    將數值以簡潔格式轉為字串，方便日誌與輸出。

    參數（Args）
    - value (float): 需格式化的數值。

    回傳值（Returns）
    str: 適合閱讀的數值字串。

    異常（Raises）
    無。

    副作用（Side Effects）
    無。

    限制（Constraints）
    採用 6 位有效數字輸出，保持範例簡潔。

    範例（Examples）
    >>> format_number(3.1415926)
    '3.14159'

    LLM-META
    - utility: format-number
    - style: concise
    - locale: neutral
    """
    if isinstance(value, (int, float)):
        return f"{float(value):.6g}"
    return str(value)


def main() -> None:
    """概述（Overview）
    結合所有子程序，執行命令列介面的完整流程。

    參數（Args）
    無。

    回傳值（Returns）
    無。

    異常（Raises）
    無；函式內部會攔截常見錯誤並以退出碼 1 結束程式。

    副作用（Side Effects）
    從標準輸出列印成功訊息；錯誤時輸出到標準錯誤並終止程式。

    限制（Constraints）
    需在專案結構完整的情況下執行，以確保可找到註冊表與模組。

    範例（Examples）
    >>> # 需於命令列環境執行
    >>> main()

    LLM-META
    - role: cli-entrypoint
    - behavior: user-facing
    - termination: sys-exit
    """
    args = parse_arguments()
    default_registry = Path(__file__).resolve().parent.parent / "a01_registry" / "TOOL_INDEX.yaml"
    registry_path = Path(args.registry).resolve() if args.registry else default_registry
    try:
        registry_data = load_registry(registry_path)
        tool_catalog = build_tool_catalog(registry_path, registry_data)
        pipeline_text = args.pipeline
        if pipeline_text is None:
            pipelines = registry_data.get("pipelines")
            if not isinstance(pipelines, dict):
                raise ValueError("註冊表中缺少 pipelines 定義。")
            demo_pipeline = pipelines.get("demo_pipeline")
            if not isinstance(demo_pipeline, dict):
                raise ValueError("註冊表中缺少 demo_pipeline 定義。")
            pipeline_text = demo_pipeline.get("steps")
            if not isinstance(pipeline_text, str) or not pipeline_text.strip():
                raise ValueError("demo_pipeline.steps 必須為非空字串。")
        pipeline_text = pipeline_text.strip()
        variables = {"a": args.a, "b": args.b, "c": args.c, "d": args.d}
        result, logs = evaluate_pipeline(parse_pipeline(pipeline_text), tool_catalog, variables)
    except (ValueError, RuntimeError, FileNotFoundError, ImportError) as exc:
        print(f"[錯誤] {exc}", file=sys.stderr)
        sys.exit(1)

    for line in logs:
        print(line)
    print(f"Final result: {format_number(result)}")


if __name__ == "__main__":  # pragma: no cover - CLI 入口
    main()
