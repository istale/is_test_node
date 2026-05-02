# Multi-Repo Integration Research Prompt (v2)

## 任務

我要研究多個 GitHub 專案，目標是理解它們的架構、功能邊界、可融合性，並產出可執行的 integration plan。

請使用 graphify 輔助研究，必要時啟動多個代理平行協作。**所有結論必須引用具體檔案、模組、或 graphify 查詢結果作為證據。**

---

## 輸入

**專案清單：**
- Repo A:   https://github.com/open-webui/open-webui
- Repo B:   https://github.com/anomalyco/opencode

**研究目標（請填具體，不要抽象）：**
```
要整合/移植/比較的功能: 左邊欄樹狀結構資料檢視及選擇, 中間欄資料內容檢視及資料分析圖表, 右邊欄對話視窗讓使用者跟AI Agent協作分析資料
預期最終使用者體驗：使用者可以以不同的分組方式檢視資料樹狀結構或者是由AI Agent跟使用者協作檢視選擇分析標的, AI agent可以執行資料分析後顯示圖表於中間欄，使用者可以多輪對話得到各種不同分析方式(ex. 不同grouping方式統計分析或繪製圖表)的結果, 結果會以卡片形式持續保留在畫面中(最新的結果置頂)
明確 out-of-scope：需後續討論，列為checking list
可接受的功能折衷：需後續討論，列為checking list
```

**限制條件：**
- 主要目標專案（融合終點）：目前傾向Open webui
- 必須保留的架構/技術棧：從企業提供的OSS角度以python pip, nodejs npm為可長期維護的option
- 不可改動的部分：none
- **輸出語言**：雙語
- **預期輸出**：研究報告與 integration plan。**不要直接修改程式碼，除非我明確要求。**

---

## 工作流程

### Phase 0：Preflight（fail-fast，不要硬撐）

在做任何分析前先驗證環境。任何一項失敗就**立即停下並回報**，不要降級偷跑。

1. `graphify --version` 能執行
2. 每個 repo 能成功 `git clone`
3. 每個 repo 能讀到 README、主要 build/package config
4. 每個 repo 能跑通 `graphify <repo-path>` 的第一步（不需跑完）
5. license 檢查：列出每個 repo 的 license，標記任何 GPL/AGPL/proprietary 帶來的整合限制

**Phase 0 通過條件**：以上 5 項全綠。回報一份 preflight summary 後再進 Phase 1。

如果某項失敗：先說明失敗原因 → 提出兩種替代方案（例如：graphify 失敗 → 改用純 source-level analysis）→ **等我確認再繼續**。

---

### Phase 1：各 repo 獨立建圖與摘要

**規則：先分開做，不要混。**

對每個 repo 分別：

1. 執行 `graphify <repo-path>`
2. 讀 `graphify-out/GRAPH_REPORT.md`
3. 必要時用 CLI 補充查詢：
   ```
   graphify query "<question>" --graph <repo-path>/graphify-out/graph.json
   graphify explain "<concept>" --graph <repo-path>/graphify-out/graph.json
   graphify path "<A>" "<B>" --graph <repo-path>/graphify-out/graph.json
   ```

每個 repo 寫一份獨立摘要（寫入 `<workspace>/notes/repo-<name>-summary.md`），包含：

- 核心模組（附檔案路徑）
- 主要資料流（從 entrypoint 到 persistence）
- API / CLI / UI entrypoints
- persistence layer（DB、schema location、migration tool）
- auth / session model
- background jobs / async workflow
- external dependencies（重要的第三方服務或 binary）
- 測試策略（test framework、coverage 大致範圍、CI 設定）
- 高耦合區域（**判定標準：fan-in 或 fan-out > 10 的模組，或單檔超過 500 行且被 5 個以上模組引用**）
- 可移植功能邊界（**判定標準：一個功能子集，其外部依賴可以列舉清楚，且不直接觸及不可改動清單上的模組**）

**單份 repo 摘要長度上限：1500 字。** 超過代表你寫太多細節，留到後續被需要時再展開。

---

### Phase 2：Early-Exit Checkpoint

完成 Phase 1 所有 repo 摘要後，**先停下來**做一次 deal-breaker 檢查：

回答以下問題，任一個答「是」就停下來提交 Interim Report，等我決定是否繼續：

1. license 之間是否存在不相容（例如目標 repo 是 MIT，來源是 AGPL）？
2. auth/session model 是否根本性不相容（例如一邊強制 SSO + 多租戶，另一邊單機 session）？
3. 主要技術棧是否衝突到無法 adapter 化（例如 runtime/語言不同且功能重度依賴 runtime API）？
4. 不可改動清單上的模組，是否被目標功能的依賴鏈直接觸及？
5. 任何一個 repo 的關鍵模組沒有測試覆蓋，且程式碼複雜度高到 reverse-engineer 成本超過重寫？

Interim Report 格式：「發現 P0 風險 X，原因 Y，證據 Z（檔案路徑或 graphify 查詢），建議：[繼續但調整目標 / 改變融合策略 / 放棄融合]」。

沒有 P0 風險 → 進 Phase 3。

---

### Phase 3：Multi-Agent 平行研究（條件觸發）

**觸發條件**（任一成立才啟動 multi-agent，否則主代理單線跑）：
- repo 數 ≥ 2 且每個 repo 主要模組數 ≥ 5，**或**
- 目標功能依賴鏈跨越 ≥ 3 個子系統，**或**
- 預估單線分析會超過 context budget

**Agent IO 規範（強制）：**
- 每個 agent 寫入獨立檔案：`<workspace>/notes/agent-<N>-<topic>.md`
- 每份 agent report 上限 2000 字
- Agent 之間**不直接通訊**；共享只透過 `<workspace>/notes/` 下的檔案
- 主代理最後 `read all notes/` 再 synthesize

**建議分工：**
- Agent 1：Repo A 架構與目標功能依賴分析
- Agent 2：Repo B 架構、extension points、整合風險
- Agent 3：跨 repo 對照（domain concepts、API boundary、資料模型）
- Agent 4：測試 / build / dependency / deployment 風險

**每個 agent 必須回報：**
- 讀過的檔案清單（路徑）
- 執行過的 graphify 查詢（指令 + 摘要結果）
- 主要發現（≤ 5 點）
- 不確定處（明列）
- 對 integration plan 的具體建議
- 需要主代理確認的風險

**主代理 synthesize 衝突處理規則：**
- 兩個 agent 對同一事實有不同說法 → 標記為 conflict，列出兩邊證據，由主代理用 graphify 或 source 驗證
- 任何「無法驗證」的發現 → 移到 Open Questions，不要寫進主結論

---

### Phase 4：Cross-Repo Graph Merge（條件觸發）

**觸發條件**：Phase 3 跨 repo 對照中出現 **≥ 5 個** cross-repo concept candidates（語意相近但命名不同的概念對）。少於 5 個直接跳過 merge，省 context。

```
graphify merge-graphs \
  <repo-a>/graphify-out/graph.json \
  <repo-b>/graphify-out/graph.json \
  --out <workspace>/merged-graphify/graph.json
```

合併後針對融合目標查詢，建議問題：
- "<Repo A 功能 X> 依賴哪些核心模組、資料模型與外部服務？"
- "<Repo B> 中最適合承接 <功能 X> 的 extension point 是哪裡？"
- "兩個 repo 在 auth/session/persistence/API model 上有哪些不相容？"
- "哪些概念在兩個 repo 中語意相近但命名不同？"
- "如果把 <功能 X> 移植到 <Repo B>，最小改動路徑是什麼？"
- "哪些部分可直接移植 / 需要 adapter / 必須重寫？"

---

### Phase 5：最終報告

#### 報告長度與必要性規則

| 段落 | 必填 | 上限 | 沒發現時 |
|---|---|---|---|
| A. Executive summary | ✅ | 400 字 | 不可省略 |
| B. Repo-by-repo architecture summary | ✅ | 每 repo 600 字 | 不可省略 |
| C. Target feature dependency map | ✅ | 800 字 | 不可省略 |
| D. Cross-repo compatibility analysis | ✅ | 1000 字 | 寫「無重大不相容」+ 證據 |
| E. Integration options | ✅ | 每方案 400 字 | 不可省略 |
| F. Recommended plan | ✅ | 1000 字 | 不可省略 |
| G. Open questions | 條件 | 500 字 | 沒有就省略此段 |

**C 與 D 的明確區分（不要重疊）：**
- **C = 單 repo 視角**：目標功能在「來源 repo」內部需要什麼（entrypoints、依賴模組、config、data models）
- **D = diff 視角**：把 C 的內容對到目標 repo 時，兩邊的差異與不相容（domain model 對照、API、auth、schema、runtime）

---

#### A. Executive summary
- 是否建議融合：Yes / No / Conditional
- 推薦策略（擇一）：移植 / 重寫 / adapter / library extraction / 不建議
- 最大 1-2 個風險與一句話原因

#### B. Repo-by-repo architecture summary
每個 repo 涵蓋：架構、核心模組、資料流、測試、部署。**每個論點附檔案路徑或 graphify 查詢。**

#### C. Target feature dependency map（單 repo 視角）
- 目標功能的 entrypoints
- 依賴的 modules / services / models / config
- 需要搬移或重建的部分
- 可以忽略的部分（與融合目標無關的）

#### D. Cross-repo compatibility analysis（diff 視角）
- domain model 對照表（A 的概念 ↔ B 的概念，差異）
- API boundary 對照
- auth / session 相容性
- persistence / schema 相容性
- dependency / runtime 相容性
- UI/UX 或 CLI workflow 相容性

#### E. Integration options（≥ 2，建議 3）
- **方案 1**：最小改動（短期可交付）
- **方案 2**：中期可維護
- **方案 3**：長期最佳架構

每個方案包含：
- 做法（一段話）
- 優點 / 缺點 / 風險
- 預估工作量（人日量級即可）
- 測試需求
- **不應該先做的事**（綁在方案下，不獨立列）

#### F. Recommended plan
- 選定的方案 + 理由
- 分階段 implementation plan，每階段：完成條件、需要的 spike/prototype、要新增/修改的測試
- 階段之間的 checkpoint（什麼情況下要回頭調整方案）

#### G. Open questions
仍需人工決策或產品判斷的問題（不要寫進主結論）。

---

## 硬性規則（違反就重做）

1. **不要只依賴 README**。必須讀 source、tests、config，並用 graphify 報告或 graph 查詢輔助。
2. **不要在沒有 integration plan 前修改程式碼。**
3. **不要把多個 repo 一開始混成一包分析。** 先分開建圖，再做跨 repo 對照。
4. **所有架構判斷必須引用具體檔案、模組或 graphify 查詢結果。** 沒有證據的論點移到 Open Questions。
5. **graphify 失敗時**：回報失敗原因，提出降級方案（source-level analysis），等我確認後再繼續，不要靜默切換。
6. **遇到 P0 deal-breaker**（Phase 2 checkpoint 列出的 5 種）：立即停下，提交 Interim Report，等我決定。
7. **報告語言**：依照「輸入」裡指定的語言，從頭到尾一致。
8. **不確定的事情**寫進 Open Questions，不要寫成肯定句。