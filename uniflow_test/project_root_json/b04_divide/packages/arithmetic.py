from __future__ import annotations
import math

def div(x: float, y: float) -> float:
    """概述（Overview）
    計算兩個浮點數的商並提供除以零的防護。

    參數（Args）
    - x (float): 被除數，必須為有限浮點數。
    - y (float): 除數，必須為有限浮點數且不可為零。

    回傳值（Returns）
    float: x 除以 y 的結果。

    異常（Raises）
    ValueError: 當任一輸入不是有限浮點數時拋出。
    ZeroDivisionError: 當除數接近零時拋出。

    副作用（Side Effects）
    無。

    限制（Constraints）
    使用相對與絕對誤差 1e-12 判定除數是否為零。

    範例（Examples）
    >>> div(10.0, 2.0)
    5.0

    LLM-META
    - role: arithmetic-div
    - reliability: deterministic
    - complexity: low
    """
    if not math.isfinite(x):
        raise ValueError("除法輸入 x 必須為有限數值。")
    if not math.isfinite(y):
        raise ValueError("除法輸入 y 必須為有限數值。")
    if math.isclose(y, 0.0, rel_tol=1e-12, abs_tol=1e-12):
        raise ZeroDivisionError("除法的除數不可為零。")
    return x / y
