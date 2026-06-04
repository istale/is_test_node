# Reversibility Triage

## Purpose

對待決策的問題分類「該快做 vs 該慢做、該自動 vs 該問人」。是 Agent 在企業場景中**不過度自主、也不過度提問**的核心判準。

## When to Use

- agent 自動化任務的 guardrail
- 大量資料操作前的判斷(刪除、批次更新)
- 對外溝通前的審核(發郵件、發訊息、發布內容)
- 預算 / 採購決策
- Code 變更(commit 到 main vs feature branch)
- 任何「Agent 該不該自己做」的情境

## When NOT to Use

- 純粹的資訊查詢(沒有「決策」可言)
- 已經有明確 SOP 規定的場景(直接照 SOP 走就好)

## Procedure

### Step 1 — 可逆性評估

對每個決策評估:

- `[Fully reversible]` — 完全可逆(成本接近 0,5 分鐘可還原)
- `[Costly reversible]` — 可逆但有成本(時間 / 金錢 / 信任)
- `[Partially reversible]` — 部分可逆(可改但留下副作用)
- `[Irreversible]` — 實質不可逆(法律、對外承諾、資料刪除、公開言論)

### Step 2 — 影響範圍評估

- `[Self]` 只影響 Agent 自己 / 單一使用者
- `[Team]` 影響團隊 / 部門
- `[Cross-org]` 影響跨部門 / 對外
- `[Critical]` 影響法律 / 財務 / 安全

### Step 3 — 分流規則

根據可逆性 × 影響範圍交叉決定行動:

| 可逆性 / 影響 | Self | Team | Cross-org | Critical |
|--------------|------|------|-----------|----------|
| Fully reversible | 自動執行 | 自動執行+通知 | 自動執行+通知 | 必須先問 |
| Costly reversible | 自動執行+通知 | 提案+確認 | 提案+確認 | 必須先問 |
| Partially reversible | 提案+確認 | 必須先問 | 必須先問 | 必須先問 |
| Irreversible | 必須先問 | 必須先問 | 必須先問 | 必須先問 |

### Step 4 — 提問品質檢查

對需要詢問的項目,確保問題符合:

- **包含完整脈絡** — 不要「要繼續嗎?」這種空問
- **列出選項及各自後果**
- **標註預設選項及不選的代價**
- **標註這個決策一旦做出,還能不能撤回**
- **標註所需資訊已提供 / 還缺什麼**

### Step 5 — 最終產出

每個決策輸出一行決議:

```yaml
- decision: <text>
  action: <auto | auto_with_notice | propose | ask>
  reasoning: <why this action>
  if_ask: <full question with context, options, consequences>
```

## Strict Prohibitions

- 不要把不可逆決策當成可逆決策處理
- 不要為了「展現自主性」而執行該問的事
- 不要為了「展現謙虛」而問該自己決定的小事
- 「可以全部問人」不是好策略,過度提問跟過度自主一樣糟
- 不要省略 reasoning — 不寫清楚為什麼這個級別,人類無法快速 audit

## Output Format

```yaml
triage_audit:
  decisions:
    - id: <D1, D2, ...>
      decision_topic: <text>
      reversibility: <Fully | Costly | Partially | Irreversible>
      impact_scope: <Self | Team | Cross-org | Critical>
      action: <auto | auto_with_notice | propose | ask>
      reasoning: <one-line why>

  questions_to_ask:
    - decision_id: <ref>
      context: <full background>
      options:
        - option: <choice A>
          consequence: <outcome>
          reversibility_after: <can it be undone>
        - option: <choice B>
          consequence: <outcome>
          reversibility_after: <can it be undone>
      default_if_no_response: <action>
      cost_of_delay: <what happens if not answered>

  auto_actions_log:
    - decision_id: <ref>
      action_taken: <text>
      notification_to: <role>
```

## Composition Hints

- 此 skill 通常作為其他 skill 的**收尾步驟** — 跑完 bridge-failure / assumption-surfacing / inversion 之後,用 reversibility-triage 把所有發現分流成「Agent 自己處理 vs 必須問人類」
- 與 `inversion` 配合特別有效:Inversion 找出的高風險失敗模式,對應的決策往往是不可逆的,需要從 ask 路徑走
- 在多 Agent 協作場景中,此 skill 也是「Agent 之間能達成什麼協議 vs 必須拉人類進來」的判準

## 為什麼這個 skill 是「主動參與者」幻覺的真正解藥

我前面論證過 Agent 不可能變成真正的主動參與者,因為它缺判斷力和責任承擔能力。Reversibility Triage 是在這個現實下的最佳折衷:

**Agent 不需要有完美判斷力,只需要知道「什麼決策可以自己做、什麼決策必須問人」**。這個分類能力比真正的判斷力低階,但足以讓 Agent 在大多數場景表現得像個有判斷力的協作者。

關鍵是 triage 結果必須準確 — 把不可逆決策誤判成可逆是災難,把可逆決策過度提問是噪音。這個準確度本身要靠人類反饋持續校準,本質上是個 calibration 問題。
