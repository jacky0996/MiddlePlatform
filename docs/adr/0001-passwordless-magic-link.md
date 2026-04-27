# ADR-0001: 採用 Passwordless Magic Link 取代密碼登入

- **狀態**: Accepted
- **日期**: 2026-04-19
- **決策者**: Shane (SA / 開發者)

## Context — 我們在解決什麼問題?

中台的核心責任是身分驗證,所以「使用者怎麼證明自己是本人」是第一個要決定的事。傳統做法是 **email + password**,但這帶來一連串「密碼相關」的工程負擔:

- 密碼雜湊與升級(bcrypt → argon2 → ?)
- 密碼複雜度策略
- 防暴力破解(rate limit、帳號鎖定)
- 忘記密碼流程(再生 token、寄信、重設)
- 防撞庫(check 弱密碼字典、HIBP API)
- 密碼洩漏應變(強制 reset、通知)

而本專案的場景:

- 使用者數量不多(企業內部 + 邀請制)
- 寄信機制本來就要做(忘記密碼也需要)
- Email 帳號本身的安全性不會比中台密碼差(若 email 被駭,就算密碼安全也擋不住「忘記密碼」攻擊)

所以「**密碼**」這層額外的安全機制,實際保護的東西不多,卻帶來大量工程負擔。

## Decision — 我們選了什麼?

**採用 Magic Link 作為唯一登入方式**:使用者輸入 email → 中台寄一次性連結 → 使用者點連結即登入。

- 不儲存密碼 (`set_unusable_password()`)
- 不提供「設定密碼」UI
- 程式化 API(`/api/auth/register`, `/api/auth/login`)保留密碼欄位,但**僅供測試或未來 federation 用**,不對外公開

## Considered Options — 還評估過哪些?

### 選項 1 — 傳統 email + password

- ✅ 使用者習慣
- ✅ 不依賴信件送達
- ❌ 上述所有密碼工程負擔
- ❌ 增加攻擊面(撞庫、弱密碼、洩漏)

### 選項 2 — Passwordless Magic Link 【選中】

- ✅ 不存密碼 = 不會洩密碼
- ✅ 整套機制只依賴「Email 帳號的所有權」,跟「忘記密碼」本來就依賴同一件事
- ✅ UX 簡單,適合 B2B 內部系統
- ⚠ 依賴 email 可達性(信件被擋會讓人無法登入)
- ⚠ 比密碼登入慢(要去信箱)

### 選項 3 — 第三方 OAuth (Google / Microsoft)

- ✅ 安全責任外包給大廠
- ✅ UX 最好(一鍵登入)
- ❌ 強迫使用者必須有特定帳號
- ❌ 增加外部依賴與設定複雜度
- 🔁 列為 **Roadmap**,未來可作為 Magic Link 之外的選項

### 選項 4 — WebAuthn / Passkey

- ✅ 業界趨勢、最高安全
- ❌ 對作品集場景過度工程,需要硬體 / 系統 keychain 支援
- 🔁 列為 **長期 Roadmap**

## Consequences — 這個決定帶來什麼?

### ✅ 正面

- **DB 無密碼** → 即使 DB 整批外洩,攻擊者拿不到登入憑證
- **無需處理密碼相關工程**:省下複雜度規則、忘記密碼流程、撞庫防護
- **安全模型集中**:整個系統的「身分證明」只依賴一件事 — Email 收得到,容易稽核

### ⚠ 負面 / Trade-off

- **依賴 email 送達率**:被擋信、延遲、進垃圾匣 → 使用者無法登入。緩解方式:Roadmap 接 SES / SendGrid,並監控送達率
- **登入比較慢**:每次都要去開信。緩解方式:登入後簽 7 天的 refresh token,日常不用重登
- **email 帳號本身被駭就無解**:這是 passwordless 的本質,跟「忘記密碼」流程的風險是同一個

### 🔁 後續追蹤

- 若使用者抱怨登入太慢 → 評估加上 Google OAuth(選項 3)
- 若需要更高安全(金融、醫療場景)→ 評估 Passkey(選項 4)或 MFA

## References

- Code:
  - [`apps/accounts/managers.py`](../../apps/accounts/managers.py) — `create_passwordless_user`
  - [`apps/accounts/sso_views.py`](../../apps/accounts/sso_views.py) — Magic Link 簽發 / 核銷
- 文件:
  - [`docs/architecture.md` Level 5 State Diagram](../architecture.md#level-5--state-diagramlogintoken-生命週期)
  - [`docs/overview.md` 第 5 條設計原則](../overview.md#5-設計原則guiding-principles)
- 外部:
  - [Auth0: What is Passwordless Authentication?](https://auth0.com/blog/what-is-passwordless-authentication/)
  - [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
