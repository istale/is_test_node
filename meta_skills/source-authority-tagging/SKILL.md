# Source Authority Tagging

## Purpose

對每條資訊建立「權威溯源」,以便:
1. 遇到衝突時知道該信誰、該問誰
2. 防止 Agent 把推測偽裝成事實
3. 為跨 Agent 協作提供可審查的信任基礎

## When to Use

- 整合多份內部文件(版本、來源、權威度可能不一)
- 客服 / 支援場景(SOP vs 主管最新指示衝突時)
- 跨部門規則衝突排解
- 長期 conversation 中區分「使用者明說的」vs「Agent 推測的」
- 寫入 LLM wiki 之前(每條 entry 都要有來源層級)
- Agent 之間協作時,作為信任傳遞鏈的錨點

## When NOT to Use

- 公開知識的單純查詢(來源都是公開知識,標註多此一舉)
- 一次性、低風險的對話(過度標註會讓回應變繁瑣)

## Procedure

### Step 1 — 來源類型標註

對每條資訊標註來源類型:

- `[Official]` 公司正式文件、SOP、規範
- `[Authority]` 特定角色的口述或郵件(老闆、PM、Tech Lead)
- `[Consensus]` 同事之間口頭流傳但無正式記錄
- `[Inference]` Agent 自己根據 pattern 推測的
- `[Public]` 網路、教科書、通用知識
- `[History]` 過往對話、過往決策紀錄
- `[Wiki-Stable]` 已被人類確認的 wiki 條目
- `[Wiki-Draft]` Agent 寫入但尚未人類確認的 wiki 條目

### Step 2 — 多維度評估

對每條資訊評估:

- **權威等級**(1-5,5 最高)
- **時效性**:`永久` / `季度` / `隨時可能變`
- **變更頻率**:`穩定` / `中等` / `高頻`
- **裁決者**:衝突時誰可以拍板(具體角色或人名)

### Step 3 — 衝突偵測

列出所有「不同來源對同一件事說法不一」的情況:

```yaml
- 衝突主題: <topic>
  source_a: { type, content, authority_level }
  source_b: { type, content, authority_level }
  recommended_arbiter: <role>
  interim_strategy: <what to do before resolution>
```

### Step 4 — 提問路由表

未來遇到不同類型問題時,該問誰?輸出對照表:

```yaml
question_routing:
  - topic_pattern: <e.g. "業務規則 / 折扣">
    primary_contact: <role>
    fallback_contact: <role>
    escalation_path: <role>
```

## Strict Prohibitions

- 不要把 `[Inference]` 偽裝成 `[Official]`
- 不要因為某條資訊「聽起來合理」就升級它的權威等級
- 不要把過時的 `[History]` 當成現行有效規則
- 不要在沒有明確 arbiter 時隨意指定一個(寧可標 `[需要先確認誰能裁決]`)
- 不要混用「我從哪聽到這個」(來源)和「這個有多權威」(權威等級) — 兩者必須分開標註

## Output Format

```yaml
source_audit:
  tagged_facts:
    - fact: <statement>
      source_type: <Official | Authority | Consensus | Inference | Public | History | Wiki-Stable | Wiki-Draft>
      authority_level: <1-5>
      volatility: <stable | medium | high>
      arbiter: <role>
      last_confirmed: <timestamp or "unknown">

  detected_conflicts:
    - topic: <text>
      conflicting_sources: [...]
      recommended_arbiter: <role>
      interim_strategy: <text>

  routing_table:
    - pattern: <topic pattern>
      primary: <role>
      fallback: <role>
```

## Composition Hints

- 此 skill 應**先於**多數其他 skill 執行,作為知識基底
- 與 `bridge-failure-listing` 配合:跨文件衝突常涉及來源權威差異
- 與 `numerical-consistency-audit` 配合:數字衝突的裁決需要先知道誰能裁決
- 寫入 wiki 前必須執行此 skill,確保每條 entry 帶來源標註

## 對 LLM Wiki 場景的特別重要性

當 Agent 之間透過 wiki 協作時,wiki 條目的「來源層級」是防止 collusive hallucination 的核心機制。每條條目必須清楚標明:

- 是 Human 確認的還是 Agent 推測的
- 是哪個 Human、什麼時候確認的
- 引用時 Agent 必須帶上這些標註,不能脫光只剩內容

沒有這層標註,wiki 會變成「腦補的儲存櫃」,讓推測取得文件化的虛假權威。
