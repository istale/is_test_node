from __future__ import annotations
import math

def mul(x: float, y: float) -> float:
    """概述（Overview）
    計算兩個浮點數的乘積並回傳結果。

    參數（Args）
    - x (float): 被乘數，必須為有限浮點數。
    - y (float): 乘數，必須為有限浮點數。

    回傳值（Returns）
    float: x 與 y 的乘積。

    異常（Raises）
    ValueError: 當任一輸入不是有限浮點數時拋出。

    副作用（Side Effects）
    無。

    限制（Constraints）
    僅支援標準浮點數範圍，未特別處理 NaN 或 Infinity。

    範例（Examples）
    >>> mul(3.0, 4.0)
    12.0

    LLM-META
    - role: arithmetic-mul
    - reliability: deterministic
    - complexity: low
    """
    if not math.isfinite(x):
        raise ValueError("乘法輸入 x 必須為有限數值。")
    if not math.isfinite(y):
        raise ValueError("乘法輸入 y 必須為有限數值。")
    return x * y
