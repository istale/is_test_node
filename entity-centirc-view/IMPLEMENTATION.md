# 實作文件 — Entity-centric Faceted Knowledge View

> **本文件讀者：27B Code Agent。**
> 所有架構決策已鎖定，**不要再做選型**。照本文件的檔案結構、型別、函式簽章與驗收標準實作即可。
> 遇到本文件未規定的細節，選「最簡單、最少依賴、最接近既有範例」的做法，不要自行擴張範圍。

---

## 0. 一頁總覽

- **唯一真實來源**：**llm-wiki 的 markdown 檔案**（`*.md`，YAML frontmatter + `[[wikilinks]]`，git 管理、由 LLM ingest/query/lint 維護）。
- **`knowledge.json` 是編譯產物（compiled index / build artifact）**，由 `parseWiki()` 從 markdown 轉出，**唯讀、不可手改**（手改會在重建時被覆蓋）。
- **三個投影**（全部從編譯後的 `knowledge.json` 產生）：
  - 給人類 → `3-column view`（左 facets / 中 entity / 右 details），可看可編輯。
  - 給模型讀 → `Agent Card`（Markdown / YAML，名字已 resolve、1-hop 自足；llm-wiki page 本身已是八成成品）。
  - 給模型寫 → `Agent Import`（JSON + schema 驗證，進 staging 不直接落地）。
- **人類在 UI 的編輯 → 決定性程式同步回 markdown**（`commandToMarkdownEdit`），**不經 LLM**。詳見 §7.5。
- **React Flow / ELK 只是 view layer**，永遠不是真實來源。
- **語言全程 TypeScript**（前後端共用同一份 zod schema，減少不一致）。

資料流：
```
llm-wiki/*.md  ──parseWiki()──▶  knowledge.json (編譯索引)
   │ (唯一真實來源)                  │
   │                                ├─to3ColumnView()─▶ ColumnView ─viewToReactFlow()─▶ React Flow (人類看/編輯)
   │                                ├─buildAgentCard()─▶ Markdown / YAML  (模型讀)
   │                                └─（搜尋 / facet filter / lint 視覺化）
   ▲
   │  決定性回寫（無 LLM）
   └── 人類編輯 ─KnowledgeCommand─▶ diffKnowledge/commandToMarkdownEdit ─▶ 改 *.md ─▶ 重建 knowledge.json

模型寫：Agent JSON ─parseAgentImport()─▶ planImport (dryRun) ─核可─▶ mergeImport ─▶ 改 *.md
LLM 的角色只剩：① ingest 新原始資料寫成 markdown　② 散文層 stale 內容的「建議」（人審）
```

---

## 1. 鎖定的技術決策（不可更改）

| 項目 | 決策 | 理由 |
|---|---|---|
| 語言 | TypeScript（前後端皆是） | 共用 schema/型別 |
| Monorepo | npm workspaces（不要 pnpm/yarn/turbo） | 零額外工具 |
| 共用套件 | `packages/core`（schema + 全部轉譯函式，無 IO、無 React） | 純函式好測 |
| 驗證 | `zod` | schema = 型別 = runtime 驗證 |
| **真實來源** | **llm-wiki markdown 目錄**（`data/wiki/*.md`）；`knowledge.json` 為重建索引 | 相容 llm-wiki ingest/query/lint、git-friendly |
| 後端 | `express` + TypeScript，檔案儲存：讀 markdown、寫 markdown（透過 Repository 介面） | 原型階段，之後可換 DB |
| markdown 解析 | `gray-matter`（拆 frontmatter）+ `yaml`（Document API 就地編輯，保留註解/格式） | 決定性回寫，diff 乾淨 |
| 前端 | `vite` + `react` + `@xyflow/react`（React Flow v12）+ `elkjs` + `zustand` | 鎖定版本見 §10 |
| YAML | npm `yaml` 套件 | 模型讀 + frontmatter 就地編輯 |
| 測試 | `vitest` | 跑在 core 與 backend |

**Phase 1 不需要 ELK 也能完整運作**（單一 entity 聚焦的 3 欄視圖用固定座標）。ELK 只在 Phase 2 的「多 entity 關係視圖」才介入。先把 Phase 1 做到綠燈再碰 ELK。

---

## 2. Monorepo 結構

```
entity-centric-view/
├── package.json                 # workspaces: ["packages/*", "apps/*"]
├── tsconfig.base.json
├── packages/
│   └── core/                    # 純函式：schema + 轉譯（無 IO / 無 React）
│       ├── package.json         # name: "@ecv/core"
│       ├── src/
│       │   ├── schema.ts        # zod canonical schema + 型別
│       │   ├── selectors.ts     # derive 用（如相關 entity 清單）
│       │   ├── view.ts          # to3ColumnView
│       │   ├── reactflow.ts     # viewToReactFlow / applyElkLayoutToReactFlow
│       │   ├── elk.ts           # buildElkGraph（Phase 2）
│       │   ├── agent.ts         # buildAgentCard / parseAgentImport / mergeImport
│       │   ├── commands.ts      # KnowledgeCommand union + applyKnowledgeCommand
│       │   ├── sample.ts        # 範例 canonical 資料（entity_a / entity_b）
│       │   └── index.ts         # re-export
│       └── test/*.test.ts
├── apps/
│   ├── server/                  # express API
│   │   ├── package.json         # name: "@ecv/server"
│   │   ├── src/
│   │   │   ├── repo.ts          # KnowledgeRepository 介面 + JsonFileRepository
│   │   │   ├── routes.entities.ts
│   │   │   ├── routes.relations.ts
│   │   │   ├── routes.views.ts
│   │   │   ├── routes.agent.ts
│   │   │   └── server.ts        # 組裝 + listen
│   │   └── data/
│   │       ├── knowledge.json   # 真實來源（啟動時若不存在用 sample 寫入）
│   │       └── views/*.json     # view state
│   └── web/                     # vite react app
│       ├── package.json         # name: "@ecv/web"
│       ├── index.html
│       ├── vite.config.ts       # proxy /api -> localhost:8787
│       └── src/
│           ├── main.tsx
│           ├── api.ts           # fetch wrapper（型別來自 @ecv/core）
│           ├── store.ts         # zustand：canonical + view state + 命令派發
│           ├── App.tsx
│           ├── components/
│           │   ├── EntityCanvas.tsx     # React Flow 畫布
│           │   ├── nodes/*.tsx          # 各 node 元件
│           │   ├── Inspector.tsx        # 右側編輯面板（表單）
│           │   ├── SearchBar.tsx
│           │   └── FacetFilter.tsx
│           └── layout/elkLayout.ts      # 呼叫 elkjs（Phase 2，可用 web worker）
└── README.md
```

---

## 3. Canonical Schema（`packages/core/src/schema.ts`）

完整照抄。型別由 zod `infer` 出來,前後端共用。

```ts
import { z } from "zod";

export const FacetColumn = z.enum(["left", "right"]); // 目前只用 left

export const FacetDef = z.object({
  key: z.string(),                 // "category"
  label: z.string(),               // "分類"
  column: FacetColumn.default("left"),
  multi: z.boolean().default(true),
});

export const RelationType = z.object({
  predicate: z.string(),           // "related_to"
  label: z.string(),               // "相關於"
  directed: z.boolean().default(false),
  inverseLabel: z.string().optional(), // 有向時用，如 "被需要於"
});

export const Evidence = z.object({
  id: z.string(),
  source: z.string(),              // "docs/source-a.md" 或 chunk id
  quote: z.string(),
  confidence: z.number().min(0).max(1).optional(),
});

export const Report = z.object({
  id: z.string(),
  title: z.string(),
  source: z.string(),              // "reports/a1.md"
  entityIds: z.array(z.string()).default([]),
});

export const Entity = z.object({
  id: z.string(),
  name: z.string(),
  type: z.string(),                // "system" / "person" / ...
  summary: z.string().default(""), // 一句話：欄位標題 + 模型 grounding
  description: z.string().default(""),
  facets: z.record(z.string(), z.array(z.string())).default({}),
  reportIds: z.array(z.string()).default([]),
  evidenceIds: z.array(z.string()).default([]),
  updatedAt: z.string().default(() => new Date().toISOString()),
});

export const Relation = z.object({
  id: z.string(),
  subject: z.string(),             // entity id
  predicate: z.string(),           // 對應 RelationType.predicate
  object: z.string(),              // entity id
  evidenceIds: z.array(z.string()).default([]),
  confidence: z.number().min(0).max(1).optional(),
  updatedAt: z.string().default(() => new Date().toISOString()),
});

export const Knowledge = z.object({
  schemaVersion: z.literal("1.0"),
  facetDefs: z.array(FacetDef),
  relationTypes: z.array(RelationType),
  entities: z.array(Entity),
  relations: z.array(Relation),
  reports: z.array(Report),
  evidence: z.array(Evidence),
});

export type TFacetDef = z.infer<typeof FacetDef>;
export type TRelationType = z.infer<typeof RelationType>;
export type TEvidence = z.infer<typeof Evidence>;
export type TReport = z.infer<typeof Report>;
export type TEntity = z.infer<typeof Entity>;
export type TRelation = z.infer<typeof Relation>;
export type TKnowledge = z.infer<typeof Knowledge>;
```

**不變量（implementer 必須維持）**
1. `relations` 是 entity↔entity 關係的唯一來源。**不得**在 entity 內另存相關清單。
2. `reportIds` / `evidenceIds` / `relation.evidenceIds` 一律是參照,實體存在 top-level collection。
3. 任何寫入後 `updatedAt` 更新；PATCH 用 `updatedAt` 做樂觀鎖（不符就回 409）。
4. `entity.id`、`relation.id` 全域唯一。

---

## 4. Selectors（`packages/core/src/selectors.ts`）

derive 出 view/agent 需要的東西,**不改 canonical**。

```ts
import type { TKnowledge, TEntity, TRelation } from "./schema";

export const entityById = (k: TKnowledge, id: string) =>
  k.entities.find(e => e.id === id);

export const reportById = (k: TKnowledge, id: string) =>
  k.reports.find(r => r.id === id);

export const evidenceById = (k: TKnowledge, id: string) =>
  k.evidence.find(e => e.id === id);

export const relationLabel = (k: TKnowledge, predicate: string) =>
  k.relationTypes.find(t => t.predicate === predicate)?.label ?? predicate;

export interface RelatedItem {
  relationId: string;
  entity: TEntity;          // 已 resolve 的對方 entity
  predicate: string;
  predicateLabel: string;
  direction: "out" | "in";  // 相對 focus entity
  confidence?: number;
  evidenceIds: string[];
}

/** 取得某 entity 的 1-hop 鄰居（含進出兩個方向），已 resolve 成 entity 物件。 */
export function relatedEntities(k: TKnowledge, entityId: string): RelatedItem[] {
  const items: RelatedItem[] = [];
  for (const r of k.relations) {
    if (r.subject === entityId) {
      const e = entityById(k, r.object);
      if (e) items.push(mk(k, r, e, "out"));
    } else if (r.object === entityId) {
      const e = entityById(k, r.subject);
      if (e) items.push(mk(k, r, e, "in"));
    }
  }
  return items;
}

function mk(k: TKnowledge, r: TRelation, e: TEntity, direction: "out" | "in"): RelatedItem {
  return {
    relationId: r.id, entity: e, predicate: r.predicate,
    predicateLabel: relationLabel(k, r.predicate),
    direction, confidence: r.confidence, evidenceIds: r.evidenceIds,
  };
}
```

---

## 5. 投影 A：3 欄視圖（`packages/core/src/view.ts`）

這是**人類視圖與編輯的共同資料結構**。HTML 表單和 React Flow 都從它生成。

```ts
import type { TKnowledge, TEntity, TReport, TEvidence } from "./schema";
import { entityById, reportById, evidenceById, relatedEntities, RelatedItem } from "./selectors";

export interface FacetBlock { key: string; label: string; values: string[]; }
export interface ColumnView {
  focusEntity: TEntity;
  left: FacetBlock[];                 // facets（依 facetDefs 順序）
  center: { id: string; name: string; type: string; summary: string };
  right: {
    description: string;
    related: RelatedItem[];           // 已 resolve；超過 threshold 時 UI collapse
    reports: TReport[];
    evidence: TEvidence[];
  };
}

export interface ViewOptions { collapseRelatedOver?: number; } // 預設 8

export function to3ColumnView(
  k: TKnowledge, focusEntityId: string, _opt: ViewOptions = {}
): ColumnView {
  const e = entityById(k, focusEntityId);
  if (!e) throw new Error(`entity not found: ${focusEntityId}`);

  const left: FacetBlock[] = k.facetDefs
    .filter(d => d.column === "left")
    .map(d => ({ key: d.key, label: d.label, values: e.facets[d.key] ?? [] }))
    .filter(b => b.values.length > 0);

  return {
    focusEntity: e,
    left,
    center: { id: e.id, name: e.name, type: e.type, summary: e.summary },
    right: {
      description: e.description,
      related: relatedEntities(k, e.id),
      reports: e.reportIds.map(id => reportById(k, id)).filter(Boolean) as TReport[],
      evidence: e.evidenceIds.map(id => evidenceById(k, id)).filter(Boolean) as TEvidence[],
    },
  };
}
```

### 5.1 ColumnView → React Flow（`packages/core/src/reactflow.ts`，Phase 1 用固定座標）

單一 entity 聚焦時**不需要 ELK**：左欄堆 facets、右欄堆 details、中間放 entity。

```ts
import type { Node, Edge } from "@xyflow/react";
import type { ColumnView } from "./view";

const COL_X = { left: 0, center: 360, right: 720 };
const ROW_GAP = 90;
const NODE_W = 260, NODE_H = 60;

export function viewToReactFlow(view: ColumnView): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // center
  const centerId = `entity:${view.center.id}`;
  nodes.push({
    id: centerId, type: "entityNode",
    position: { x: COL_X.center, y: 300 },
    data: { entityId: view.center.id, label: view.center.name, type: view.center.type, summary: view.center.summary },
  });

  // left: facets
  view.left.forEach((f, i) => {
    const id = `facet:${view.center.id}:${f.key}`;
    nodes.push({
      id, type: "facetNode",
      position: { x: COL_X.left, y: 120 + i * ROW_GAP },
      data: { entityId: view.center.id, facetKey: f.key, label: f.label, values: f.values },
    });
    edges.push({ id: `e:${id}`, source: id, target: centerId,
      sourceHandle: "right", targetHandle: "left", type: "facetEdge" });
  });

  // right: description / related(list) / reports / evidence
  let row = 0;
  const pushRight = (id: string, type: string, data: any, edgeType: string) => {
    nodes.push({ id, type, position: { x: COL_X.right, y: 80 + row++ * ROW_GAP }, data });
    edges.push({ id: `e:${id}`, source: centerId, target: id,
      sourceHandle: "right", targetHandle: "left", type: edgeType });
  };

  if (view.right.description)
    pushRight(`detail:${view.center.id}:desc`, "detailNode",
      { label: "description", text: view.right.description }, "detailEdge");

  if (view.right.related.length)
    pushRight(`related:${view.center.id}`, "relatedEntityListNode",
      { entityId: view.center.id, items: view.right.related }, "collapsedRelationEdge");

  view.right.reports.forEach(r =>
    pushRight(`report:${r.id}`, "reportNode", { label: r.title, source: r.source }, "reportEdge"));

  view.right.evidence.forEach(ev =>
    pushRight(`evidence:${ev.id}`, "evidenceNode",
      { quote: ev.quote, source: ev.source, confidence: ev.confidence }, "evidenceEdge"));

  return { nodes, edges };
}
```

> **註**：node 寬高 `NODE_W/NODE_H` 給 ELK Phase 2 用；Phase 1 固定座標即可，使用者拖曳的位置存進 view state（§7.2），不回寫 canonical。

---

## 6. 投影 B：給模型讀（`packages/core/src/agent.ts`）

### 6.1 `buildAgentCard` — 模型讀（Markdown 主、YAML 選）

```ts
import { stringify as toYaml } from "yaml";
import type { TKnowledge } from "./schema";
import { entityById, reportById, evidenceById, relatedEntities } from "./selectors";

export interface AgentCardOptions {
  maxDepth?: 1 | 2;          // 預設 1
  includeReports?: boolean;  // 預設 true
  includeEvidence?: boolean; // 預設 true
  includeTriples?: boolean;  // 預設 true
  outputFormat?: "markdown" | "yaml"; // 預設 "markdown"
  quoteMaxLen?: number;      // 預設 200
}

export function buildAgentCard(k: TKnowledge, entityId: string, opt: AgentCardOptions = {}): string {
  const o = { maxDepth: 1, includeReports: true, includeEvidence: true,
              includeTriples: true, outputFormat: "markdown", quoteMaxLen: 200, ...opt } as Required<AgentCardOptions>;
  const e = entityById(k, entityId);
  if (!e) throw new Error(`entity not found: ${entityId}`);
  const rel = relatedEntities(k, entityId);
  const clip = (s: string) => s.length > o.quoteMaxLen ? s.slice(0, o.quoteMaxLen) + "…" : s;

  if (o.outputFormat === "yaml") {
    return toYaml({
      entity: { id: e.id, name: e.name, type: e.type, summary: e.summary },
      facets: e.facets,
      related: rel.map(r => ({ name: r.entity.name, relation: r.predicateLabel,
        confidence: r.confidence, evidence: r.evidenceIds })),
      ...(o.includeReports && { reports: e.reportIds.map(id => reportById(k, id)).filter(Boolean)
        .map(r => ({ title: r!.title, source: r!.source })) }),
      ...(o.includeEvidence && { evidence: e.evidenceIds.map(id => evidenceById(k, id)).filter(Boolean)
        .map(ev => ({ quote: clip(ev!.quote), source: ev!.source, confidence: ev!.confidence })) }),
      ...(o.includeTriples && { triples: rel.map(r => ({
        s: e.name, p: r.predicateLabel, o: r.entity.name, confidence: r.confidence })) }),
    });
  }

  // markdown
  const L: string[] = [];
  L.push(`# ${e.name}  ·  type: ${e.type}`);
  if (e.summary) L.push(e.summary);
  const facetLines = Object.entries(e.facets).filter(([, v]) => v.length);
  if (facetLines.length) { L.push(`\n## 分面`); facetLines.forEach(([key, v]) => {
    const label = k.facetDefs.find(d => d.key === key)?.label ?? key; L.push(`- ${label}: ${v.join("、")}`); }); }
  if (rel.length) { L.push(`\n## 相關實體 (1-hop)`); rel.forEach(r => {
    const ev = r.evidenceIds.map(id => evidenceById(k, id)?.quote).filter(Boolean)[0];
    L.push(`- ${r.entity.name} — 關係: ${r.predicateLabel}` +
      (r.confidence != null ? ` · 信心 ${r.confidence}` : "") + (ev ? ` · 依據: "${clip(ev)}"` : "")); }); }
  if (o.includeReports && e.reportIds.length) { L.push(`\n## 報告`);
    e.reportIds.forEach(id => { const r = reportById(k, id); if (r) L.push(`- ${r.title} → ${r.source}`); }); }
  if (o.includeEvidence && e.evidenceIds.length) { L.push(`\n## 證據`);
    e.evidenceIds.forEach(id => { const ev = evidenceById(k, id);
      if (ev) L.push(`- "${clip(ev.quote)}" — ${ev.source}` + (ev.confidence != null ? ` (信心 ${ev.confidence})` : "")); }); }

  // maxDepth=2：附上每個鄰居的精簡卡（只到 facets，避免爆 context）
  if (o.maxDepth === 2 && rel.length) {
    L.push(`\n---`);
    rel.forEach(r => L.push(buildAgentCard(k, r.entity.id, { ...o, maxDepth: 1, includeTriples: false })));
  }
  return L.join("\n");
}
```

**為什麼這樣寫給 27B/30B 模型讀**：對方名字已 resolve（不必 id-chasing）、predicate 用中文 label、1-hop 自足、Markdown heading 當結構、quote 截斷避免爆 context。**不得**輸出任何 UI-only 欄位（position/zoom/handle/bend）。

### 6.2 `parseAgentImport` / `mergeImport` — 模型寫（JSON + 驗證 + staging）

模型**寫**回來一律 JSON（好驗證、好修）。先驗 schema,再進 staging,不直接落地。

```ts
import { z } from "zod";
import { Entity, Relation, Knowledge, TKnowledge } from "./schema";

export const AgentImport = z.object({
  entities: z.array(Entity).default([]),
  relations: z.array(Relation).default([]),
});
export type TAgentImport = z.infer<typeof AgentImport>;

export interface ImportPlan {
  ok: boolean;
  errors: string[];
  newEntities: string[];      // 將新增的 entity id
  updatedEntities: string[];  // 將更新的 entity id
  newRelations: string[];
  conflicts: string[];        // id 衝突或 dangling 參照
}

/** 驗證並產生 dry-run 計畫。不改 knowledge。 */
export function planImport(k: TKnowledge, raw: unknown): ImportPlan {
  const parsed = AgentImport.safeParse(raw);
  if (!parsed.success) return { ok: false, errors: parsed.error.issues.map(i => i.message),
    newEntities: [], updatedEntities: [], newRelations: [], conflicts: [] };
  const imp = parsed.data;
  const existing = new Set(k.entities.map(e => e.id));
  const plan: ImportPlan = { ok: true, errors: [], newEntities: [], updatedEntities: [],
    newRelations: [], conflicts: [] };
  for (const e of imp.entities) (existing.has(e.id) ? plan.updatedEntities : plan.newEntities).push(e.id);
  const allEntityIds = new Set([...existing, ...imp.entities.map(e => e.id)]);
  for (const r of imp.relations) {
    if (!allEntityIds.has(r.subject) || !allEntityIds.has(r.object))
      plan.conflicts.push(`relation ${r.id} 參照不存在的 entity`);
    else plan.newRelations.push(r.id);
  }
  plan.ok = plan.conflicts.length === 0;
  return plan;
}

/** 套用 import（建議在使用者/規則核可 plan 後才呼叫）。回傳新 knowledge。 */
export function mergeImport(k: TKnowledge, imp: TAgentImport): TKnowledge {
  const entities = [...k.entities];
  for (const e of imp.entities) {
    const i = entities.findIndex(x => x.id === e.id);
    if (i >= 0) entities[i] = { ...entities[i], ...e, updatedAt: new Date().toISOString() };
    else entities.push(e);
  }
  const relations = [...k.relations];
  for (const r of imp.relations) if (!relations.some(x => x.id === r.id)) relations.push(r);
  return Knowledge.parse({ ...k, entities, relations });
}
```

> **Open Q7 的答案已鎖定**：agent import **可以**新增 entity,但**必須**先過 `planImport` 並由 API 回傳計畫,核可後才 `mergeImport`。預設 API 行為見 §8。

---

## 7. 編輯：Typed Knowledge Commands（`packages/core/src/commands.ts`）

**RF→canonical 的唯一語意入口**。前端任何「編輯知識」的動作都派發 command;React Flow 的 onChange（拖曳/選取/縮放）**只進 view state,絕不產生 command**。

```ts
import { Knowledge, TKnowledge, TEntity, TRelation } from "./schema";

export type KnowledgeCommand =
  | { type: "CreateEntity"; entity: TEntity }
  | { type: "RenameEntity"; id: string; name: string }
  | { type: "UpdateEntityType"; id: string; entityType: string }
  | { type: "UpdateSummary"; id: string; summary: string }
  | { type: "UpdateDescription"; id: string; description: string }
  | { type: "SetFacet"; id: string; key: string; values: string[] }
  | { type: "RemoveFacet"; id: string; key: string }
  | { type: "AddRelation"; relation: TRelation }
  | { type: "RemoveRelation"; relationId: string }
  | { type: "AddReportLink"; entityId: string; reportId: string }
  | { type: "RemoveReportLink"; entityId: string; reportId: string }
  | { type: "AddEvidenceLink"; entityId: string; evidenceId: string }
  | { type: "RemoveEvidenceLink"; entityId: string; evidenceId: string };

const now = () => new Date().toISOString();
const touch = (e: TEntity): TEntity => ({ ...e, updatedAt: now() });

/** 純函式 reducer：回傳新的 knowledge，不 mutate。未知 command 直接丟錯。 */
export function applyKnowledgeCommand(k: TKnowledge, cmd: KnowledgeCommand): TKnowledge {
  const ents = () => [...k.entities];
  const mapEnt = (id: string, fn: (e: TEntity) => TEntity): TEntity[] =>
    k.entities.map(e => e.id === id ? touch(fn(e)) : e);

  switch (cmd.type) {
    case "CreateEntity":        return next({ entities: [...k.entities, cmd.entity] });
    case "RenameEntity":        return next({ entities: mapEnt(cmd.id, e => ({ ...e, name: cmd.name })) });
    case "UpdateEntityType":    return next({ entities: mapEnt(cmd.id, e => ({ ...e, type: cmd.entityType })) });
    case "UpdateSummary":       return next({ entities: mapEnt(cmd.id, e => ({ ...e, summary: cmd.summary })) });
    case "UpdateDescription":   return next({ entities: mapEnt(cmd.id, e => ({ ...e, description: cmd.description })) });
    case "SetFacet":            return next({ entities: mapEnt(cmd.id, e => ({ ...e, facets: { ...e.facets, [cmd.key]: cmd.values } })) });
    case "RemoveFacet":         return next({ entities: mapEnt(cmd.id, e => { const f = { ...e.facets }; delete f[cmd.key]; return { ...e, facets: f }; }) });
    case "AddRelation":         return next({ relations: [...k.relations, cmd.relation] });
    case "RemoveRelation":      return next({ relations: k.relations.filter(r => r.id !== cmd.relationId) });
    case "AddReportLink":       return next({ entities: mapEnt(cmd.entityId, e => ({ ...e, reportIds: uniq([...e.reportIds, cmd.reportId]) })) });
    case "RemoveReportLink":    return next({ entities: mapEnt(cmd.entityId, e => ({ ...e, reportIds: e.reportIds.filter(x => x !== cmd.reportId) })) });
    case "AddEvidenceLink":     return next({ entities: mapEnt(cmd.entityId, e => ({ ...e, evidenceIds: uniq([...e.evidenceIds, cmd.evidenceId]) })) });
    case "RemoveEvidenceLink":  return next({ entities: mapEnt(cmd.entityId, e => ({ ...e, evidenceIds: e.evidenceIds.filter(x => x !== cmd.evidenceId) })) });
    default: { const _x: never = cmd; throw new Error(`unknown command: ${JSON.stringify(_x)}`); }
  }
  function next(patch: Partial<TKnowledge>): TKnowledge { return Knowledge.parse({ ...k, ...patch }); }
  function uniq(a: string[]) { return [...new Set(a)]; }
}
```

**驗收**：`applyKnowledgeCommand` 對任一 command 都回傳通過 `Knowledge.parse` 的新物件;`Node position / viewport / zoom / selection / hover / edge bend / collapsed state` **不存在於任何 command**。

---

## 7.5 llm-wiki 來源與決定性同步（`packages/core/src/wiki.ts`）

> **本節是整個系統的關鍵。** 真實來源是 llm-wiki 的 markdown,`knowledge.json` 是編譯產物。
> 人類在 UI 的編輯**必須用決定性程式同步回 markdown,不准用 LLM 做這件事**。
> 以下做法已用 Node + `yaml` 實測通過(就地改節點 + 一次性正規化 → diff 只剩語意變動、註解保留、未觸碰欄位不變)。

### 7.5.0 llm-wiki 頁面格式約定（解析/回寫的前提）

每個 entity = 一個 `data/wiki/<id>.md`,格式固定如下,`parseWiki` 與 `commandToMarkdownEdit` 都依賴此約定:

```markdown
---
id: hermes_desktop          # = entity.id（= 檔名）
name: Hermes Desktop
type: system                # entity.type
page_type: entity           # entity | concept | summary；只有 entity/concept 變成 Entity，summary 變成 report
category: [系統]            # ↓ 以下 frontmatter key 對應 facets（由 facetDefs 決定哪些是 facet）
tags: [desktop, gateway]
status: active
reports:                    # report id 清單（參照 reports collection）
  - report_a1
evidence:                   # evidence id 清單
  - evidence_a1
---

Hermes Desktop 是一個桌面閘道程式。   ← 第一段 = summary；全文 = description（散文，人類/LLM 維護）

## Relations                ← entity↔entity 關係專區（不要把關係散在散文裡）
- [[requires::HERMES_DESKTOP_REMOTE_URL]]   ← 「有類型」wikilink：`predicate::目標`
- [[related::Open WebUI]]
```

**兩條硬約定**（缺一則同步會失準）：
1. **wikilink 必須有類型**：`[[predicate::Target]]`。`predicate` 對應 `relationTypes`；解析時取 `::` 前為 predicate、後為目標 entity 名稱/ id。純 `[[Target]]` 一律視為 `related_to`。
2. **結構化關係只放在 `## Relations` 區塊**，散文裡的 `[[...]]` 只當閱讀用、**不**解析成 relation。

### 7.5.1 `parseWiki()` — markdown → canonical（建立索引）

```ts
import matter from "gray-matter";
import type { TKnowledge, TEntity, TRelation } from "./schema";

export interface WikiFile { id: string; raw: string; } // id = 檔名（去 .md）

/** 把整個 wiki 目錄編譯成 canonical index。純函式，不碰檔案系統（檔案由 server 讀好傳入）。 */
export function parseWiki(files: WikiFile[], facetKeys: string[]): TKnowledge {
  const entities: TEntity[] = [];
  const relations: TRelation[] = [];
  for (const f of files) {
    const { data: fm, content } = matter(f.raw);
    if (fm.page_type && fm.page_type !== "entity" && fm.page_type !== "concept") continue; // summary → 另路處理成 report
    const facets: Record<string, string[]> = {};
    for (const k of facetKeys) if (fm[k] != null) facets[k] = toArr(fm[k]);
    const body = content.trim();
    entities.push({
      id: fm.id ?? f.id, name: fm.name ?? f.id, type: fm.type ?? "concept",
      summary: firstParagraph(body), description: body,
      facets, reportIds: toArr(fm.reports), evidenceIds: toArr(fm.evidence),
      updatedAt: fm.updatedAt ?? new Date().toISOString(),
    });
    // 解析 ## Relations 區塊的有類型 wikilink
    for (const m of body.matchAll(/^- \[\[([^\]]+)\]\]/gm)) {
      const [pred, target] = splitLink(m[1]);
      relations.push({
        id: `rel:${fm.id}:${pred}:${target}`,
        subject: fm.id ?? f.id, predicate: pred, object: target,
        evidenceIds: [], updatedAt: new Date().toISOString(),
      });
    }
  }
  // 注意：object 此時可能是「名稱」，需在後處理 resolve 成 entity id（用 name→id 映射）
  return resolveRelationTargets({ schemaVersion: "1.0", facetDefs: [], relationTypes: [],
    entities, relations, reports: [], evidence: [] });
}

const toArr = (v: unknown): string[] => v == null ? [] : Array.isArray(v) ? v.map(String) : [String(v)];
const firstParagraph = (s: string) => s.split(/\n\s*\n/)[0]?.replace(/^#.*$/gm, "").trim() ?? "";
const splitLink = (s: string): [string, string] => s.includes("::")
  ? [s.split("::")[0].trim(), s.split("::").slice(1).join("::").trim()] : ["related_to", s.trim()];
function resolveRelationTargets(k: TKnowledge): TKnowledge { /* name→id 映射後回填 relation.object；略 */ return k; }
```

> `facetDefs` / `relationTypes` 兩張 registry 來自 wiki 的 schema 檔（llm-wiki 的 `CLAUDE.md` 慣例），由 server 另外讀入後合併進 `knowledge.json`。

### 7.5.2 `diffKnowledge()` — 還原人類改了什麼（集合運算，零 LLM）

當你手上只有「編輯前 / 編輯後」兩份 canonical（沒有逐筆 command 紀錄）時，用它還原出 `KnowledgeCommand[]`：

```ts
import type { TKnowledge, TEntity } from "./schema";
import type { KnowledgeCommand } from "./commands";

export function diffKnowledge(oldK: TKnowledge, newK: TKnowledge): KnowledgeCommand[] {
  const cmds: KnowledgeCommand[] = [];
  const oldById = new Map(oldK.entities.map(e => [e.id, e]));
  const newById = new Map(newK.entities.map(e => [e.id, e]));
  const sd = (a: string[], b: string[]) => a.filter(x => !b.includes(x));

  for (const n of newK.entities) {
    const o = oldById.get(n.id);
    if (!o) { cmds.push({ type: "CreateEntity", entity: n }); continue; }
    if (o.name !== n.name)       cmds.push({ type: "RenameEntity", id: n.id, name: n.name });
    if (o.type !== n.type)       cmds.push({ type: "UpdateEntityType", id: n.id, entityType: n.type });
    if (o.summary !== n.summary) cmds.push({ type: "UpdateSummary", id: n.id, summary: n.summary });
    if (o.description !== n.description) cmds.push({ type: "UpdateDescription", id: n.id, description: n.description });
    for (const r of sd(o.reportIds, n.reportIds))   cmds.push({ type: "RemoveReportLink", entityId: n.id, reportId: r });
    for (const r of sd(n.reportIds, o.reportIds))   cmds.push({ type: "AddReportLink", entityId: n.id, reportId: r });
    for (const e of sd(o.evidenceIds, n.evidenceIds)) cmds.push({ type: "RemoveEvidenceLink", entityId: n.id, evidenceId: e });
    for (const e of sd(n.evidenceIds, o.evidenceIds)) cmds.push({ type: "AddEvidenceLink", entityId: n.id, evidenceId: e });
    const keys = new Set([...Object.keys(o.facets), ...Object.keys(n.facets)]);
    for (const k of keys)
      if ((o.facets[k] ?? []).join("|") !== (n.facets[k] ?? []).join("|"))
        cmds.push((n.facets[k]?.length ? { type: "SetFacet", id: n.id, key: k, values: n.facets[k] }
                                       : { type: "RemoveFacet", id: n.id, key: k }) as KnowledgeCommand);
  }
  // relations：以 id 集合比對 → Add/RemoveRelation（略，同樣式）
  return cmds;
}
```

> 更好的是在 UI 編輯時就直接記 command（§9.1），連 diff 都省。`diffKnowledge` 是「只有整份 JSON」時的補救。

### 7.5.3 `commandToMarkdownEdit()` — command 精準改 markdown（決定性、已實測）

每個 command 對應一個明確的 markdown 修改。用 `yaml` 的 **Document API 就地改節點**（保留註解、未觸碰欄位不動）。

```ts
import { parseDocument, isSeq } from "yaml";

function splitFm(md: string) {
  const m = md.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!m) throw new Error("no frontmatter");
  return { fm: m[1], body: m[2] };
}

/** seq 就地增刪到 target，保留存活項目的註解（不要整個 doc.set 換掉）。 */
function setSeqInPlace(doc: any, field: string, target: string[]) {
  const seq = doc.get(field, true);
  if (!isSeq(seq)) { doc.set(field, target); return; }
  for (let i = seq.items.length - 1; i >= 0; i--)
    if (!target.includes(String(seq.items[i].value ?? seq.items[i]))) seq.delete(i);
  const have = seq.items.map((it: any) => String(it.value ?? it));
  for (const v of target) if (!have.includes(v)) seq.add(v);
}

/** 對單一 entity 的 markdown 套用一個 command，回傳新 markdown。body 散文類交給 §7.5.5。 */
export function commandToMarkdownEdit(md: string, cmd: KnowledgeCommand): string {
  const { fm, body } = splitFm(md);
  const doc = parseDocument(fm);
  const seqRemove = (f: string, v: string) => {
    const s = doc.get(f, true);
    if (isSeq(s)) { const i = s.items.findIndex((it: any) => String(it.value ?? it) === v); if (i >= 0) s.delete(i); }
  };
  const seqAdd = (f: string, v: string) => {
    const s = doc.get(f, true); if (isSeq(s)) s.add(v); else doc.set(f, [v]);
  };
  let newBody = body;
  switch (cmd.type) {
    case "RenameEntity":       doc.set("name", cmd.name); break;
    case "UpdateEntityType":   doc.set("type", cmd.entityType); break;
    case "SetFacet":           setSeqInPlace(doc, cmd.key, cmd.values); break;
    case "RemoveFacet":        doc.delete(cmd.key); break;
    case "AddReportLink":      seqAdd("reports", cmd.reportId); break;
    case "RemoveReportLink":   seqRemove("reports", cmd.reportId); break;
    case "AddEvidenceLink":    seqAdd("evidence", cmd.evidenceId); break;
    case "RemoveEvidenceLink": seqRemove("evidence", cmd.evidenceId); break;
    case "AddRelation":        newBody = addRelationLine(body, cmd.relation); break;   // 改 ## Relations 區塊
    case "RemoveRelation":     newBody = removeRelationLine(body, cmd.relationId); break;
    case "UpdateSummary":      newBody = replaceFirstParagraph(body, cmd.summary); break;
    case "UpdateDescription":  newBody = cmd.description; break;                        // 散文整段替換（見 §7.5.5）
    case "CreateEntity":       return newEntityMarkdown(cmd.entity);                    // 產生新檔
  }
  return `---\n${doc.toString().trimEnd()}\n---\n${newBody.startsWith("\n") ? newBody : "\n" + newBody}`;
}
```

`## Relations` 區塊的 `addRelationLine` / `removeRelationLine` 是純行級操作（新增/刪除一行 `- [[predicate::Target]]`），同樣決定性。`newEntityMarkdown` 依 §7.5.0 範本產生新檔。

### 7.5.4 `normalizeWiki()` — 一次性正規化（讓之後每次 diff 都乾淨）

YAML 重新序列化會把 flow 風格的內距正規化（`[系統]`→`[ 系統 ]`）。**對來源檔先跑一次正規化**，之後每次 `commandToMarkdownEdit` 的輸出風格就與來源一致 → git diff 只剩語意變動。

```ts
export function normalizeWiki(md: string): string {
  const { fm, body } = splitFm(md);
  return `---\n${parseDocument(fm).toString().trimEnd()}\n---\n${body}`;
}
```

**實測結果（PoC，可信賴）**：對「人類拿掉 report_a2/a3 + tags 加 internal」的編輯，套用後 `git diff` 為：

```diff
-tags: [ desktop, gateway ] # 人類維護的標籤
+tags: [ desktop, gateway, internal ] # 人類維護的標籤     ← 註解保留，只加 internal
 reports:
   - report_a1
-  - report_a2 # 待會人類認為相關性低，要拿掉                ← 只刪這兩行
-  - report_a3 # 同上
 evidence:
   - evidence_a1                                            ← category 等未觸碰欄位完全不變
```

### 7.5.5 邊界：程式做不到的，不要硬做（誠實切分）

| 變動類型 | 由誰處理 | 怎麼做 |
|---|---|---|
| 結構化欄位（facet / report / evidence / relation / name / type） | **程式**（§7.5.3） | 決定性，diff 乾淨，**禁止用 LLM** |
| 散文 `description` 的人工修改 | **人類** | UI textarea 整段替換（`UpdateDescription`），也是決定性 |
| 散文因刪除而 stale（如刪了 report_a2，正文卻寫「依據報告 A2…」） | **LLM（建議）** | 標記出 stale 句子 → 當建議給人審 → 人核可才改;**不自動改** |
| ingest 新原始資料寫成 markdown | **LLM** | llm-wiki 原生 ingest 流程，不在本系統的同步路上 |

> **核心紀律**：結構同步 = 程式;散文撰寫/清理 = 人或 LLM。原本「叫 27B 看 knowledge.json 去改 markdown」的機械同步整段被 §7.5.2 + §7.5.3 取代;27B 退回只做最後兩列。

### 7.5.6 整條回寫流程（server 端串起來）

```
人類在 UI 編輯
  → (有 command) 直接得 KnowledgeCommand[]
  → (只有新 JSON) diffKnowledge(oldK, newK) 還原 KnowledgeCommand[]
  → 對每個 cmd：讀對應 <id>.md → commandToMarkdownEdit → 寫回（temp+rename）
  → parseWiki(全目錄) 重建 knowledge.json
  → 回傳新 knowledge 給前端覆蓋
```

---

## 8. 後端 API（`apps/server`）

### 8.1 Repository（`repo.ts`）

```ts
export interface KnowledgeRepository {
  load(): Promise<TKnowledge>;                 // 讀 data/wiki/*.md → parseWiki → 回 canonical（並快取成 knowledge.json）
  applyCommands(cmds: KnowledgeCommand[]): Promise<TKnowledge>; // 每個 cmd → 改對應 .md → 重建 index
  loadView(viewId: string): Promise<ViewState | null>;
  saveView(viewId: string, v: ViewState): Promise<void>;
}
```
`WikiFileRepository`（取代原本的 `JsonFileRepository`）：
- **`load()`**：讀 `data/wiki/*.md` + schema 檔 → `parseWiki()` → 回 canonical;同時把結果快取成 `data/knowledge.json`（**唯讀產物**，給除錯/外部工具看，不是來源）。
- **`applyCommands(cmds)`**：對每個 cmd，讀對應 `data/wiki/<id>.md` → `commandToMarkdownEdit()` → 寫回（temp + rename）→ 全部套完後重新 `load()` 重建 index。
- 啟動時若 `data/wiki/` 為空，寫入 `@ecv/core` 的 sample markdown（§2 sample 改為 markdown 範本）。
- view state 仍存 `data/views/<id>.json`。
- **首次啟動對所有 `*.md` 跑一次 `normalizeWiki()`**（§7.5.4），確保之後 diff 乾淨。

### 8.2 路由表

所有回應 JSON。錯誤格式統一 `{ error: string }`。

| Method | Path | 說明 | Body / Query | 回應 |
|---|---|---|---|---|
| GET | `/api/knowledge` | 取完整 canonical | — | `TKnowledge` |
| GET | `/api/entities` | 列出 entity（精簡） | `?facet=key:value` 可選 | `TEntity[]` |
| GET | `/api/entities/:id` | 單一 entity | — | `TEntity` |
| GET | `/api/entities/:id/view` | **3 欄視圖資料** | — | `ColumnView` |
| POST | `/api/commands` | **派發一個 KnowledgeCommand** | `KnowledgeCommand` | `{ knowledge: TKnowledge }` |
| GET | `/api/relations?entityId=:id` | 某 entity 的關係 | — | `TRelation[]` |
| GET | `/api/views/:viewId` | view state | — | `ViewState` |
| PATCH | `/api/views/:viewId` | 更新 view state（含 manualPositions/collapsed） | `Partial<ViewState>` | `ViewState` |
| GET | `/api/agent/context/:id` | **模型讀**：Agent Card | `?format=markdown\|yaml&maxDepth=1\|2` | `text/markdown` 或 `text/yaml` |
| POST | `/api/agent/import?dryRun=1` | **模型寫**：先驗證回計畫 | `TAgentImport` | `ImportPlan` |
| POST | `/api/agent/import` | 核可後合併 | `TAgentImport` | `{ knowledge, plan }` |

**規則**
- 所有「改知識」一律走 `POST /api/commands` → `repo.applyCommands()` → **改 markdown → 重建 index**。**不開**直接 PUT entity 的端點,也**不准**寫 `knowledge.json` 當來源。
- **「只有新 JSON、沒有 command」的相容路徑**：`POST /api/sync`，body 為整份新 canonical → server 內部 `diffKnowledge(currentK, newK)` 還原 command → 同樣走 `applyCommands`。（這就是取代「叫 27B 改 markdown」的端點。）
- `POST /api/agent/import` 內部：先 `planImport`,`plan.ok===false` 回 422 + plan;`dryRun` 一律只回 plan;核可後 `mergeImport` 的結果一樣經 `diffKnowledge` → `applyCommands` 落到 markdown。
- `GET /api/agent/context/:id` 直接回傳 `buildAgentCard` 的字串,`Content-Type` 對應格式。
- 樂觀鎖：command 內若帶 `expectedUpdatedAt`（可選擴充）不符回 409。MVP 可先略,但 entity PATCH 類 command 建議檢查。

| 補充端點 | Method | 說明 |
|---|---|---|
| `/api/sync` | POST | body=整份新 canonical → `diffKnowledge` → `applyCommands`（無 command 紀錄時用） |

---

## 9. 前端（`apps/web`）

### 9.1 State（`store.ts`，zustand）

```ts
interface ViewState {
  viewId: string;
  selectedEntityId: string | null;
  collapsedSections: Record<string, string[]>;       // entityId -> ["evidence", ...]
  manualPositions: Record<string, { x: number; y: number }>; // nodeId -> pos
  viewport: { x: number; y: number; zoom: number };
}

interface Store {
  knowledge: TKnowledge | null;
  view: ViewState;
  // canonical 操作：一律經由 command（呼叫 POST /api/commands 後以回傳覆蓋本地）
  dispatch(cmd: KnowledgeCommand): Promise<void>;
  // view 操作：只更新本地 + debounce PATCH /api/views/:id，絕不產生 command
  focusEntity(id: string): void;
  setManualPosition(nodeId: string, pos: { x: number; y: number }): void;
  toggleCollapse(entityId: string, section: string): void;
}
```

**鐵則（重申）**：React Flow 的 `onNodesChange`/`onEdgesChange` → 只呼叫 `setManualPosition` / viewport 更新 → 進 view state。**唯一**會產生 command 的畫布操作是「拉一條 handle 連線兩個 entity」→ `AddRelation`、「刪一條 relation edge」→ `RemoveRelation`。其餘語意編輯都在 §9.3 的 Inspector 表單。

### 9.2 畫布（`EntityCanvas.tsx`）

- 用 `@xyflow/react`。`nodeTypes` / `edgeTypes` 註冊 §7.1/§7.2 的型別。
- 資料來源：`GET /api/entities/:id/view` → `viewToReactFlow()` → 套用 `view.manualPositions` 覆蓋座標。
- 每個 node 元件用 `<Handle>` 明確標出 `left` / `right` / `top` / `bottom`，id 與 `viewToReactFlow` 產生的 handle 對齊。
- 切換 focus entity：點 `entityNode` 或 `relatedEntityListNode` 的某一項 → `focusEntity(id)` → 重新抓 view。

**Node 元件清單**（`components/nodes/`）：`EntityNode`、`FacetNode`、`DetailNode`、`ReportNode`、`EvidenceNode`、`RelatedEntityListNode`（顯示前 N 個+「展開全部」）。`relationLaneNode` Phase 2 才做。

### 9.3 編輯面板（`Inspector.tsx`）

選中 entity 時顯示表單,每個欄位 onBlur/儲存時派發對應 command：
- 名稱 → `RenameEntity`；type → `UpdateEntityType`；summary → `UpdateSummary`；description → `UpdateDescription`。
- facet 區：每個 facetDef 一組 tag input → `SetFacet` / `RemoveFacet`。
- 關係區：列出 `relatedEntities`,可刪 → `RemoveRelation`;可新增（選對方 entity + predicate）→ `AddRelation`。
- 報告/證據：加減連結 → `Add/RemoveReportLink`、`Add/RemoveEvidenceLink`。
- 「匯出給模型」按鈕：開新分頁 `GET /api/agent/context/:id?format=markdown`（或 yaml）。

### 9.4 搜尋與 filter

- `SearchBar`：依 name 模糊搜 → 選中 → `focusEntity`。
- `FacetFilter`：讀 `facetDefs` 列出可選值,選取後 `GET /api/entities?facet=key:value` 縮小左側清單。

### 9.5 ELK（Phase 2，`layout/elkLayout.ts`）

僅在「多 entity 關係視圖」啟用。**兩層 layout**：
1. 內層（每個 entity 的 facet/detail 衛星）→ 沿用 §5.1 固定相對座標,不進 ELK。
2. 外層（只有 entity 節點 + relation 邊）→ 丟 ELK `layered`,`elk.direction=RIGHT`,`elk.edgeRouting=ORTHOGONAL`,port 用 `FIXED_SIDE`（entity↔entity 走 top/bottom）。ELK 在 web worker 跑（`elkjs` worker build）。
3. ELK 回來後用 `applyElkLayoutToReactFlow` 只更新 entity 座標,衛星節點跟著平移;**不覆蓋任何 data 欄位**。

Phase 1 可先不實作,畫布只顯示單一聚焦 entity 的 3 欄。

---

## 10. 版本與啟動

`package.json`(root)：
```json
{ "private": true, "workspaces": ["packages/*", "apps/*"],
  "scripts": { "dev:server": "npm -w @ecv/server run dev",
               "dev:web": "npm -w @ecv/web run dev",
               "test": "vitest run" } }
```
鎖定主要依賴（用這些大版本）：`zod@^3`、`yaml@^2`、`gray-matter@^4`、`express@^4`、`react@^18`、`@xyflow/react@^12`、`elkjs@^0.9`、`zustand@^4`、`vite@^5`、`typescript@^5`、`vitest@^1`。

啟動：
```
npm install
npm run dev:server   # http://localhost:8787
npm run dev:web      # http://localhost:5173 （vite proxy /api -> 8787）
```

---

## 11. Definition of Done（逐項可測,實作完要自己核對）

**Core（vitest，`packages/core/test`）**
- [ ] `Knowledge.parse(sample)` 通過。
- [ ] `to3ColumnView(sample,"entity_a")`：left 含「分類/標籤」、center 是 entity_a、right.related 含 entity_b（名字已 resolve）。
- [ ] `relatedEntities` 進出兩方向都抓得到。
- [ ] `buildAgentCard(sample,"entity_a")` 的 markdown：含 `# Named Entity A`、相關實體用名字（**不含** `entity_b` 這個 id）、含證據 quote;輸出**不含** position/zoom/handle 字樣。
- [ ] `buildAgentCard(... format:"yaml")` 可被 `yaml.parse` 解析。
- [ ] 每個 `KnowledgeCommand` 經 `applyKnowledgeCommand` 後仍通過 `Knowledge.parse`,且原物件未被 mutate。
- [ ] `planImport`：dangling 參照時 `ok===false`;`mergeImport` 後新 entity/relation 存在。

**Wiki 同步（vitest，§7.5 ★ 最關鍵）**
- [ ] `parseWiki(sampleWikiFiles)` → 轉出的 canonical 與既有 `sample` knowledge **逐欄相等**（用今天 27B 產的 knowledge.json 當期望值對拍）。
- [ ] round-trip：`parseWiki` → `to3ColumnView` → 左 facets / 右 reports·evidence·related 正確。
- [ ] `diffKnowledge(old,new)`：拿掉兩個 reportId → 還原出剛好兩個 `RemoveReportLink`,無多餘 command。
- [ ] `commandToMarkdownEdit`：對 `RemoveReportLink` 套用後,markdown **只少那一行**;frontmatter 其他欄位與註解**逐字不變**（先 `normalizeWiki` 過）。
- [ ] `SetFacet`（既有 tags 加一項）：用就地增刪,**保留該行註解**,不整段 replace。
- [ ] `normalizeWiki` 對已正規化的檔案再跑一次 → 輸出與輸入相同（idempotent）。
- [ ] `UpdateDescription`：body 整段替換,frontmatter 不動。

**Server**
- [ ] `GET /api/entities/:id/view` 回 `ColumnView`。
- [ ] `POST /api/commands` 派發 `RenameEntity` 後,**對應 `data/wiki/<id>.md` 的 frontmatter `name` 已改**,且重建後 `GET /api/knowledge` 反映變更;`knowledge.json` 為重建產物。
- [ ] `POST /api/sync`（送整份新 canonical，少兩個 report）→ 對應 `.md` 只少兩行 report,git diff 乾淨。
- [ ] `GET /api/agent/context/:id?format=yaml` 回 `text/yaml` 且可解析。
- [ ] `POST /api/agent/import?dryRun=1` 對壞資料回 422 + plan。

**Web（人工驗收）**
- [ ] 選一個 entity → 左 facets、中 entity、右 description/related/reports/evidence 正確分欄。
- [ ] 在 Inspector 改名稱 → 畫布即時更新 → 重整後仍在（**已落地到 `data/wiki/<id>.md`**）。
- [ ] 拖曳節點位置 → 重整後位置保留,但 **markdown 與 `knowledge.json` 都未因此變動**（只進 view.json）。
- [ ] 拿掉一個 report 連結 → 看 `git diff data/wiki/` **只少一行**,其餘逐字不變。
- [ ] related 超過門檻時 collapse 成清單,可展開。
- [ ] 「匯出給模型」開啟可讀的 Markdown/YAML。

---

## 12. 分階段交付（建議 PR 切分）

1. **PR1 — core**：schema + selectors + view + agent + commands + sample + 全部 core 測試綠燈。
2. **PR2 — wiki adapter（§7.5，★ 先於 server）**：`parseWiki` + `diffKnowledge` + `commandToMarkdownEdit` + `normalizeWiki` + 全部 §7.5 測試綠燈。**這是接 llm-wiki 的核心,務必先做穩。**
3. **PR3 — server**：`WikiFileRepository`（讀寫 markdown）+ 路由 + `/api/sync` + agent 端點 + server 測試。
4. **PR4 — web 唯讀**：抓 view、React Flow 3 欄渲染、focus 切換、搜尋。
5. **PR5 — web 編輯**：Inspector + command 派發 → 落地 markdown + view state 落地。
6. **PR6 — agent 寫入**：import dryRun/merge → markdown。
7. **PR7 — ELK 多 entity 視圖**（Phase 2，兩層 layout + web worker）。

先做到 PR5 就已滿足你的兩個核心目標（人類看與編輯且決定性回寫 llm-wiki、模型讀寫）。PR7 是加分。
**建議 PR2 先用今天 27B 產的 `knowledge.json` 當對拍基準**：寫一份對應的 sample markdown,驗 `parseWiki(md) === 那份 json`,確認 adapter 方向正確再往下。

---

## 13. 給 27B 實作者的提醒（務必遵守）

1. **唯一真實來源是 `data/wiki/*.md`**。`knowledge.json` 是 `parseWiki` 的編譯產物,**唯讀、不可手改、不可當來源寫入**。
2. **絕不用 LLM 做「把編輯同步回 markdown」**。結構化變動一律走 `diffKnowledge` → `commandToMarkdownEdit`（決定性程式）。LLM 只做 ingest 新資料 + 散文 stale 建議（人審）。見 §7.5.5。
3. **不要把 React Flow / ELK 當資料庫**。它們只是 view layer。
4. **不要從 React Flow 的幾何 change 反推語意編輯**;語意編輯只能來自明確的 command。
5. **改 markdown 一律用 `yaml` Document API 就地改節點 + 先 `normalizeWiki`**,不要整段重寫 frontmatter（會吃掉註解、汙染 diff）。目標：`git diff` 只剩語意變動。
6. **給模型讀的輸出絕不含 UI 欄位**;對方一律用名字,不用 id。
7. **模型寫回一律走 JSON + zod 驗證 + dryRun plan**,核可後一樣經 `diffKnowledge`→`commandToMarkdownEdit` 落到 markdown。
8. wikilink 必須有類型 `[[predicate::Target]]`,關係只放 `## Relations` 區（§7.5.0）。
9. 任何寫入後維持 §3 的四條不變量;改完 schema 相關程式要同步更新測試。
10. 不確定的細節 → 選最簡方案,不擴張範圍,並在 PR 描述標注假設。
