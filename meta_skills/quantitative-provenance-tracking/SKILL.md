# Quantitative Provenance Tracking

## Purpose

對每個規格數字追蹤它的來源層級,判斷這個數字是「決策」、「推導」、「測量」還是「猜的」。是 `numerical-consistency-audit` 的搭檔 skill。

## When to Use

- 系統容量規劃文件審查
- 性能 SLA 制定 / 修改
- 合規數字的合理性檢查(為什麼是 90 天而不是 60 天?)
- 老系統重構前的規格考古
- 對外承諾數字的回溯驗證
- 與 `numerical-consistency-audit` 配合使用

## When NOT to Use

- 數字本身是即時測量值(provenance 很明顯,不需要追蹤)
- 純粹的計算結果(如報表加總)

## Procedure

### Step 1 — 來源類型標註

對每個數字標記其來源類型:

- `[Decided]` 由特定角色拍板決定(誰、何時、為什麼選這個值)
- `[Derived]` 從其他數字 / 規則推導而來(推導鏈是什麼)
- `[Measured]` 來自實測 / benchmark(測試條件、測試環境)
- `[Inherited]` 從外部標準 / 上游文件繼承(出處)
- `[Convention]` 行業慣例 / 預設值(沒人特別決定,習慣這樣寫)
- `[Unknown]` 文件沒交代來源

### Step 2 — 推導鏈展開

對 `[Derived]` 數字,顯式畫出推導鏈:

```
每秒查詢上限 100
  ← 單機 RPS 25 × 4 台機器
    ← 單機 RPS 25(來自 benchmark)
    ← 機器數 4(來自 [Decided] by Tech Lead, 2024-Q3)
  ← 預估流量峰值 80
    ← 歷史峰值 60 × 季節係數 1.33
  ← buffer 1.25
    ← [Convention]: 25% 安全係數
```

### Step 3 — Unknown 提問

對 `[Unknown]` 數字,生成提問:

- 這個數字的決策依據是什麼?
- 它依賴於哪些其他假設?
- 它是什麼時候決定的?後來條件變了嗎?
- 誰是最後簽字的人?

### Step 4 — 衝突診斷(配合 numerical-consistency-audit)

當兩份文件對同一數字有不同值時,根據 provenance 類型診斷:

- 兩份都是 `[Decided]` 但值不同 → `[A. 真衝突]`,必須由原決策者裁決
- 兩份都是 `[Derived]` 但值不同 → 推導鏈可能不同,要對齊推導前提
- 一份 `[Decided]` vs 另一份 `[Inherited]` → 可能是上游變了沒同步,優先確認上游現況
- 兩份都是 `[Convention]` 但值不同 → 通常無人能裁決,需要正式決策流程
- 一份 `[Decided]` vs 另一份 `[Convention]` → 通常 `[Decided]` 勝,但要確認決策還有效
- 兩份都是 `[Unknown]` → 雙方都需要先補 provenance 才能談一致性

### Step 5 — Provenance 健康度報告

對整份文件的 provenance 整體狀態評估:

- `[Unknown]` 數字佔比(越高越危險)
- `[Convention]` 數字是否有人 review 過
- `[Derived]` 推導鏈是否完整
- `[Decided]` 數字的決策時間是否過時

## Strict Prohibitions

- 不要把 `[Convention]` 偽裝成 `[Decided]`(沒人決定不代表不能改)
- 不要把 `[Unknown]` 跳過 — 沒交代來源的數字最危險
- 不要在 `[Derived]` 推導鏈不完整時硬補,要 flag 出來
- 不要把「我不知道誰決定的」當成 `[Convention]`,那是 `[Unknown]`
- 不要假設 `[Decided]` 還有效 — 要檢查決策時間和當時前提

## Output Format

```yaml
provenance_audit:
  numbers:
    - number: <value with unit>
      refers_to: <object.attribute>
      provenance_type: <Decided | Derived | Measured | Inherited | Convention | Unknown>
      details:
        # for Decided
        decided_by: <role + name>
        decided_when: <timestamp>
        decision_reasoning: <why this value>
        # for Derived
        derivation_chain: <visual chain>
        upstream_dependencies: [...]
        # for Measured
        test_conditions: <text>
        test_environment: <text>
        # for Inherited
        upstream_source: <doc/standard>
        # for Convention
        convention_origin: <industry/team>
        # for Unknown
        questions_to_ask: [...]

  health_report:
    unknown_ratio: <percentage>
    stale_decisions: [<numbers with old decision dates>]
    incomplete_derivations: [...]
    convention_review_needed: [...]

  conflict_diagnostics:
    - topic: <text>
      type_a: <provenance type from doc A>
      type_b: <provenance type from doc B>
      diagnosis: <which conflict pattern>
      recommended_action: <text>
```

## Composition Hints

- 與 `numerical-consistency-audit` 是核心搭檔 — 一個負責找不一致,一個負責診斷不一致的根源
- 與 `source-authority-tagging` 配合:`[Decided]` 數字的權威來源就是該決策角色
- 對 `[Unknown]` 數字,套用 `assumption-surfacing` 挖掘背後可能的隱性假設

## 一個常見的「規格考古」場景

在維護老系統時,你常會遇到「為什麼這裡寫 30」這種問題。沒人記得了,文件沒寫,但這個數字深深嵌在系統裡。

Provenance tracking 的價值不只是「找到答案」,而是**把這種無法回答的數字 flag 出來**,讓組織知道「這是個風險點 — 我們依賴一個沒人記得為什麼的值」。光是把這類數字列出來,就足以推動下次 review 時補上 provenance。

如果 Agent 在多年運作中持續累積 provenance 資料,組織等於有了一份**活的決策史**。這比任何靜態文件都有價值。
