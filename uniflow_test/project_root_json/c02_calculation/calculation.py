"""概述（Overview）
應用已註冊於 Universal Flow Registry Framework 的算術工具，計算表達式 (2 + 5 * 3) / 2。

參數（Args）
無。

回傳值（Returns）
無直接回傳值；模組提供函式 evaluate_expression() 與主程式進入點。

異常（Raises）
匯入階段不會主動拋出額外異常。

副作用（Side Effects）
執行 main() 時會在標準輸出列印結果。

限制（Constraints）
依賴 b02_addition、b03_multiply、b04_divide 套件；需存在於 Python 模組搜尋路徑。

範例（Examples）
>>> from c02_calculation.calculation import evaluate_expression
>>> evaluate_expression()
8.5

LLM-META
- module: c02_calculation
- purpose: fixed-expression-demo
- locale: zh-Hant
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure the project root is discoverable when running as a script.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from b03_multiply.packages.arithmetic import mul
from b04_divide.packages.arithmetic import div

ADDITION_ENV_PATH = PROJECT_ROOT / "b02_addition" / "env_command_path.json"


def load_env_config(file_path: Path) -> Dict[str, Any]:
    """概述（Overview）
    解析環境設定檔，支援 JSON 與極簡 YAML 規則，包含字串、數值及多行區塊。

    參數（Args）
    - file_path (Path): 設定檔案路徑。

    回傳值（Returns）
    Dict[str, Any]: 解析後的鍵值資料。

    異常（Raises）
    FileNotFoundError: 當檔案不存在時拋出。
    ValueError: 當檔案格式不符預期時拋出。

    副作用（Side Effects）
    讀取檔案。

    限制（Constraints）
    支援 JSON 物件格式，或每行一個鍵值對與 `|` 標記的縮排多行文字區塊。

    範例（Examples）
    >>> load_env_config(Path("b02_addition/env_command_path.json"))  # 須先存在檔案

    LLM-META
    - function: load_env_config
    - parser: mini-yaml
    - resilience: medium
    """
    if not file_path.exists():
        raise FileNotFoundError(f"找不到環境設定檔案：{file_path}")

    raw_text = file_path.read_text(encoding="utf-8")
    stripped_text = raw_text.strip()
    if stripped_text.startswith("{") or stripped_text.startswith("["):
        try:
            parsed_json = json.loads(stripped_text)
            if not isinstance(parsed_json, dict):
                raise ValueError("環境設定需為 JSON 物件。")
            return parsed_json
        except json.JSONDecodeError as exc:
            raise ValueError(f"環境設定不是有效的 JSON：{exc}") from exc

    lines = raw_text.splitlines()
    config: Dict[str, Any] = {}
    index = 0
    total = len(lines)

    def parse_scalar(token: str) -> Any:
        if token.startswith('"') and token.endswith('"'):
            return token[1:-1]
        if token.startswith("'") and token.endswith("'"):
            return token[1:-1]
        return token

    while index < total:
        raw_line = lines[index]
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
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


def invoke_addition_via_shell(x: float, y: float) -> float:
    """概述（Overview）
    讀取加法工具的環境設定，組合 shell 腳本字串並透過 subprocess 執行以取得加總結果。

    參數（Args）
    - x (float): 第一個加數。
    - y (float): 第二個加數。

    回傳值（Returns）
    float: 來自子程序輸出的加總結果。

    異常（Raises）
    RuntimeError: 當環境檔缺少 run_shell_template 或子程序回傳非數值時拋出。
    FileNotFoundError: 當環境設定檔不存在時拋出。
    subprocess.CalledProcessError: 當子程序執行失敗時拋出。

    副作用（Side Effects）
    透過子程序執行額外的 Python 腳本。

    限制（Constraints）
    預期 run_shell_template 以 str.format 語法包含 project_root、x、y 參數。

    範例（Examples）
    >>> invoke_addition_via_shell(1.0, 2.0)
    3.0

    LLM-META
    - function: invoke_addition_via_shell
    - mechanism: subprocess-shell
    - safety: medium
    """
    env_config = load_env_config(ADDITION_ENV_PATH)
    template = env_config.get("run_shell_template")
    if not isinstance(template, str) or not template.strip():
        raise RuntimeError("加法工具環境檔案缺少有效的 run_shell_template 欄位。")
    script = template.format(project_root=str(PROJECT_ROOT), x=float(x), y=float(y))
    try:
        result = subprocess.run(
            ["bash", "-lc", script],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr_text = exc.stderr.strip() if exc.stderr else "(no stderr)"
        raise RuntimeError(
            f"加法子程序執行失敗，退出碼 {exc.returncode}，訊息：{stderr_text}"
        ) from exc
    stdout = result.stdout.strip()
    try:
        return float(stdout.splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"加法子程序回傳非數值輸出：{stdout!r}") from exc


def evaluate_expression() -> float:
    """概述（Overview）
    使用註冊的算術工具計算表達式 (2 + 5 * 3) / 2 並回傳結果。

    參數（Args）
    無。

    回傳值（Returns）
    float: 表達式 (2 + 5 * 3) / 2 的計算結果，預期為 8.5。

    異常（Raises）
    ValueError: 若工具偵測到非有限數值輸入時。
    ZeroDivisionError: 若除法工具偵測到除以零（理論上不會在此範例發生）。

    副作用（Side Effects）
    無。

    限制（Constraints）
    工具假設輸入皆為有限浮點數；此函式未涵蓋錯誤恢復邏輯。

    範例（Examples）
    >>> evaluate_expression()
    8.5

    LLM-META
    - function: evaluate_expression
    - stability: deterministic
    - dependency: registry-tools
    """
    product = mul(5.0, 3.0)
    total = invoke_addition_via_shell(2.0, product)
    result = div(total, 2.0)
    return result


def main() -> None:
    """概述（Overview）
    呼叫 evaluate_expression() 並將結果列印到標準輸出。

    參數（Args）
    無。

    回傳值（Returns）
    無。

    異常（Raises）
    ValueError: 若工具執行導致數值錯誤。
    ZeroDivisionError: 若除法工具偵測到除以零。

    副作用（Side Effects）
    於標準輸出列印計算結果。

    限制（Constraints）
    無額外限制；在工具模組可匯入的環境下運作。

    範例（Examples）
    >>> main()  # 於命令列執行
    Result: 8.5

    LLM-META
    - function: main
    - interface: cli-friendly
    - i18n: zh-Hant
    """
    result = evaluate_expression()
    print(f"Result: {result}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
