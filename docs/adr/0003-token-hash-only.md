# ADR-0003: LoginToken 只儲存 sha256 hash,不存原始 token

- **狀態**: Accepted
- **日期**: 2026-04-19
- **決策者**: Shane (SA / 開發者)

## Context — 我們在解決什麼問題?

Magic Link 是「**持有即登入**」的憑證 — 任何人拿到原始 token,都能完成這個 user 的登入。原始 token 在系統裡的生命週期:

```
[secrets.token_urlsafe(32)]
        │
        ├──→ 寄出 Email 的 URL 裡
        └──→ 中台需要記錄這個 token,以便使用者點連結時可以驗證
```

第二步「中台記錄」這件事,有三種做法:

1. 直接存原始 token
2. 存對稱加密後的 token(可解回原始)
3. 存單向 hash(無法解回)

如果 DB 外洩,做法 1 等於所有有效 token 全部洩漏 → 攻擊者立即登入所有帳號。做法 2 雖然有加密,但加密金鑰若也在同一台機器(常常是),等於沒加密。做法 3 即使外洩,攻擊者也只拿到一堆 hash,無法逆推原始 token。

這個權衡跟「為什麼 DB 不存明文密碼」是同一個道理。

## Decision — 我們選了什麼?

**LoginToken.token_hash 永遠儲存 sha256(raw_token) 的 hex(64 chars),原始 token 永不入庫。**

- 簽發時:`secrets.token_urlsafe(32)` 產生原始 token,只放進寄出的 URL,DB 存 sha256
- 驗證時:使用者點連結帶原始 token 進來 → 程式即時計算 sha256 → 用 hash 反查 LoginToken row → 比對 `is_usable`
- 比對欄位 `token_hash` 加 `UNIQUE INDEX`,確保查詢效率

## Considered Options — 還評估過哪些?

### 選項 1 — 直接存原始 token

- ✅ 程式最簡單
- ❌ DB 外洩 = 所有有效 token 立即被利用
- ❌ Backup / Replica / Log 都可能無意間散播原始 token

### 選項 2 — 對稱加密(AES-GCM)

- ✅ DB 外洩單獨無用
- ❌ 加密金鑰實務上常跟 DB 一起被取走(同一台 server 的環境變數)
- ❌ 增加加解密開銷與金鑰管理複雜度
- ❌ 沒有比 hash 更強(因為原始 token 本來就是隨機字串,hash 已經足夠)

### 選項 3 — sha256 單向 hash【選中】

- ✅ DB 外洩**無法逆推**(原始 token 32 bytes 隨機,brute force 不可行)
- ✅ 程式邏輯簡單,Python 內建 `hashlib`
- ✅ 跟「不存密碼明文」是同一個安全模型
- ⚠ 一旦原始 token 寄出,中台就**無法**從 DB 反查它(這是設計目的,不是缺點)

### 選項 4 — bcrypt / argon2(像密碼一樣)

- ✅ 抗 GPU 暴力破解
- ❌ **過度設計**:原始 token 是 32 bytes 高熵隨機,sha256 已經安全;bcrypt 用於低熵的人類密碼才有意義
- ❌ 計算成本高,每次 magic link 點擊都要算

## Consequences — 這個決定帶來什麼?

### ✅ 正面

- **DB 外洩不等於登入外洩** — 攻擊者拿到一堆 sha256,無法從中還原可用的 magic link
- **稽核紀錄可保留** — `accounts_login_token` 可以長期保留作為登入歷史(誰、何時、從哪 IP),不會因為「保留歷史」而擴大攻擊面
- **與密碼安全模型一致** — `User.password` 也是 hash,團隊不需要在不同安全模型間切換思維

### ⚠ 負面 / Trade-off

- **客服無法「重發同一個 token」** — 因為 DB 沒有原始 token,只能撤銷 + 重新簽一個新的。實務上這也是更安全的做法,所以不算缺點
- **無法做「展示最近 magic link 連結」之類的 admin 功能** — Admin 只能看到 hash,不能看到原始 URL
- **如果寄信失敗,使用者收不到 link 也無法重發同一個** — 必須讓使用者重新請求(會觸發 cooldown)

### 🔁 後續追蹤

- 監控 `LoginToken` 的 `created` vs `consumed` 比率,異常下降可能代表 email 送達有問題
- 評估是否在 `created_ip` 欄位上加上 hashed/anonymized 處理(GDPR 等隱私規範的長期策略)

## References

- Code:
  - [`apps/accounts/models.py`](../../apps/accounts/models.py) — `LoginToken.token_hash` 欄位定義
  - [`apps/accounts/sso_views.py`](../../apps/accounts/sso_views.py) — `_hash_token()` helper、`secrets.token_urlsafe(32)`
- 文件:
  - [`docs/data-model.md` 3.2 accounts_login_token](../data-model.md#32-accounts_login_token)
  - [`docs/architecture.md` Level 5 State Diagram](../architecture.md#level-5--state-diagramlogintoken-生命週期)
- 外部:
  - [OWASP: Storing Passwords](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) — 雖然講密碼,但「不存可逆」這個原則完全適用 token
  - [Python `secrets` 模組文件](https://docs.python.org/3/library/secrets.html)
