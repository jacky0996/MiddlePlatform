# Architecture Decision Records (ADR)

本目錄收錄 Middle Platform 的關鍵架構決策。每份 ADR 回答一個「**為什麼選 A 不選 B**」的問題,讓未來維護者(包括未來的自己)在改動前能先理解當初的取捨。

## 為什麼要寫 ADR

- **避免重複辯論**:同一個決策每個新人都重新問一次,團隊成本很高
- **避免錯誤推翻**:不知道為何選 A 的人,容易因為短期方便就改成 B,踩同一個坑
- **作為 SA 思維證據**:一個專案的 ADR 數量與品質,直接反映 owner 的設計深度

## 索引

| # | 標題 | 狀態 | 影響範圍 |
|---|---|---|---|
| [0001](./0001-passwordless-magic-link.md) | 採用 Passwordless Magic Link 取代密碼 | Accepted | 認證機制、UX、安全模型 |
| [0002](./0002-jwt-vs-session.md) | 業務系統間用 JWT 而非 Session | Accepted | 跨系統通訊、可擴展性 |
| [0003](./0003-token-hash-only.md) | LoginToken 只儲存 sha256 hash | Accepted | DB schema、外洩防護 |

## ADR 模板

新增 ADR 時複製這個結構:

```markdown
# ADR-XXXX: <一句話標題>

- **狀態**: Proposed | Accepted | Deprecated | Superseded by ADR-YYYY
- **日期**: YYYY-MM-DD
- **決策者**: <角色或姓名>

## Context — 我們在解決什麼問題?
<背景、限制條件、為什麼這個決策現在要做>

## Decision — 我們選了什麼?
<明確一句話的決定>

## Considered Options — 還評估過哪些?
1. **選項 A** — pros / cons
2. **選項 B** — pros / cons
3. **選項 C** — pros / cons

## Consequences — 這個決定帶來什麼?
- ✅ 正面影響
- ⚠ 負面影響 / 已知 trade-off
- 🔁 後續需要追蹤的事項

## References
- 相關 code: ...
- 相關文件: ...
- 外部資料: ...
```

> ADR 一旦被 `Accepted`,**不要回頭改它的結論**。要改變就新增一份 `Superseded by ADR-XXXX`,保留歷史脈絡。
