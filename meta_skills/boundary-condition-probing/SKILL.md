# Boundary Condition Probing

## Purpose

對每個規格數字,生成邊界探測問題,逼文件作者面對沒想過的情境。攻擊「典型值寫了但邊界行為沒寫」這個常見大坑。

## When to Use

- API 規格 review
- 限制條款審查(rate limit、quota、timeout)
- 安全閾值設定(失敗多少次鎖定?鎖多久?)
- 業務規則設計(滿多少免運?多少天可退貨?)
- 演算法 spec(收斂條件、終止條件)
- 系統整合前的 contract 確認

## When NOT to Use

- 純粹的描述性文件(沒有邊界行為的概念)
- 高層次的策略文件(邊界討論為時尚早)

## Procedure

### Step 1 — 邊界生成

對每個規格數字 X(例:`超時時間 = 30 秒`),產生以下探測問題:

- **[剛好邊界]** 如果剛好 = X,算成功還是失敗?(`<X` / `≤X` 的差別)
- **[剛好超過]** `X + 最小單位` 時的行為?
- **[極小值]** 0 或負數時的行為?
- **[極大值]** 上限是多少?超過會怎樣?
- **[累積邊界]** 重複多次的累積效應?(單次 X、做 100 次呢?)
- **[並發邊界]** 多個並發實體都在 X 附近時?
- **[時間漂移]** X 隨時間變化嗎?(系統運行 30 天後還是 X 嗎?)
- **[單位精度]** X 的精度是多少?(`30 秒` vs `30.0 秒` vs `30.000 秒`)
- **[失效行為]** 系統無法達到 X 時的 fallback 是什麼?
- **[初始狀態]** 系統剛啟動時 X 是什麼值?
- **[終止狀態]** 系統關閉前 X 怎麼處理?

### Step 2 — 文件覆蓋度檢查

對每個探測問題,檢查文件是否有明確答案:

- ✓ 有明確答案
- ⚠ 有暗示但不明確
- ✗ 完全沒提

### Step 3 — 跨文件邊界一致性

對涉及同一數字的多份文件,額外檢查:

- 兩份文件對同一邊界行為的描述是否一致?
- 不一致的話,套用 `numerical-consistency-audit` 的分類框架

### Step 4 — 提問生成

對 ✗ 的項目,生成具體提問:

- 不是「請定義邊界行為」這種空泛要求
- 而是「當輸入為 X+1 時,系統應該回 200 還是 400?」這種具體選擇題
- 帶上「為什麼問這個」 — 解釋這個邊界在實作時必踩

### Step 5 — Critical Flag

特別 flag 以下情況:

- 兩份文件對同一邊界行為的描述若有差異 → `[Critical]`
- 文件只寫「典型值」沒寫「邊界行為」是常見大坑 → 至少 `[High]`
- 失效行為(fallback)沒寫是 `[Critical]` — 永遠不要假設「應該很合理」

## Strict Prohibitions

- 不要替作者腦補「應該是 X 的話就...」 — 邊界腦補錯誤的代價極高
- 不要因為「常識上應該這樣」就跳過提問 — 不同人對「常識」理解不同
- 邊界問題往往看起來「沒必要問」,但實作時必踩坑,寧可問
- 不要把 ⚠ 歸為 ✓ — 暗示不算明確,實作者會用自己的猜測填補
- 不要只問「典型邊界」,要強迫自己想「**極端但合法的輸入**」

## Output Format

```yaml
boundary_audit:
  spec_number: <name + value>

  probes:
    - probe_type: <剛好邊界 | 剛好超過 | 極小值 | 極大值 | 累積邊界 | 並發邊界 | 時間漂移 | 單位精度 | 失效行為 | 初始狀態 | 終止狀態>
      question: <specific scenario>
      doc_coverage: <✓ | ⚠ | ✗>
      severity_if_unspecified: <Critical | High | Medium | Low>

  generated_questions:
    - question: <specific question, not abstract>
      why_it_matters: <impl-time consequence>
      who_to_ask: <role>
      proposed_default: <if no answer, what should the system do>

  cross_doc_inconsistencies:
    - boundary: <which boundary>
      doc_a_says: <text>
      doc_b_says: <text>
      severity: <Critical | High>
```

## Composition Hints

- 與 `numerical-consistency-audit` 配合:典型值不一致時,邊界值通常更不一致
- 與 `inversion` 配合:邊界失敗常是 inversion 的子類,可從邊界生成失敗劇本
- 與 `assumption-surfacing` 配合:邊界行為沒寫,通常是因為作者預設了某些「不會發生」的情境

## 為什麼這個 skill 是「實作會 vs 不會踩雷」的關鍵分水嶺

在規格審查時,典型值的不一致很容易被發現,因為它們是「文件主角」。但邊界行為通常是「文件配角」 — 設計者寫文件時聚焦在「**正常情況下系統怎麼運作**」,而不是「**異常情況下系統怎麼處理**」。

實作者拿到這份文件,典型情況都能照著做。但他寫到第 100 行時遇到第一個邊界,文件沒寫,他就憑感覺寫一個。第二個實作者寫到同樣邊界,憑感覺寫了不同的處理。**Bug 就這樣誕生**,而且很難追根溯源,因為文件本身沒錯,是文件**沒寫**的部分出問題。

Boundary probing 的價值是把「文件沒寫的角落」系統性地挖出來,在實作前就給設計者面對的機會。這比實作後才發現問題便宜十倍。
