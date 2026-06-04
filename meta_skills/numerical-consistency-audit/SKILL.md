# Numerical Consistency Audit

## Purpose

跨多份文件審查規格數字時,不只找不一致,還要**判斷不一致的性質**,以決定該問什麼問題、該由誰裁決。

## When to Use

- 規格文件 vs 實作文件的對齊
- 多版本 spec 並存(API v1 / v2 文件混雜)
- 上下游契約檢查(前端 spec vs 後端 spec)
- 性能基準 vs SLA 文件
- 安全合規數值(密碼長度、超時時間、retry 次數)
- 商務合約中的數字條款

## When NOT to Use

- 單一文件內的數字檢查(沒有跨源比對需要)
- 數字本身是估算 / 預測性質,不期望精確一致

## Procedure

### Step 1 — 數字盤點

對每份文件,提取所有規格數字。每筆記錄:

- **數值**(含單位)
- **所指對象**(什麼東西的什麼屬性)
- **適用條件**(在什麼情境下這個數字成立)
- **出處**(文件名 + 章節)
- **表述強度**(必須 / 建議 / 預期 / 上限 / 下限 / 典型值)

### Step 2 — 配對

找出「指涉同一件事」的數字組,做配對表。

注意:看似不同名但其實同一件事的詞要合併處理(例:`latency` / `response time` / `回應時間`)。

### Step 3 — 不一致分類

對每組配對,判斷不一致屬於哪一類(可多選):

- `[A. 真衝突]` 同一對象、同一條件、同一單位、不同數字
- `[B. 單位/換算差]` 表面不同但換算後一致或可能一致
- `[C. 強度差]` 一個是上限、一個是典型(可能其實一致)
- `[D. 條件差]` 適用條件不同,不能直接比
- `[E. 時序差]` 文件版本不同,可能其中一份過時
- `[F. 粒度差]` 計量粒度不同(per-x vs per-y)
- `[G. 層級差]` 一個對外、一個對內;一個 spec、一個實作
- `[H. 隱性依賴]` 數字之間有因果或推導關係,看似不一致實則受限於彼此
- `[I. 無法判斷]` 資訊不足以歸類

### Step 4 — 問題生成

對每個不一致,生成具體問題,包含:

- 兩個數字各自是什麼
- 你判斷它們屬於哪一類不一致
- 如果是 `[I]`,說明你需要什麼資訊才能歸類
- 如果是 `[A]`,標 `[Critical]`,必須立刻解決
- 如果是 `[E]`,建議確認哪份是現行版本
- 如果是 `[D]` 或 `[G]`,建議在文件中明確標註適用條件以避免下游誤用

### Step 5 — 風險評估

對每個未解決的不一致,評估:

- 如果 Agent 自己選一邊用,選錯的後果是什麼?
- 在拿到答案前,Agent 該採取哪個值作為暫時策略,為什麼?

## Strict Prohibitions

- 不要直接「取平均」、「取較保守值」之類的妥協方案 — 這是把問題藏起來
- 不要因為一個數字「看起來比較合理」就採信它
- 不要把單位換算當成「沒問題」(即使數字一致,也要 flag 出來提醒文件統一單位)
- 不要漏掉表述強度的差異(「最多 100ms」和「約 100ms」是兩件事)
- 不要在類別 `[I. 無法判斷]` 時硬選一類 — 寧可標未知,也不要假分類

## Output Format

```yaml
numerical_audit:
  inventory:
    - value: <number>
      unit: <unit>
      refers_to: <object.attribute>
      condition: <when this applies>
      source: <doc + section>
      strength: <must | should | typical | upper_bound | lower_bound>

  pairings:
    - topic: <what is being measured>
      values:
        - { value, unit, source, strength }
        - { value, unit, source, strength }
      classification: <A | B | C | D | E | F | G | H | I>
      classification_reasoning: <why this category>
      severity: <Critical | High | Medium | Low>

      generated_question: <concrete question>
      who_to_ask: <role>
      interim_strategy:
        chosen_value: <which one to use temporarily>
        reasoning: <why this is safer>

  doc_quality_recommendations:
    - issue: <e.g. "文件 A 沒標註單位">
      recommendation: <fix>
```

## Composition Hints

- **必須**先跑或同時跑 `quantitative-provenance-tracking` — 不知道數字怎麼來的,無法準確分類不一致
- 與 `boundary-condition-probing` 配合:典型值不一致時,常常邊界值更有差異
- 與 `source-authority-tagging` 配合:`[A. 真衝突]` 的裁決需要先知道誰能裁決
- 跑完此 skill 後,所有 `[Critical]` 項目套用 `reversibility-triage` 決定是否阻斷後續流程

## 一個容易被忽略的設計重點

數字一致性的真正問題不是「數字不同」,而是「**不同的原因有不同的處理路徑**」:

- `[A]` 必須裁決 — 不能將就
- `[B]` 可以技術解決 — 文件補單位即可
- `[D] [G]` 可以澄清解決 — 文件補適用條件即可
- `[E]` 流程解決 — 確認版本管理即可
- `[I]` 必須先取得更多資訊才能往下走

把所有不一致當成 `[A]` 處理會讓人類煩躁(很多其實不需要他們裁決),把所有都當成 `[D]` 處理會讓真衝突被埋沒。**正確的分類本身就是這個 skill 的核心價值**。
