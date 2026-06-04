# Skill Orchestration:觸發條件與組合規則

這份文件規範這 8 個 meta-skill 如何被觸發、如何組合、如何避免過度使用。

## 核心原則

### 原則 1:Skill 是工具不是流程

這些 skill **不應該**作為預設的審查流程跑在每次任務上。它們是「在特定觸發條件下被選擇性調用的工具」。預設跑全套會產生大量低價值噪音。

### 原則 2:Question Budget 強制執行

無論觸發了多少 skill,Agent 最終呈現給人類的問題清單**不得超過 5 個**(除非任務性質特別需要,例如正式合約審查)。Skill 跑完後必須有一個排序步驟,把問題按「value of information」排序,只呈現最高價值的幾個。

### 原則 3:Negative Output 也是 Output

如果跑完 skill 沒發現問題,Agent 應該明確報告「跑了 X skill,沒發現 Y 類問題」,而不是沉默。沉默會讓使用者誤以為 skill 沒跑。

### 原則 4:Composition over Single Use

單獨用一個 skill 通常價值有限。組合使用才是這套系統真正的力量。下面定義幾個常用組合管線。

---

## Skill 觸發矩陣

| 觸發情境 | 應觸發的 skill | 不該觸發的 skill |
|---------|--------------|---------------|
| 收到 1 份新文件 | assumption-surfacing | bridge-failure(沒對象比) |
| 收到 2+ 份相關文件 | bridge-failure-listing → assumption-surfacing | inversion(過早) |
| 規格文件審查 | 完整管線 P1(見下) | reversibility-triage(這是審查不是執行) |
| Agent 即將執行操作 | reversibility-triage | source-authority-tagging(過晚) |
| 整合多個 API / 工具 | bridge-failure-listing + numerical-consistency-audit | inversion(看情況) |
| 系統架構 review | inversion + assumption-surfacing | numerical-consistency-audit(看情況) |
| 寫入 LLM wiki 之前 | source-authority-tagging | 其他都看情況 |
| Agent 之間協作協商 | source-authority-tagging + reversibility-triage | numerical-consistency-audit(除非涉及數字) |
| 規格數字對齊 | 完整管線 P2(見下) | 其他 |
| 簡單問答 / 查詢 | 都不觸發 | 全部 |

---

## 組合管線定義

### 管線 P1:規格文件全面審查

**觸發條件**:正式的規格 / 設計文件需要請設計者補齊或審查

**步驟**:

```
Step 1: source-authority-tagging
  → 標清楚每段內容的權威等級
  → 識別誰是這份文件的真正 owner

Step 2: bridge-failure-listing(若有相關文件)
  → 跟既有文件對照,找出無法整合的缺口

Step 3: assumption-surfacing
  → 挖出設計者沒寫的隱性假設
  → 這是「補齊」場景的核心步驟

Step 4: inversion
  → 從失敗反推,找出方案的脆弱點

Step 5: reversibility-triage
  → 把所有發現分流:
    - Agent 可以自己決定的
    - Agent 提案、人類確認的
    - 必須由設計者親自回答的

Step 6: 排序與精煉
  → 套用 question budget,只保留最高價值的 3-5 個問題
  → 每個問題附帶「為什麼問」與「不答的後果」
```

**輸出**:一份「設計者問題清單」,每題都帶完整脈絡和不答的後果。

**典型耗時**:Agent 處理 15-30 分鐘,人類消化 5-10 分鐘。

### 管線 P2:規格數字對齊

**觸發條件**:多份文件涉及同樣的規格數字,需要確認一致性

**步驟**:

```
Step 1: numerical-consistency-audit
  → 找出表面的數字不一致,並分類

Step 2: quantitative-provenance-tracking
  → 對有問題的數字追溯來源
  → 此時 Agent 已能區分:
    - 哪些是真衝突(必須讓決策者裁決)
    - 哪些是時序差(確認版本即可)
    - 哪些是單位/條件差(文件要補註解)
    - 哪些是來源不明(需要原作者交代)

Step 3: boundary-condition-probing
  → 進一步逼出文件沒寫的邊界行為

Step 4: source-authority-tagging
  → 對每個衝突項,確認該由誰裁決

Step 5: 產出三類提問清單
  1. [Critical 衝突] 必須由 X 角色裁決,在裁決前 Agent 暫採 Y 值
  2. [來源不明] 需要 Z 補充決策依據
  3. [邊界缺漏] 規格需要補上 W 情境的明確行為
```

**輸出**:結構化的數字一致性報告,每個不一致都帶分類和處理路徑。

### 管線 P3:Agent 自主決策前的 guardrail

**觸發條件**:Agent 即將執行任何操作(寫入、發送、修改、刪除)

**步驟**:

```
Step 1: reversibility-triage(必跑)
  → 評估這個操作是否可逆、影響範圍多大

Step 2: 若分流為「auto」→ 直接執行,記錄 audit log
Step 3: 若分流為「auto_with_notice」→ 執行並通知
Step 4: 若分流為「propose」→ 提出方案,等待確認
Step 5: 若分流為「ask」→
   套用 inversion 確認是否有沒考慮到的失敗模式
   套用 source-authority-tagging 確認問誰
   產出包含完整脈絡的提問
```

**輸出**:行動或提問,而不是「兩者皆有」的混亂狀態。

### 管線 P4:多 Agent 協作前的對齊

**觸發條件**:Agent A 即將跟 Agent B 協作完成跨人類任務

**步驟**:

```
Step 1: source-authority-tagging
  → 雙方先標清楚各自的資訊權威來源

Step 2: bridge-failure-listing
  → 雙方對概念進行對齊,顯式列出無法 bridge 的點

Step 3: 對 unbridged 項目,各自回頭問自己的人類
   → 不要 Agent 之間直接腦補出共識

Step 4: 拿到答案後,寫入 wiki(若有 LLM wiki 系統)
   → 標註為 [Wiki-Stable] 或 [Wiki-Draft] 視確認程度

Step 5: 進入實際協作
   → 過程中遇到新衝突,再次觸發 bridge-failure-listing
```

**輸出**:雙方 Agent 對齊的概念基底 + 各自待人類確認的問題清單。

---

## 反模式:不該怎麼用

### 反模式 1:把所有 skill 當預設流程

**症狀**:每次任務都跑完 8 個 skill,產出 50 個問題給使用者。

**為什麼錯**:
- 高頻任務會讓使用者瘋掉
- 大量低價值問題稀釋真正重要的問題
- Skill 失去「特定觸發」的價值,變成噪音來源

**正確做法**:依任務性質選擇 1-3 個最相關的 skill,不要全套上。

### 反模式 2:用 skill 替代判斷

**症狀**:Agent 跑完 skill 後說「我列出了所有問題,請使用者回答」,把判斷責任全推回去。

**為什麼錯**:
- 使用者本來找 Agent 是要減輕負擔,結果負擔變重
- Agent 沒有展現任何判斷力,變成純粹的 checklist 跑機器
- 違反「Agent 是放大人類判斷力,不是替代或推卸」的設計哲學

**正確做法**:Agent 跑完 skill 後,要先**自己**對結果排序、過濾、判斷,只把真正需要人類介入的呈現出來。

### 反模式 3:讓 skill 成為儀式

**症狀**:每次都跑同樣的管線,但結論千篇一律。

**為什麼錯**:
- Skill 變成形式,失去 epistemic 價值
- 使用者開始忽略 skill 的輸出
- 真正的問題反而被儀式化的「已審查」標籤掩蓋

**正確做法**:跑 skill 時必須有具體的「我在尋找什麼」,而不是機械式跑完所有步驟。如果 skill 沒產生新洞察,如實報告「沒發現問題」,而不是強行擠出問題湊數。

### 反模式 4:Skill 跑完不蒸餾

**症狀**:每次任務都從零開始跑 skill,沒有把上次的發現累積成 domain knowledge。

**為什麼錯**:
- Agent 永遠是新人,domain intuition 不會累積
- 同樣的問題被重複問
- 違反「skill 的價值是壓縮成複利知識」的核心原則

**正確做法**:每次 skill 跑出的高價值發現(特別是人類確認後的答案),必須蒸餾成 wiki 條目或新的 skill rule,讓下次類似情境可以直接套用。配合 OpenClaw skillstack 的 `build-review-learn-loop` 與 `leverage-point-extractor`。

---

## 進階:Skill 之間的依賴關係

```
                source-authority-tagging
                    │
                    │ (provides authority context)
                    ▼
   ┌──────── bridge-failure-listing ─────────┐
   │                │                         │
   │                │ (unbridged → unknown)   │
   │                ▼                         │
   │      assumption-surfacing                │
   │                │                         │
   │                │ (assumptions → fail modes) 
   │                ▼                         │
   │           inversion                      │
   │                │                         │
   │                │ (numbers in scope)      │
   │                ▼                         │
   ├── numerical-consistency-audit ◄──────────┤
   │       │                                  │
   │       ▼                                  │
   │   quantitative-provenance-tracking       │
   │       │                                  │
   │       ▼                                  │
   │   boundary-condition-probing             │
   │                │                         │
   │                ▼                         │
   └─────► reversibility-triage ◄─────────────┘
                    │
                    ▼
            (action or question)
```

實線箭頭:典型的 skill 觸發順序
虛線箭頭:資訊流向

關鍵觀察:
- `source-authority-tagging` 通常**先**跑,作為知識基底
- `reversibility-triage` 通常**最後**跑,作為行動分流
- 中間的 skill 順序視任務而定

---

## 與 LLM Wiki 系統的整合

如果你的環境有 LLM wiki 系統,這 8 個 skill 應該:

### Skill 寫入 wiki 時

每個 skill 的輸出可以選擇性寫入 wiki,但必須:

1. 套用 `source-authority-tagging`,標註來源層級
2. 標註信心度(已驗證 / 推測)
3. 標註時效性與衰減函數
4. 寫入 `[Wiki-Draft]` 區,等人類確認後才升級到 `[Wiki-Stable]`

### Skill 讀取 wiki 時

每個 skill 在分析時可以參考 wiki,但必須:

1. 區分 `[Wiki-Stable]` 與 `[Wiki-Draft]` 的引用權重
2. 對 `[Wiki-Draft]` 的引用要降級信心度
3. 對「Agent 之間 wiki 達成的共識但未經人類確認」的條目特別警覺(防止 collusive hallucination)

### Skill 觸發 wiki 維護

當 skill 在運作時發現以下情況,應觸發 wiki 維護:

- 發現過時的 wiki 條目 → flag 給人類 review
- 發現衝突的 wiki 條目 → 列入裁決清單
- 發現使用率為零的 wiki 條目 → 建議審查是否還需要

這就是讓 wiki「腐爛速率 < 更新速率」的核心機制 — Agent 主動引導人類維護,而不是讓人類主動巡邏。

---

## 實踐建議

1. **從 P3 開始**:Reversibility Triage 是最容易看到價值的 skill,先把這個用順
2. **再加 P1 用於規格場景**:這是大多數企業最痛的場景,效益明顯
3. **P2 看是否有大量數字密集的文件**:如果是規格密集型行業(金融、醫療、合規),P2 必跑;否則可選
4. **P4 等到真的開始多 Agent 協作再啟用**:單 Agent 階段先別碰
5. **Question Budget 寧緊勿鬆**:寧可一開始限制 3 個問題,不夠再放寬;不要一開始 10 個然後使用者已經放棄
6. **追蹤指標**:每週看「Agent 提的問題,人類回答率是多少」、「人類覺得有用的問題佔比」 — 這些指標會告訴你 skill 用得對不對
