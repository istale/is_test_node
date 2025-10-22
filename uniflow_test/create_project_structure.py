#!/usr/bin/env python3
"""
create_project_structure.py

Create the project_root layout with the registry, addition, multiply, divide, and invoker folders
and the placeholder files described in the spec.
"""

from pathlib import Path

PROJECT_ROOT = Path("project_root")

DIRS_AND_FILES = {
    PROJECT_ROOT / "a01_registry": ["TOOL_INDEX.yaml"],
    PROJECT_ROOT / "b01_addition": ["env_executive_path.yaml"],
    PROJECT_ROOT / "b02_addition" / "packages": [],
    PROJECT_ROOT / "b03_multiply": ["env_executive_path.yaml"],
    PROJECT_ROOT / "b03_multiply" / "packages": [],
    PROJECT_ROOT / "b04_divide": ["env_executive_path.yaml"],
    PROJECT_ROOT / "b04_divide" / "packages": [],
    PROJECT_ROOT / "c01_invoker": ["run_pipeline.py"],
}

PLACEHOLDERS = {
    "TOOL_INDEX.yaml": "# 🔍 全域查找表 (Registry)\n",
    "env_executive_path.yaml": "# 指定執行檔路徑與版本設定\n",
    "run_pipeline.py": '# 🧠 通用執行器（讀 registry → 執行）\n',
}


def main() -> None:
    for directory, files in DIRS_AND_FILES.items():
        directory.mkdir(parents=True, exist_ok=True)
        for filename in files:
            file_path = directory / filename
            if not file_path.exists():
                file_path.write_text(PLACEHOLDERS.get(filename, ""), encoding="utf-8")


if __name__ == "__main__":
    main()
