# Bridge-Failure Listing

## Purpose

跨多份資訊來源時,顯式列出無法建立對應關係的概念缺口,並禁止 Agent 自行腦補橋接。

## When to Use

當以下任一條件成立時觸發:

- 同時處理 2 份以上來自不同作者 / 部門 / 系統的文件
- 任務涉及「整合」、「對接」、「翻譯」、「合併」多個資訊源
- 收到的資訊使用了不同的術語體系但討論可能相關的主題
- 上游 API 文件 vs 下游使用文件
- 跨部門工具串接(A 部門工具 → B 部門使用)

## When NOT to Use

- 單一來源的文件分析(沒有 bridge 可言)
- 純粹的事實查詢(不需要跨源整合)
- 創意探索任務(過早結構化會殺死探索)

## Procedure

### Step 1 — 概念盤點

對每份文件,列出:
- 核心概念與術語
- 輸出格式 / 欄位定義
- 輸入假設 / 前置條件
- 角色與責任歸屬

### Step 2 — 對應嘗試

把每個概念嘗試對應到其他文件中的對等物。注意:看似不同名但可能同義的詞要納入考慮(例:`latency` / `response time` / `回應時間`)。

### Step 3 — 對應結果分類

每組對應必須歸類為以下其中一類:

- **✓ 確認對應**:雙方有明確定義且一致
- **⚠ 疑似對應但低信心**:能自圓其說但無證據
- **✗ 無法對應**:找不到對等物
- **◯ 單向存在**:只在一份文件出現,另一份完全沒提

### Step 4 — 輸出問題清單

對 ⚠ 和 ✗ 類項目,輸出結構化資訊:

```yaml
- 概念名稱: <name>
  出處文件: <doc>
  分類: <⚠ | ✗ | ◯>
  無法對應的原因: <reason>
  建議詢問對象: <author | maintainer | user>
  不釐清的下游風險: <risk>
```

## Strict Prohibitions

- 不要替任何 ⚠ 項目「合理化」一個對應關係
- 不要在沒有證據時把 ⚠ 升級成 ✓
- 寧可多列 ⚠,不要漏列
- 不要用「應該是」、「想必是」、「合理推測」這類語言把推測偽裝成結論

## Output Format

```yaml
bridge_audit:
  confirmed_bridges:
    - source_a: <concept>
      source_b: <concept>
      evidence: <quote or reference>

  uncertain_bridges:
    - source_a: <concept>
      source_b: <concept>
      reason_uncertain: <why>
      who_to_ask: <role>

  unbridged_concepts:
    - concept: <name>
      source: <doc>
      expected_in: <other_doc>
      who_to_ask: <role>
      downstream_risk: <description>

  one_sided_concepts:
    - concept: <name>
      source: <doc>
      note: <whether this is by design or oversight>
```

## Composition Hints

- 跑完此 skill 後,對 unbridged 項目套用 `assumption-surfacing` 挖掘隱性假設
- 對涉及數字的 unbridged 項目,套用 `numerical-consistency-audit`
- 對需要詢問人類的項目,套用 `source-authority-tagging` 確認該問誰
