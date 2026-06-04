# Inversion

## Purpose

從失敗反推風險,而非從成功推估可行性。對抗樂觀偏誤,挖掘原方案沒有對應防禦的高風險失敗模式。

## When to Use

- 系統架構 review(特別是上線前)
- 跨團隊依賴的計劃審查
- 對賭性質的決策(投資、合作、技術選型)
- agent 自動化流程設計(自動化失敗的代價往往很大)
- 不可逆操作的事前檢查
- 規格文件的 stress test

## When NOT to Use

- 純探索性質的 brainstorm(過早 inversion 會殺死創意)
- 已經失敗的事後檢討(用其他 root cause analysis 工具更合適)
- 非常低風險的小改動(成本不對稱,inversion 過度)

## Procedure

### Step 1 — 失敗情境生成

假設這個方案在執行 X 個月後**徹底失敗**。從以下角度各生成至少 3 個失敗劇本:

- **技術失敗**:系統壞了、性能不達標、整合失敗
- **人為失敗**:使用者誤用、操作者離職、訓練不足
- **流程失敗**:審批卡關、依賴方延遲、優先級被搶走
- **外部失敗**:法規變更、供應商倒閉、市場變化
- **隱性失敗**:看似運作正常但其實沒產生價值

### Step 2 — 逆向追查

對每個失敗劇本逐一追查:

- 失敗的最早徵兆會是什麼?
- 哪個決策埋下了這個失敗的種子?
- 在原方案中,有沒有 mitigation?如果有,夠不夠?
- 如果沒有,需要加什麼?

### Step 3 — 失敗模式分級

按發生機率 × 影響程度建立四象限:

- `[High × High]` 必須在方案中加入防禦
- `[High × Low]` 接受但設監控
- `[Low × High]` 設 contingency plan
- `[Low × Low]` 記錄但不處理

### Step 4 — 缺失防禦清單

列出原方案「沒有對應防禦」的高風險失敗模式,提出補強建議。

## Strict Prohibitions

- 不要只列「常見風險」(資安、人員流動之類的範本式風險),要針對這個具體方案
- 不要把失敗劇本寫得太抽象 — 要具體到「**誰**在**什麼情境**下**做了什麼**導致 X」
- 不要因為失敗劇本「不太可能」就跳過評估,可能性低不代表不用想
- 不要只挑容易想到的失敗模式,刻意往「沒人想過的失敗」推
- 不要在分析未完成前提出修復方案 — 先把失敗看清楚,再談怎麼防

## Output Format

```yaml
inversion_audit:
  scenarios:
    - id: <S1, S2, ...>
      category: <technical | human | process | external | hidden>
      failure_story: <specific narrative>
      earliest_symptom: <observable signal>
      seed_decision: <which decision planted this seed>
      existing_mitigation: <if any, and whether sufficient>
      likelihood: <low | medium | high>
      impact: <low | medium | high>
      quadrant: <HH | HL | LH | LL>

  defensive_gaps:
    - failure_mode: <which scenarios share this gap>
      missing_defense: <what's not in the plan>
      proposed_addition: <concrete change>
      cost_estimate: <effort to add this defense>

  meta_pattern:
    - <recurring theme across multiple scenarios, e.g. "多個失敗都源自單點依賴 X">
```

## Composition Hints

- 與 `assumption-surfacing` 配合:Critical 假設的失敗劇本可用 inversion 展開
- 與 `reversibility-triage` 配合:不可逆決策必須先跑 inversion
- 與 `boundary-condition-probing` 配合:邊界失敗常是 inversion 的子類

## 為什麼這個 skill 特別有效

人類在規劃時有強烈的樂觀偏誤,會自動聚焦在「這個怎麼成功」。Inversion 強迫切換到「這個怎麼失敗」,而失敗模式往往比成功路徑更具體、更可分析、更能暴露盲點。

Charlie Munger 有句名言對應這個技巧:「告訴我我會死在哪裡,我就不會去那裡。」企業場景的應用是:**告訴我這個方案會怎麼崩,我就知道該補強哪裡**。
