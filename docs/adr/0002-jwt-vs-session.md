# ADR-0002: 業務系統間採用 JWT 而非 Server Session

- **狀態**: Accepted
- **日期**: 2026-04-19
- **決策者**: Shane (SA / 開發者)

## Context — 我們在解決什麼問題?

中台簽出的「身分信物」會被多個業務系統(EDM 等)使用。每個業務系統收到信物後,需要回答兩個問題:

1. **這個信物是真的嗎?**(Authentication)
2. **持有者是誰?**(Identity Resolution)

兩個基本的技術選項:

- **Session-based**:中台維護一個 session store(DB / Redis),信物只是 session ID,業務系統每次收到都要回中台查
- **Token-based (JWT)**:信物本身帶簽章與身分資訊,業務系統用公鑰 / 共享 secret 自己驗,免回中台

選哪個,牽動中台的可擴展性、業務系統的耦合度、以及登出機制的複雜度。

## Decision — 我們選了什麼?

**採用 JWT (HS256) 作為跨系統信物**:

- 中台用 SimpleJWT 簽發 access + refresh token
- 業務系統可以**自己驗 JWT 簽章**(知道 SECRET_KEY 即可),不一定要回中台
- 中台仍提供 verify endpoint,給「不想/不能持有 secret」的業務系統使用
- Refresh token 有黑名單機制(`token_blacklist_*` 表),用於主動撤銷

## Considered Options — 還評估過哪些?

### 選項 1 — Server Session(中台維護 session store)

- ✅ 登出立即生效(刪 session 即可)
- ✅ 不用解決 token rotation、blacklist 等問題
- ❌ **每個業務 request 都要回中台**,中台變成單點瓶頸與 SPOF
- ❌ 跨域 cookie 處理麻煩(SameSite、Secure、Domain)
- ❌ 中台一旦短暫不可用,所有業務系統都登入失敗

### 選項 2 — JWT (HS256, 對稱密鑰)【選中】

- ✅ 業務系統自驗,中台無流量負擔
- ✅ 中台短暫故障,**已登入使用者不受影響**(token 還沒過期就能繼續用)
- ✅ 標準清楚,SimpleJWT 開箱可用
- ⚠ 登出無法立即生效:access token 在 TTL 內仍有效。緩解:**短 TTL (30min) + refresh blacklist**
- ⚠ 所有業務系統必須**信任並持有 SECRET_KEY**,洩漏會造成大規模偽造

### 選項 3 — JWT (RS256, 非對稱密鑰 + JWKS)

- ✅ 同選項 2 的所有優勢
- ✅ 業務系統只需要**公鑰**,即使前端可見也無風險
- ✅ 中台可以做 key rotation 而不用通知所有業務系統(透過 JWKS endpoint)
- ⚠ 部署複雜度高(產 RSA key、JWKS endpoint、rotation 流程)
- 🔁 列為 **明確的 Roadmap**:當業務系統數量 ≥ 3,或對外開放第三方接入時切換

### 選項 4 — OAuth 2.0 / OIDC 完整實作

- ✅ 業界標準,生態最成熟
- ❌ 對「自己人用的中台」過度工程(完整實作要 5+ flow、grant type、scope 等)
- 🔁 若未來真的要對外開放(類似企業 IdP-as-a-Service),再評估改造

## Consequences — 這個決定帶來什麼?

### ✅ 正面

- **中台可水平擴展**:無 session 黏滯,任何 instance 都可以驗任何 token
- **故障隔離**:中台升級 / 重啟,**已登入使用者完全無感**
- **跨域簡單**:JWT 走 `Authorization` header,不依賴 cookie

### ⚠ 負面 / Trade-off

- **登出延遲**:JWT 在 TTL 內無法被撤銷。**緩解措施**:
  - Access token TTL 限制在 30 分鐘
  - Refresh token 有 blacklist,主動 logout 會立即生效
  - 對「立即登出」要求高的場景(改密碼、被駭),考慮加上 token version + DB 一次性 query(性能 trade-off)

- **共用 SECRET_KEY 風險**:HS256 是對稱密鑰,任何業務系統洩漏 = 所有系統都能被偽造 token 攻擊
  - 緩解:Roadmap 切到 RS256(選項 3)
  - 短期:SECRET_KEY 只放在 server 環境變數,不入 repo;Email backend 不夾帶 secret

- **不能 invalidate 單一 access token**:這是 JWT 本質的限制,業界的解法都是 trade-off

### 🔁 後續追蹤

- 業務系統數量 ≥ 3 時,切換到 RS256 + JWKS
- 加入 access token blacklist?(會變相 session,需評估必要性)
- 監控 refresh rotation 異常(同一 jti 被重複 refresh 嘗試 = 可能被竊)

## References

- Code:
  - [`config/settings.py`](../../config/settings.py) — `SIMPLE_JWT` 設定
  - [`apps/accounts/views.py`](../../apps/accounts/views.py) — `LoginView` / `LogoutView` / `VerifyTokenView`
- 文件:
  - [`docs/api-spec.md`](../api-spec.md)
  - [`docs/data-model.md` 3.3 token_blacklist](../data-model.md#33-simplejwt--token_blacklist_)
- 外部:
  - [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
  - [Auth0: JWT vs Session Cookies](https://auth0.com/blog/cookies-vs-tokens-definitive-guide/)
  - [SimpleJWT 文件](https://django-rest-framework-simplejwt.readthedocs.io/)
