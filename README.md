# Middle Platform — SA 文件索引

本目錄為 Middle Platform(SSO 中台)的系統分析文件,給三類讀者使用:

- **使用者** — 想知道怎麼登入
- **開發者 / SA / Architect** — 想知道系統長什麼樣、為什麼這樣設計
- **未來維護者** — 想知道某個技術決策當初的取捨

文件採 Markdown + Mermaid 撰寫,GitHub 直接渲染,不需要任何工具即可閱讀。

---

## 推薦閱讀順序

| # | 文件 | 給誰看 | 一句話 |
|---|---|---|---|
| 1 | [overview.md](./overview.md) | 所有人 | **為什麼**要做這個系統(動機、定位、Scope) |
| 2 | [use-cases.md](./use-cases.md) | SA / 開發者 / 審查者 | 系統能做什麼(Actor + Use Case Diagram) |
| 3 | [user-flow.md](./user-flow.md) | UX / 前端 / SA | 使用者會看到什麼畫面、按什麼按鈕(User Flow + Sequence Diagram) |
| 4 | [architecture.md](./architecture.md) | 開發者 / Architect | 系統長什麼樣(C4 Context / Container / Component / Class / State) |
| 5 | [data-model.md](./data-model.md) | 開發者 / DBA | 資料怎麼存(ERD + 表結構 + 索引設計) |
| 6 | [api-spec.md](./api-spec.md) | 串接方(EDM、其他子系統) | 對外 API 完整規格 |
| 7 | [deployment.md](./deployment.md) | Ops / Architect | 怎麼部署、容器組成、網路拓樸 |
| 8 | [user-guide.md](./user-guide.md) | End User | 第一次登入怎麼操作 |
| 9 | [adr/](./adr/) | 後續維護者 | 關鍵技術決策的「為什麼」 |

---

## 不同角色的入口建議

| 你是誰 | 從這裡開始 |
|---|---|
| **第一次來** | `overview.md` → `architecture.md` → `user-flow.md` |
| **要 review 設計** | `use-cases.md` → `architecture.md` → `adr/` |
| **要串接 API** | `api-spec.md` → `user-flow.md` 的 Sequence Diagram |
| **要部署 / 維運** | `deployment.md` → 專案根目錄的 `README.md` |
| **要查 DB schema** | `data-model.md` |
| **要學登入操作** | `user-guide.md` |

---

## 文件公約

- **圖優於文字**:盡量用 Mermaid 畫圖,文字補關鍵說明
- **每份文件 < 5 分鐘看完**:超過就拆檔
- **變更 code 時同步更新**:文件與 code 同 repo,改 model 就改 `data-model.md`,改 endpoint 就改 `api-spec.md`
- **決策必留 ADR**:任何「為什麼選 A 不選 B」的判斷,新增一份 ADR(模板見 [`adr/`](./adr/))
