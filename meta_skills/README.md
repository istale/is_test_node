# Meta-Skills for Enterprise Agent Collaboration

## 設計理念

這是一組為 OpenClaw Agent 設計的元技能(meta-skills)套件,目的是讓 Agent 在企業場景中能:

1. 主動偵測自己「不知道什麼」(epistemic gap detection)
2. 把模糊的不一致變成具體可回答的問題(question crystallization)
3. 在資訊不全時做出有 calibration 的判斷(confidence-aware decision)
4. 把每次互動蒸餾成可重用的知識(skill distillation)

這套 skill 不是 domain knowledge,而是**處理 domain knowledge 的方法**。它們的價值不在於替 Agent 做決定,而在於**把人類腦中 implicit knowledge 逼出來變成 explicit**。

## Skill 清單

### 第一組:基礎元技能(5 個)

| Skill | 核心功能 | 主要對抗的 LLM 失效模式 |
|-------|---------|----------------------|
| `bridge-failure-listing` | 跨來源缺口偵測 | 強行腦補對應關係 |
| `assumption-surfacing` | 隱性假設挖掘 | 把預設當共識 |
| `source-authority-tagging` | 來源權威標註 | 把推測偽裝成事實 |
| `inversion` | 反向風險偵測 | 樂觀偏誤 |
| `reversibility-triage` | 可逆性分流 | 過度自主或過度提問 |

### 第二組:規格審查專用(3 個)

| Skill | 核心功能 | 主要對抗的 LLM 失效模式 |
|-------|---------|----------------------|
| `numerical-consistency-audit` | 規格數字稽核 | 取平均、取保守值的虛假妥協 |
| `quantitative-provenance-tracking` | 數字溯源追蹤 | 對來源不明的數字照單全收 |
| `boundary-condition-probing` | 邊界條件試探 | 只關注典型值,忽略邊界 |

## 使用哲學

這套 skill 的設計原則:

1. **顯式優於隱式**:每個 skill 都強迫把腦補的步驟外化成可審查的輸出
2. **缺口優於答案**:回報「無法對應」比給出「合理化的對應」更有價值
3. **觸發優於常駐**:這些 skill 不是預設流程,要在特定條件下被調用
4. **組合優於單用**:多個 skill 串成管線使用,效果遠大於單獨使用

## 重要限制

這套 skill **不能**讓 Agent 變成「主動參與者」,只能讓 Agent 變成「謹慎的審查者」。它解決的是「該問什麼」,不解決「該不該問」、「該怎麼判斷」、「該如何承擔責任」。

當你發現 Agent 跑完所有 skill 後產出 50 個問題,這就是 skill 用過頭的訊號 — 真正的工藝是讓 Agent 排序出最有價值的 3 個問題,而不是窮盡所有可能的問題。

## 檔案結構

```
meta_skills/
├── README.md                              (本檔)
├── ORCHESTRATION.md                       (觸發條件與組合規則)
├── bridge-failure-listing/SKILL.md
├── assumption-surfacing/SKILL.md
├── source-authority-tagging/SKILL.md
├── inversion/SKILL.md
├── reversibility-triage/SKILL.md
├── numerical-consistency-audit/SKILL.md
├── quantitative-provenance-tracking/SKILL.md
└── boundary-condition-probing/SKILL.md
```
