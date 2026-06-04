# Assumption Surfacing

## Purpose

挖掘文件作者「沒寫但默認成立」的隱性假設,把它們轉成具體可回答的問題。特別針對「設計者不知道自己漏寫了什麼」這個痛點。

## When to Use

- 審查規格 / 設計 / 計劃文件
- 程式碼 review,挖掘隱性 contract
- 商業計劃 / 提案審查
- 法律文件 / 合約審查
- 跨文化、跨團隊合作前的對齊
- **特別場景**:你需要請設計者「補齊」文件,但連設計者自己都不知道該補什麼

## When NOT to Use

- 文件本身就是 brainstorming / 探索性質(假設本來就還沒形成)
- 對方明確要求快速決策,沒時間挖掘
- 假設挖掘的結果無法影響任何決策(純學術練習)

## Procedure

### Step 1 — 顯性主張盤點

列出文件中所有明確的主張、規則、決策。每條標記為:
- 規則性主張(「必須 X」)
- 描述性主張(「系統會 X」)
- 預期性主張(「使用者會 X」)
- 邊界性主張(「不超過 X」)

### Step 2 — 假設挖掘

對每條主張,逐一追問:

- **前提類**:這條主張要成立,需要什麼前提?(物理 / 技術 / 人為 / 環境)
- **不證自明類**:作者預設了哪些「不證自明」但其實有爭議的事?
- **自動發生類**:作者預設了哪些「會自動發生」但需要設計才會發生的事?
- **角色類**:作者預設了「誰」會做什麼,但沒明說?
- **邊界類**:作者預設了使用情境的邊界(規模、頻率、用戶類型),但沒寫?
- **時間類**:作者預設了某些事「永遠」或「從不」發生,但其實會變?

### Step 3 — 假設分級

對每個挖出的假設標記嚴重度:

- `[Critical]` — 假設不成立,整個方案崩潰
- `[Risky]` — 假設不成立,需要重大修改
- `[Minor]` — 假設不成立,有 workaround

### Step 4 — 提問轉化

針對 `[Critical]` 和 `[Risky]` 假設,把它們轉成具體問題。問題格式必須:

- 不是抽象的「請確認 X」,而是具體的「假設 X 在 Y 情境下不成立,該怎麼處理?」
- 標出該問誰(具體角色,不是「相關單位」)
- 帶上「不答的後果」,讓被問的人有回答動機

## Strict Prohibitions

- 不要只列文件「寫了什麼」(那是摘要,不是假設挖掘)
- 不要把假設寫得太抽象(「假設使用者會用得對」太空泛)
  - 反例:「假設使用者會用得對」
  - 正例:「假設使用者會在每次操作前讀說明書」
- 不要替作者腦補理由為什麼這個假設「應該」成立
- 不要因為某個假設「常識上應該成立」就跳過 — 常識在企業情境下常常不成立

## Output Format

```yaml
assumption_audit:
  document: <doc_name>

  explicit_claims:
    - claim: <text>
      type: <rule | description | expectation | boundary>

  hidden_assumptions:
    - assumption: <specific statement>
      severity: <Critical | Risky | Minor>
      what_breaks_if_false: <consequence>
      who_to_ask: <specific role>
      generated_question: <concrete question>
      cost_of_not_answering: <what happens if ignored>

  meta_observation:
    - <pattern noticed across multiple assumptions>
```

## Composition Hints

- 與 `bridge-failure-listing` 配合:跨文件的 unbridged 概念,通常背後是隱性假設
- 與 `inversion` 配合:Critical 假設的「失敗劇本」可用 inversion 進一步展開
- 與 `boundary-condition-probing` 配合:邊界類假設可用 boundary probing 系統性挖掘

## 為什麼這個 skill 對「規格補齊」場景特別關鍵

設計者通常無法主動「補齊」文件,因為他不知道自己漏了什麼 — 那些對他而言「理所當然」的事,在他腦中根本不是「資訊」,而是「背景」。

這個 skill 的價值是把背景變成前景。它不是要設計者「補完規格」,而是先把**設計者腦中認為理所當然但沒寫下的假設**逼出來,變成具體問題。設計者看到「[Critical] 你假設了 B 部門會在 5 秒內回應,但這沒寫在哪 — 確認一下?」會立刻反應,比「請補齊規格」有效百倍。
