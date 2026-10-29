# TikTok Shop 开放平台 API 手册（AI 联调版）

> 数据来源：官方文档站 [Partner Center](https://partner.tiktokshop.com/docv2/page/tts-developer-guide) 及各接口详情页（文档站为 SPA，正文需浏览器/Playwright 渲染后抓取）。
> **用途**：给 AI / 开发者做本仓库 `testAPI/tiktok`（规划中）联调对照——接口做什么、关键参数必传什么、响应关键字段、模块间如何串。
> **版本策略**：接口版本是**日期制**（如 `202309`、`202509`），路径形如 `/{模块}/{日期版本}/{资源}`。下文路径以全量抓取稿 `tts_API.md` 里当前收录的接口为准；同一能力若文档站已换新日期版本，不要继续用旧路径。字段与枚举只使用该接口页写出的值。
> **统一入口**：
> - 业务 API：`https://open-api.tiktokglobalshop.com`（US 区应用使用对应 US 域名，以应用所在区控制台标注为准）
> - 授权/Token：`https://auth.tiktok-shops.com`（US 区对应 US 授权域名，以控制台为准）
> - 卖家授权页：`https://services.tiktokshop.com/open/authorize`（US 区 `https://services.us.tiktokshop.com/open/authorize`）

---

## 〇、背景知识（必读）

### 0.1 平台定位与整体架构

TikTok Shop 开放平台（Partner API）面向卖家、服务商（Partner）与达人（Creator）三类角色，覆盖商品、订单、履约、物流、售后、财务、达人分销、数据分析等域。与敦煌网手册（`dhgate_API.md`）对照，理解上有四个关键差异：

1. **授权体系更重**：OAuth2 授权码模式 + 每请求 HMAC 签名双保险；敦煌网只有简单公共参数。
2. **多店铺/多区域隔离**：一次卖家授权拿到的 access_token 可以覆盖该卖家授权给应用的多家店（`Get Authorized Shops` 返回 `shops` 列表）。跨境卖家 `seller_type=CROSS_BORDER` 会有多个国家站。店铺级接口用对应店的 `shop_cipher` 指定店铺，不要把 A 店的 cipher 配到 B 店的请求上。达人 token、服务商 token 与卖家 token 不能混用。
3. **推拉结合**：平台有成熟的 Webhook 事件推送（订单状态、售后、包裹、商品审核、授权变化等），敦煌网是纯拉模式。生产建议「Webhook 实时 + 定时轮询兜底」双轨。
4. **强 scope 控制**：每个接口需要应用申请并获卖家授权的 scope；scope 不够时报 105005，需卖家重新授权。

### 0.2 角色与 token

| 角色 | 授权入口 | user_type | 说明 |
| --- | --- | --- | --- |
| Seller（卖家） | `services.{region}.tiktokshop.com/open/authorize?service_id=...` | 0 | 本仓库主要场景：店铺授权后操作商品/订单/履约 |
| Creator（达人） | `https://shop.tiktok.com/alliance/creator/auth?app_key=...&state=...` | 1 | 达人分销/联盟数据，token 与卖家 token 不可混用 |
| Partner（旧） | 以换 token 回包为准 | 2 | 旧版 Partner |
| Partner（当前） | 服务商授权入口，见 Partner authorization guide | 3 | Affiliate Partner / TAP；用 `category_asset_cipher` 标识类目资产 |
| Global Selling 卖家 | 以换 token 回包为准 | 4、5 | 4 为跨境 / Global Selling；5 为当前 Global Selling 类型 |

> 换 token 后必须核对 `user_type`。达人集成应得到 `1`，Affiliate Partner（TAP）应得到 `3`。收到表外取值时，说明授权走错了入口。

### 0.3 典型链路（优先级）

```text
授权 access_token（OAuth2）
  ├─ 店铺：authorization/202309/shops 拿 shop_id + shop_cipher（店铺映射落库）
  ├─ 商品：categories → rules/attributes → product.create → product.search
  ├─ 履约：order.search → order.detail → package.search → package.ship
  ├─ 售后：return.search → return.approve/reject；cancellation.approve/reject
  ├─ 财务：finance/202309/statements → finance/202501/.../statement_transactions
  └─ 事件：event.webhooks 配置回调 + 每次推送验签
```

```mermaid
flowchart TD
    A["OAuth2 access_token"] --> B["authorization/202309/shops<br/>shop_id + shop_cipher"]
    B --> C["product: categories → rules → create"]
    C --> D["order/202309/orders/search"]
    D --> E["order/202507/orders 详情"]
    E --> F["fulfillment: packages/search → ship"]
    E --> G["return_refund: approve/reject"]
    D --> H["webhook: ORDER_STATUS_CHANGE 实时推送"]
    F --> I["finance: statements / statement_transactions"]
```

---

## 一、公共约定（所有接口）

### 1.1 公共参数（Query）

| 参数 | 类型 | 必须 | 说明 |
| --- | --- | --- | --- |
| `app_key` | String | 是 | 应用唯一标识（Partner Center 建应用获得） |
| `timestamp` | int | 是 | 10 位 Unix 秒（GMT/UTC+0）。有效区间是 **[当前时间 − 5 分钟, 当前时间 + 30 秒]**。超出报 `36009004` |
| `sign` | String | 是 | 签名，算法见 1.3 |
| `shop_cipher` | String | 视接口 | 店铺密文。店铺级接口在详情要求时放入 query，并参与签名。来自 Get Authorized Shops 的 `cipher` |

### 1.2 请求头

| Header | 必须 | 说明 |
| --- | --- | --- |
| `content-type` | 是 | `application/json`；上传二进制时按该接口要求用 `multipart/form-data` |
| `x-tts-access-token` | 是（202309 及以后的业务接口） | Get Access Token 返回的 access_token，放在这个请求头里。签名覆盖 path、query（去掉 `sign`）和原始 body |

### 1.3 签名算法（sign）

> 以官方 [Sign your API request](https://partner.tiktokshop.com/docv2/page/sign-your-api-request) 页为准，此处为实操步骤摘要。

1. 取全部 **query 参数**，剔除 `sign` 与 `access_token`。`shop_cipher` 若在 query 里，要留在待签名参数中。`x-tts-access-token` 不参与签名。
2. 按 key 的**字典序**排序，拼接为 `k1v1k2v2...`。
3. 把上一步结果接在 **API path** 后面（不含域名、不含 query）：`path + k1v1k2v2...`。Get Authorized Shops 的 path 是 `/authorization/202309/shops`。
4. `content-type` 为 `multipart/form-data` 时不拼接 body；其它请求接上**实际发送的原始 body 字节**。按发出去的字节签名，不要先解析再重新序列化。没有 body 则跳过。
5. 前后各包一次 `app_secret`：`app_secret + path + k1v1k2v2... + body + app_secret`。
6. 以 `app_secret` 为密钥做 **HMAC-SHA256**，输出**小写十六进制**即为 `sign`。

```python
import hashlib, hmac

def tts_sign(app_secret: str, path: str, params: dict, body: str | None = None) -> str:
    raw = "".join(f"{k}{params[k]}" for k in sorted(params) if k not in ("sign", "access_token"))
    sign_string = f"{path}{raw}"
    if body:
        sign_string += body
    msg = f"{app_secret}{sign_string}{app_secret}"
    return hmac.new(app_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
```

> body 必须是即将发出的原始字符串。先签名再改 JSON 的键顺序或空格，签名会失败。官网示例明文：`e59af819cc/authorization/202309/shopsapp_key29a39dtimestamp1623812664e59af819cc`。

### 1.4 响应包络

所有业务接口返回统一结构，**成功判断看 body 的 `code == 0`，不能只看 HTTP 200**：

```json
{ "code": 0, "message": "Success", "request_id": "...", "data": { } }
```

### 1.5 分页

列表接口用 **`page_token`**。`page_size` 与 `page_token` 在 **query**。首页不传 `page_token`，下一页把响应里的 `next_page_token` 原样传回；为空表示没有下一页。翻页时筛选和排序保持不变。时间过滤常成对出现（`xxx_ge` 配 `xxx_lt` 或 `xxx_le`）：只传一边时，另一边按该接口说明默认。时间窗以该接口页为准。

### 1.6 错误码与限流

- 常见错误码：`105005` scope 不足（App 或 token 未授权该接口）；`36004004` auth_code 无效/已使用；`36009033` IP 不在白名单；`36009003` 平台内部错误；完整清单见官网 [Common errors](https://partner.tiktokshop.com/docv2/page/common-errors)。
- 限流同时看 HTTP `429` 和业务码 `36009002`。有 `Retry-After` 就把它当作最短等待；没有则指数退避加抖动。不要立刻高频重试。
- 写接口要自己带幂等（如 Approve Return 的 `idempotency_key`）。收到 429 / `36009002` 时，只有这次写操作具备幂等保护才重试。GET 可以按退避重试。

---

## 二、授权模块（重点）

### 2.1 应用与凭证

在 [Partner Center](https://partner.tiktokshop.com) →「App & Service」创建应用后获得：

| 凭证 | 用途 | 存放要求 |
| --- | --- | --- |
| `app_key` | 标识应用，随每个请求发送 | 可明文 |
| `app_secret` | 生成签名、换取 token | **只存服务端**（密钥管理），禁止进前端/仓库 |
| `service_id` | 拼卖家授权链接 | 可明文 |
| `access_token` / `refresh_token` | 调用业务 API | 落库加密存储，绑定店铺 |

应用类型：**Custom App**（自用/定向分发，本仓库场景）与 **Public App**（上架应用市场）。应用创建后不可删除、只能停用；Redirect URL、Webhook URL 在应用配置里登记。scope 在「Manage API」中申请——只申请当前功能所需 scope，申请过多会拖长审核并降低卖家授权通过率。

### 2.2 Seller 授权流程（本仓库主流程）

1. **生成授权链接**（服务端生成，可绑定 `state` 防 CSRF）：

   ```text
   https://services.tiktokshop.com/open/authorize?service_id={service_id}
   ```
   US 区应用用 `https://services.us.tiktokshop.com/open/authorize`。

2. **卖家打开链接登录授权**：展示应用申请的 scope，卖家点击 Authorize（支持部分授权，实际范围以 `granted_scopes` 为准）。

3. **回调 Redirect URL**：平台带参跳回：

   ```text
   {redirect_url}?code={CODE}&state={state}
   ```
   拒绝授权时 `code=null&error=auth_denied`。回调处理必须：校验 `state` → 读 `code` → 立即换 token。

4. **换 token**：调用 `Get Access Token`（见 2.4.1）。`code` **30 分钟有效、单次使用**，超时/复用报 `36004004`。换 token 必须在**服务端**完成（需要 app_secret）。

5. **拉取店铺信息**：调用 `Get Authorized Shops`（见 2.4.3）拿 `shop_id` 与 `shop_cipher`，与 token 一起落库，建立「店铺 ↔ token ↔ cipher」映射。

### 2.3 Token 生命周期

| 事项 | 说明 |
| --- | --- |
| access_token 有效期 | 约 7 天（以返回的 `access_token_expire_in` Unix 时间戳为准，勿硬编码） |
| refresh_token | 有效期随卖家授权期（以 `refresh_token_expire_in` 为准） |
| 刷新 | 过期前用 Refresh Token 静默续期；刷新可能轮换 refresh_token，**必须持久化新值** |
| 失效兜底 | refresh_token 也过期 → 卖家需重新授权；平台提前 30 天推送 `UPCOMING_AUTHORIZATION_EXPIRATION`，主动解绑推送 `SELLER_DEAUTHORIZATION` |
| 校验 | 每次拿到新 token 后复查 `user_type`、`open_id`、`granted_scopes` |

### 2.4 授权接口详情

#### 2.4.1 Get Access Token

- **做什么**：用授权回调的 `code` 换取 access_token / refresh_token
- **HTTP**：`GET https://auth.tiktok-shops.com/api/v2/token/get`
- **鉴权**：无需 access_token（本接口用 app_secret 鉴权）

**Query 参数**

| 参数 | 必须 | 说明 |
| --- | --- | --- |
| `app_key` | 是 | 应用标识 |
| `app_secret` | 是 | 应用密钥 |
| `auth_code` | 是 | 回调返回的 `code`（单次、30 分钟内） |
| `grant_type` | 是 | 固定值 `authorized_code` |

**响应 `data` 关键字段**

| 字段 | 说明 |
| --- | --- |
| `access_token` | 调用业务 API 的令牌（放 `x-tts-access-token` 头） |
| `access_token_expire_in` | 过期时间（Unix 秒） |
| `refresh_token` / `refresh_token_expire_in` | 刷新令牌及过期时间 |
| `open_id` | 被授权账号标识 |
| `user_type` | 0=卖家 / 1=达人 / 3=服务商，按业务预期校验 |
| `seller_name` | 卖家名称 |
| `granted_scopes` | 实际授权的 scope 列表，须校验覆盖业务最小集 |

**调用示例**

```bash
curl -G "https://auth.tiktok-shops.com/api/v2/token/get" \
  --data-urlencode "app_key=YOUR_APP_KEY" \
  --data-urlencode "app_secret=YOUR_APP_SECRET" \
  --data-urlencode "auth_code=CODE_FROM_CALLBACK" \
  --data-urlencode "grant_type=authorized_code"
# 成功判断：响应 body.code == 0
```

#### 2.4.2 Refresh Token

- **做什么**：用 refresh_token 换新 access_token
- **HTTP**：`GET https://auth.tiktok-shops.com/api/v2/token/refresh`

**Query 参数**

| 参数 | 必须 | 说明 |
| --- | --- | --- |
| `app_key` / `app_secret` | 是 | 同上 |
| `refresh_token` | 是 | 当前有效的 refresh_token |
| `grant_type` | 是 | 固定值 `refresh_token` |

**响应**：字段同 2.4.1；**若返回了新的 refresh_token 必须立即落库替换**。

```bash
curl -G "https://auth.tiktok-shops.com/api/v2/token/refresh" \
  --data-urlencode "app_key=YOUR_APP_KEY" \
  --data-urlencode "app_secret=YOUR_APP_SECRET" \
  --data-urlencode "refresh_token=YOUR_REFRESH_TOKEN" \
  --data-urlencode "grant_type=refresh_token"
```

#### 2.4.3 Get Authorized Shops

- **做什么**：查询该 access_token 已授权的店铺列表，拿 `shop_id` 与 **`shop_cipher`**
- **HTTP**：`GET /authorization/202309/shops`（业务域）
- **关联**：所有店铺级接口的 `shop_cipher` 均来源于此；多店编排按本接口结果建映射

**Query**：`app_key`、`timestamp`、`sign`。access token 放请求头 `x-tts-access-token`。

**响应 `data.shops[]`**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 店铺内部 ID |
| `name` | string | 店铺名 |
| `region` | string | 区域，如 `GB` |
| `seller_type` | string | `CROSS_BORDER`（多国多店）或 `LOCAL`（单店） |
| `cipher` | string | **shop_cipher**。店铺级接口的 query 原样传入 |
| `code` | string | Seller Center 上的店铺代码 |

仓库 ID 不在这个接口里，用 `GET /logistics/202309/warehouses`。

```bash
TS=$(date +%s)
curl -G "https://open-api.tiktokglobalshop.com/authorization/202309/shops" \
  -H "x-tts-access-token: $TOKEN" \
  --data-urlencode "app_key=KEY" --data-urlencode "timestamp=$TS" \
  --data-urlencode "sign=$SIGN"
```

### 2.5 编码规范（本仓库约定）

1. **落库字段**（对应 `app/services/tiktok_oauth.py` 预留）：`store_id` ↔ `access_token`、`refresh_token`、`access_token_expire_in`、`refresh_token_expire_in`、`open_id`、`user_type`、`granted_scopes`、`shop_id`、`shop_cipher`、`seller_name`、`region`；token 建议加密存储。
2. **刷新任务**：定时任务扫描「距过期 < 24h」的 token 批量刷新；刷新失败立即告警，refresh 失效的店铺标记「需重新授权」并在管理端提示。
3. **state 规范**：服务端生成随机不可预测值、绑定授权会话、单次使用、回调严格校验；state 中禁止携带敏感数据。
4. **code 处理**：回调拿到 code 后同步换 token（即使走异步队列也不得超过 30 分钟）；换失败按错误码区分「可重试」与「需重新授权」。
5. **scope 最小化**：换 token 后校验 `granted_scopes` 覆盖业务最小集；缺 scope 引导卖家重新授权，而不是反复撞 105005。调接口报 105005 时先查 App scope、再查 token 的 granted_scopes。
6. **多店编排**：所有店铺级请求封装统一 client：注入 `app_key/timestamp/sign` + `x-tts-access-token` 头 + `shop_cipher` 参数；按 store_id 路由 token，禁止串店。
7. **审计日志**：授权、刷新、解绑事件全部落日志（含平台 request_id），便于排查与合规。

### 2.6 授权相关 Webhook

| Topic | 说明 |
| --- | --- |
| `SELLER_DEAUTHORIZATION` | 卖家主动解绑，立即停用该店 token 并告警 |
| `UPCOMING_AUTHORIZATION_EXPIRATION` | 到期前 30 天开始推送，之后每天 0:00 再推，直到重新授权 |

---

## 三、业务模块与接口详情

> 通用约定：以下所有接口 Domain 为 `https://open-api.tiktokglobalshop.com`；query 必带 `app_key/timestamp/sign`，授权接口加 `x-tts-access-token` 头，店铺级接口按详情页要求加 `shop_cipher`（多店/跨区场景一律带上）。示例中的签名参数省略，实际调用按 1.3 补齐。scope 键名以 Partner Center「Manage API」实际标注为准。

### 3.1 商品 API（Product）

- **模块说明**：类目/属性/规则 → 创建/编辑商品 → 库存/状态管理。审核状态看 `audit.status` 的完整枚举。
- **模块关联**：创建前取类目、规则、属性；仓库 ID 来自 `GET /logistics/202309/warehouses`。图片先走 Upload Product Image，把返回的 URI 填进 `main_images[].uri`。
- **编辑**：全量编辑用 Edit Product（202509）。改完内容会重新送审；只改 `price` / `inventory` 不用重审，会马上生效。Webhook 不是最终事实，状态以 Get Product 为准。美国、欧盟、东南亚的类目接口必须传 `category_version=v2`（7 级类目树），其它区域默认 `v1`（3 级）。

| 接口 | HTTP | path |
| --- | --- | --- |
| Get Categories | GET | `/product/202309/categories` |
| Recommend Category | POST | `/product/202309/categories/recommend` |
| Get Category Rules | GET | `/product/202309/categories/{category_id}/rules` |
| Get Attributes | GET | `/product/202309/categories/{category_id}/attributes` |
| Create Product | POST | `/product/202309/products` |
| Edit Product | PUT | `/product/202509/products/{product_id}` |
| Partial Edit Product | POST | `/product/202509/products/{product_id}/partial_edit` |
| Get Product | GET | `/product/202309/products/{product_id}` |
| Search Products | POST | `/product/202502/products/search` |
| Update Inventory | POST | `/product/202309/products/{product_id}/inventory/update` |
| Deactivate / Activate | POST | `/product/202309/products/deactivate`、`/product/202309/products/activate` |

#### 3.1.1 Get Categories

- **做什么**：拉取当前店铺可用类目。类目经常变，不要长期缓存后再拿去发品。
- **关联**：响应 `categories[].id` 用作后续 rules / attributes / create 的 `category_id`。根类目的 `parent_id` 是 `"0"`。只有 `is_leaf=true` 且权限允许的类目才能创建商品。

| Query 参数 | 必须 | 说明 |
| --- | --- | --- |
| `category_version` | 视区域 | 美国、欧盟、东南亚必须 `v2`；其它区域默认 `v1` |
| `locale` | 否 | BCP-47，如 `en-US`；不传用店铺默认语言 |
| `keyword` | 否 | 按 `local_name` 过滤 |
| `listing_platform` | 否 | `TIKTOK_SHOP`（默认）或 `TOKOPEDIA`。印尼双平台上架时两边各查一次，取交集 |
| `include_prohibited_categories` | 否 | 仅 BR、MX、EU、SEA。`true` 时带上禁止类目 |

`permission_statuses`：`AVAILABLE`、`INVITE_ONLY`（受限，需资质申请）、`NON_MAIN_CATEGORY`、`PROHIBITED`。

```bash
curl -G "https://open-api.tiktokglobalshop.com/product/202309/categories" \
  -H "x-tts-access-token: $TOKEN" \
  --data-urlencode "app_key=$KEY" --data-urlencode "timestamp=$TS" \
  --data-urlencode "category_version=v2" --data-urlencode "sign=$SIGN"
```

#### 3.1.2 Recommend Category

- **做什么**：按商品标题/描述/图片推荐 TikTok 类目（对应敦煌网发布前置选类目的自动化）
- **关联**：推荐结果需运营确认后再进入 rules/attributes/create

**Body 关键参数**：`product_title`（必填）、`description`、图片相关字段。美国、欧盟、东南亚同样要传 `category_version=v2`。文案语言必须与目标市场一致。

#### 3.1.3 Get Category Rules / Get Attributes

- **做什么**：拉取叶子类目的**上架规则**（认证、包装尺寸、尺码表是否必填等）与**属性表**（必填/选填属性及候选值）
- **业务逻辑**：建品模板由此生成；**落库存 TikTok 的 attribute_id，不要只存属性名**（名称随市场/语言可变）。特定类目（如假发、3C）有强制认证与材质属性，缺失审核必拒。

#### 3.1.4 Create Product

- **做什么**：发布本地店商品。`save_mode=LISTING`（默认）直接送审上架；`save_mode=AS_DRAFT` 存草稿。该页要求美国、东南亚店铺传 `category_version=v2`。美国卖家也可在 `INVITE_ONLY` 类目建品，但仍需在 Seller Center 资质中心另申请，否则审核通过后状态会停在 `PENDING` / `audit.status=PRE_APPROVED`。
- **关联**：`category_id` ← Categories 的叶子类目；`warehouse_id` ← Get Warehouse List；`main_images[].uri` ← Upload Product Image（`use_case=MAIN_IMAGE`）
- **响应**：`product_id`、`sku_id` 列表；提交后进入审核，状态以 Get Product 为准

**Body 关键参数（摘）**

| 参数 | 必须 | 说明 |
| --- | --- | --- |
| `title` | 是 | 商品标题 |
| `description` | 是 | HTML 描述 |
| `category_id` | 是 | 叶子类目 |
| `brand_id` | 视类目 | 品牌（部分类目必填） |
| `main_images[]` | 是 | 主图，`{ "uri": "..." }` |
| `skus[]` | 是 | SKU：`seller_sku`、`price{amount,currency}`、`inventory[{warehouse_id,quantity}]`、销售属性 |
| `package_dimensions` 等 | 视规则 | 由 Category Rules 指示 |

```bash
curl -X POST "https://open-api.tiktokglobalshop.com/product/202309/products?app_key=$KEY&timestamp=$TS&shop_cipher=$CIPHER&sign=$SIGN" \
  -H "content-type: application/json" -H "x-tts-access-token: $TOKEN" \
  -d '{
    "save_mode": "LISTING",
    "title": "Example cotton T-shirt",
    "description": "<p>HTML description</p>",
    "category_id": "123456",
    "main_images": [{ "uri": "tos-image-uri" }],
    "skus": [{
      "seller_sku": "TSHIRT-BLACK-M",
      "price": { "amount": "19.99", "currency": "USD" },
      "inventory": [{ "warehouse_id": "7000714532876273410", "quantity": 100 }]
    }]
  }'
```

#### 3.1.5 Edit / Partial Edit / Get Product

- **Edit（PUT `/product/202509/products/{product_id}`）**：改描述、品牌、图片等。商品不能处于 `FREEZE` 或 `DELETED`。内容变更会生成 v2 重新送审；审核不通过则线上仍保持 v1。`price`、`inventory` 的修改不重审，立即生效。
- **Partial Edit（POST `/product/202509/products/{product_id}/partial_edit`）**：只提交要改的字段，审核规则与 Edit 相同，同样可以直接改 `price` / `inventory`。库存数量也可以单独走 Update Inventory。
- **Get（GET `/product/202309/products/{product_id}`）**：权威状态。`audit.status`：`NONE`（未送审、草稿、冻结或下架）、`AUDITING`、`FAILED`、`PRE_APPROVED`（审核过了但前置条件未满足）、`APPROVED`。

```bash
curl -X PUT "https://open-api.tiktokglobalshop.com/product/202509/products/{product_id}?app_key=$KEY&timestamp=$TS&shop_cipher=$CIPHER&sign=$SIGN" \
  -H "content-type: application/json" -H "x-tts-access-token: $TOKEN" \
  -d '{ ...全量商品对象（Get 后合并修改）... }'
```

#### 3.1.6 Search Products

- **做什么**：按条件查店内商品的关键字段。要全量详情再拿返回的 product ID 调 Get Product。
- **HTTP**：`POST /product/202502/products/search`

**Query**：`page_size`（必填，1–100）、`page_token`（首页不传）。

**Body**：`status`（单个 string，默认 `ALL`。取值 `ALL` / `DRAFT` / `PENDING` / `FAILED` / `ACTIVATE` / `SELLER_DEACTIVATED` / `PLATFORM_DEACTIVATED` / `FREEZE` / `DELETED`）、`seller_skus`、`create_time_ge` / `create_time_le`、`update_time_ge` / `update_time_le`。`status` 只过滤商品基础版本。响应有 `products[]` 与 `next_page_token`。

#### 3.1.7 Update Inventory

- **做什么**：按 SKU×仓库 更新可售库存（对应敦煌网 `dh.item.update.stock` 系列）
- **业务逻辑**：多渠道共用库存时由此接口做扣减同步；先 Get Product 确认 sku_id 与仓库映射。

```bash
curl -X POST "https://open-api.tiktokglobalshop.com/product/202309/products/{product_id}/inventory/update?app_key=$KEY&timestamp=$TS&shop_cipher=$CIPHER&sign=$SIGN" \
  -H "content-type: application/json" -H "x-tts-access-token: $TOKEN" \
  -d '{ "skus": [{ "id": "1730", "inventory": [{ "warehouse_id": "7000714532876273410", "quantity": 12 }] }] }'
```

### 3.2 订单 API（Order）

- **模块说明**：订单检索与详情。状态取值：`UNPAID`、`ON_HOLD`（支付后的犹豫期，买家可不经卖家同意取消，此状态不能履约）、`AWAITING_SHIPMENT`、`PARTIALLY_SHIPPING`、`AWAITING_COLLECTION`、`IN_TRANSIT`、`DELIVERED`、`COMPLETED`、`CANCELLED`。
- **模块关联**：状态变化主要靠 Webhook `ORDER_STATUS_CHANGE` 实时感知（见 3.7），API 轮询兜底；发货走 Fulfillment（3.3）；退款/取消走 Return & Refund（3.5）。

| 接口 | HTTP | path |
| --- | --- | --- |
| Get Order List | POST | `/order/202309/orders/search` |
| Get Order Detail | GET | `/order/202507/orders` |

#### 3.2.1 Get Order List（orders/search）

- **做什么**：按时间/状态分页拉订单列表（简略信息），对应敦煌网 `dh.order.list.get`
- **业务逻辑**：增量同步以 `update_time_ge/lt` 滚动拉取，配合 Webhook 去重；显式固定时间窗保证翻页稳定

**Body 关键参数（摘）**

| 参数 | 位置 | 必须 | 说明 |
| --- | --- | --- | --- |
| `page_size` | query | 是 | 默认 20，范围 1–100 |
| `page_token` | query | 否 | 上一页的 `next_page_token` |
| `sort_field` | query | 否 | `create_time`（默认）或 `update_time` |
| `sort_order` | query | 否 | `ASC` / `DESC`，默认 `DESC` |
| `order_status` | body | 否 | **单个 string**，不是数组。取值见模块说明 |
| `create_time_ge` / `create_time_lt` | body | 否 | 只传一边时，缺的 `lt` 默认现在，缺的 `ge` 默认店铺最早时间 |
| `update_time_ge` / `update_time_lt` | body | 否 | 规则同上。更新时间可能因为数据刷新超出所选窗口 |

```bash
curl -X POST "https://open-api.tiktokglobalshop.com/order/202309/orders/search?app_key=$KEY&timestamp=$TS&shop_cipher=$CIPHER&page_size=50&sign=$SIGN" \
  -H "content-type: application/json" -H "x-tts-access-token: $TOKEN" \
  -d '{ "order_status": "AWAITING_SHIPMENT", "update_time_ge": 1791222188, "update_time_lt": 1791229388 }'
```

#### 3.2.2 Get Order Detail（202507）

- **做什么**：按订单 ID 查详情（状态、收件地址、支付、价格税费、包裹），对应敦煌网 `dh.order.get`
- **业务逻辑**：query 参数名是 `ids`，逗号分隔，最多 50 个。

```bash
curl -G "https://open-api.tiktokglobalshop.com/order/202507/orders" \
  -H "x-tts-access-token: $TOKEN" \
  --data-urlencode "app_key=$KEY" --data-urlencode "timestamp=$TS" \
  --data-urlencode "shop_cipher=$CIPHER" --data-urlencode "sign=$SIGN" \
  --data-urlencode "ids=576461413038785752,576461413038785753"
```

### 3.3 履约 API（Fulfillment）

- **模块说明**：包裹维度发货——查询待发货包裹、申报发货（运单号+物流商）、更新物流信息、面单/报关文档。对应敦煌网 `dh.order.delivery.save` + 在线发货。
- **模块关联**：`shipping_provider_id` ← `GET /logistics/202309/delivery_options/{delivery_option_id}/shipping_providers`；包裹变化推送 `PACKAGE_UPDATE`。

| 接口 | HTTP | path |
| --- | --- | --- |
| Search Packages | POST | `/fulfillment/202309/packages/search` |
| Ship Package | POST | `/fulfillment/202309/packages/{package_id}/ship` |
| Update Shipping Info | POST | `/fulfillment/202309/packages/{package_id}/shipping_info/update` |
| Get Package Shipping Document | GET | `/fulfillment/202309/packages/{package_id}/shipping_documents` |

#### 3.3.1 Search Packages

- **做什么**：按创建/更新时间和 `package_status` 分页查包裹
- **Query**：`page_size` 必填（1–50）、`page_token`、`sort_field`（`create_time` / `update_time` / `order_pay_time`）、`sort_order`、跨境店带 `shop_cipher`
- **Body**：`create_time_ge` / `create_time_lt`、`update_time_ge` / `update_time_lt`、`package_status`（`TO_FULFILL` / `PROCESSING` / `FULFILLING` / `COMPLETED` / `CANCELLED`）
- **响应**：`packages[]`（`id`、关联 `orders`、`status`）与 `next_page_token`

#### 3.3.2 Ship Package（申报发货）

- **做什么**：对卖家自发货（3PL）包裹申报发货（Tracking + 物流商），对应敦煌网 `delivery.save`
- **业务逻辑**：仅 `AWAITING_SHIPMENT` 状态可发；SLA 内未发货会被平台处罚/接管，需监控滞留订单。

平台物流用 `handover_method`（`PICKUP` / `DROP_OFF`）和 `pickup_slot`。卖家自发（`delivery_option=SEND_BY_SELLER`）把 `tracking_number`、`shipping_provider_id` 放在 `self_shipment` 里，这两项必填。

```bash
curl -X POST "https://open-api.tiktokglobalshop.com/fulfillment/202309/packages/{package_id}/ship?app_key=$KEY&timestamp=$TS&shop_cipher=$CIPHER&sign=$SIGN" \
  -H "content-type: application/json" -H "x-tts-access-token: $TOKEN" \
  -d '{ "self_shipment": { "tracking_number": "1Z999AA10123456784", "shipping_provider_id": "6617675021119438849" } }'
```

#### 3.3.3 Update Shipping Info

- **做什么**：发货后修正运单号/物流商（发错单补救），路径与 Ship 同级。

### 3.4 物流 API（Logistics）

| 接口 | HTTP | path | 说明 |
| --- | --- | --- | --- |
| Get Warehouse List | GET | `/logistics/202309/warehouses` | 仓库列表，产出 `warehouse_id` |
| Get Shipping Providers | GET | `/logistics/202309/delivery_options/{delivery_option_id}/shipping_providers` | 某个配送方式下的承运商。TikTok 履约的配送方式没有可选承运商，调用会报错 |
| Check Shipping Template Existence | GET | `/logistics/202606/seller_template/template_exist` | query：`biz_warehouse_id` 必填，`shop_id` 可选。该页仍把 `access_token` 写在 query |

#### 3.4.1 Get Warehouse List

- **关联**：响应中的仓库 ID → Create Product 的 `inventory[].warehouse_id`。Get Authorized Shops 不返回仓库。

```bash
curl -G "https://open-api.tiktokglobalshop.com/logistics/202309/warehouses" \
  -H "x-tts-access-token: $TOKEN" \
  --data-urlencode "app_key=$KEY" --data-urlencode "timestamp=$TS" \
  --data-urlencode "shop_cipher=$CIPHER" --data-urlencode "sign=$SIGN"
```

#### 3.4.2 Get Shipping Providers

- **做什么**：按 `delivery_option_id` 查承运商，得到 `shipping_provider_id`
- **关联**：卖家自发货前先调。path 带 `delivery_option_id`。

### 3.5 售后 API（Return & Refund）

- **模块说明**：退货退款审批、买家取消审批、RMA/换货。对应敦煌网 `applymoney.* / dispute*`。
- **模块关联**：状态推送 `RETURN_STATUS_CHANGE`、`CANCELLATION_STATUS_CHANGE`；换货（EXCHANGE）会产生 `rma_id` 并自动创建 0 元换货 outbound 订单（订单接口标记 `is_exchange_order`）。
- **业务逻辑**：`return_type` 为 `REFUND`、`RETURN_AND_REFUND`、`REPLACEMENT`、`EXCHANGE`。

| 接口 | HTTP | path |
| --- | --- | --- |
| Search Returns | POST | `/return_refund/202602/returns/search` |
| Approve Return | POST | `/return_refund/202309/returns/{return_id}/approve` |
| Reject Return | POST | `/return_refund/202606/returns/{return_id}/reject` |
| Get Decision Eligibility | GET | `/return_refund/202601/decision_eligibility` |
| Approve Cancellation | POST | `/return_refund/202309/cancellations/{cancel_id}/approve` |
| Reject Cancellation | POST | `/return_refund/202309/cancellations/{cancel_id}/reject` |

#### 3.5.1 Search Returns

- **Query**：`page_size`（默认 10，范围 10–50）、`page_token`、`sort_field`（`create_time` / `update_time`）、`sort_order`
- **Body**：`return_ids`、`order_ids`、`return_types`、`return_status`（均为数组）、`create_time_ge` / `create_time_le`（只传一边时，缺的上界默认现在，缺的下界默认店铺最早时间）
- **响应**：`return_orders[]`，含 `return_id`、`order_id`、`return_type`、`return_status`

#### 3.5.2 Approve / Reject Return

- **业务逻辑**：先用 Get Decision Eligibility 看当前单允许哪些 `decision`。query 是 `return_or_cancel_id`（必填）和可选的 `check_decisions`，不是路径里的 `{return_id}`。Approve 可选 query `idempotency_key`。Reject 走 202606，原因和图片按该页必填项提交。

`decision` 取值：`APPROVE_REFUND`、`APPROVE_RETURN`、`APPROVE_RECEIVED_PACKAGE`、`APPROVE_REPLACEMENT`、`ISSUE_REPLACEMENT_REFUND`、`OFFER_PARTIAL_REFUND`、`DIRECT_REFUND`。`buyer_keep_item` 只在 `APPROVE_RETURN` 时有效。`OFFER_PARTIAL_REFUND` 时 `partial_refund.currency` 与 `partial_refund.amount` 必填。

```bash
curl -X POST "https://open-api.tiktokglobalshop.com/return_refund/202309/returns/{return_id}/approve?app_key=$KEY&timestamp=$TS&shop_cipher=$CIPHER&sign=$SIGN" \
  -H "content-type: application/json" -H "x-tts-access-token: $TOKEN" \
  -d '{ "decision": "APPROVE_RETURN" }'
```

### 3.6 财务 API（Finance）

- **模块说明**：结算账单、货款流水。对应敦煌网较弱的对账域。
- **模块关联**：与订单/售后状态联动核对（订单结算状态受退货期影响）。

| 接口 | HTTP | path | 说明 |
| --- | --- | --- | --- |
| Get Statements | GET | `/finance/202309/statements` | 结算单列表 |
| Get Payments | GET | `/finance/202605/payments` | 自动付款记录。东南亚不可用。`sort_field` 必填，只支持 `create_time` |
| Get Transactions by Statement | GET | `/finance/202501/statements/{statement_id}/statement_transactions` | 结算单内交易明细 |
| Get Transactions by Order | GET | `/finance/202501/orders/{order_id}/statement_transactions` | 订单维度交易明细 |

```bash
curl -G "https://open-api.tiktokglobalshop.com/finance/202605/payments" \
  -H "x-tts-access-token: $TOKEN" \
  --data-urlencode "app_key=$KEY" --data-urlencode "timestamp=$TS" \
  --data-urlencode "shop_cipher=$CIPHER" --data-urlencode "sort_field=create_time" \
  --data-urlencode "page_size=20" --data-urlencode "sign=$SIGN"
```

### 3.7 事件 API（Webhook）

- **模块说明**：用 Update Shop Webhook 给一家店登记 HTTPS 地址和单个 `event_type`。Body 是 `address` 与 `event_type`。
- **验签**：`Authorization` 头是小写十六进制 HMAC-SHA256，没有 `Bearer`。`signature_base_string = app_key + raw_request_body`，密钥是 `app_secret`。必须用收到的原始 body，不能先解析再重新序列化。签名不对就拒绝处理。
- **响应要求**：尽快返回 2xx，业务异步处理。

| 接口 | HTTP | path | 说明 |
| --- | --- | --- | --- |
| Get Shop Webhooks | GET | `/event/202309/webhooks` | 查看该店已订的 topic 和回调地址 |
| Update Shop Webhook | PUT | `/event/202309/webhooks` | Body：`address`、`event_type`（单个） |
| Delete Shop Webhook | DELETE | `/event/202309/webhooks` | 取消某个 topic |

**常用 Topic 一览**

| Topic | 触发 | 建议处理 |
| --- | --- | --- |
| `ORDER_STATUS_CHANGE` | 订单状态流转 | 更新订单状态；AWAITING_SHIPMENT 进入待发货队列 |
| `PACKAGE_UPDATE` | 包裹创建/合并/拆分/状态 | 同步包裹，驱动履约 |
| `RETURN_STATUS_CHANGE` | 退货退款状态 | 待审批售后进审批队列 |
| `CANCELLATION_STATUS_CHANGE` | 买家取消请求 | 审批窗口内决策 approve/reject |
| `PRODUCT_UPDATE` / 商品创建/审核类 | 商品状态变化 | 以 Get Product 复核权威状态 |
| `SELLER_DEAUTHORIZATION` / `UPCOMING_AUTHORIZATION_EXPIRATION` | 授权变化 | 见 2.6 |

```python
import hashlib, hmac

def verify_tiktok_webhook(app_key: str, app_secret: str, raw: bytes, authorization: str) -> bool:
    base = app_key.encode() + raw
    digest = hmac.new(app_secret.encode(), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, authorization.strip())
```

### 3.8 其他模块（按需展开）

| 模块 | 内容 | 说明 |
| --- | --- | --- |
| Promotion | 活动、优惠券（含 GWP 赠品/免费试用） | 营销自动化 |
| Affiliate | 达人带货：seller/partner/creator 三个视角（合作、样品、佣金单、达人内容） | TikTok 特色；creator 授权独立（见 0.2） |
| Analytics | 店铺/商品/SKU/视频/直播表现（Compass 数据） | 对应敦煌网 `wis.*` |
| FBT | TikTok 官方仓：入库单、库存、仓库 | 用官方仓履约时接入 |
| Customer Service | 买家会话、消息、客服配置 | 站内信对应物 |
| Seller / Shop | 已授权店铺、卖家权限、店铺分组 | 多店管理辅助 |
| Tools | 大文件断点续传上传 | 商品视频/大图上传前置 |

---

## 四、典型业务联动链路

### 4.1 授权与多店铺初始化

```mermaid
flowchart TD
    A["生成授权链接 service_id"] --> B["卖家授权 → 回调 code + state"]
    B --> C["token/get 换 access_token"]
    C --> D["authorization/202309/shops<br/>拿 shops[].id / cipher"]
    D --> E["落库店铺映射 + 启动刷新任务"]
```

### 4.2 选品发布

```mermaid
flowchart TD
    A["categories 类目树 / recommend"] --> B["rules + attributes 建品模板"]
    B --> C["媒体上传获得 uri"]
    C --> D["logistics/202309/warehouses"]
    D --> E["Create Product"]
    E --> F["Get Product 看 audit.status"]
    F --> G["APPROVED → 上架可售"]
```

- 要点：`attribute_id` 必须落库存；换货/预售/拍卖等特殊 Listing 走专用字段（见官方 Product Solution Guide）；编辑必须 Get 全量合并后 PUT。

### 4.3 订单履约

```mermaid
flowchart TD
    A["webhook ORDER_STATUS_CHANGE<br/>或 orders/search 轮询"] --> B["order/202507/orders 详情"]
    B --> C["packages/search 待发货包裹"]
    C --> D["delivery_options/{id}/shipping_providers"]
    D --> E["package/ship 申报发货"]
    E --> F["trackinfo / PACKAGE_UPDATE 跟踪"]
    B --> G["cancellation / return 审批"]
```

- 要点：US 区 4PL 订单由平台履约，地址可能脱敏，无需也不应自己发货；SLA 滞留监控 + 审批时限是两个必须的定时任务。

### 4.4 对账

`GET /finance/202309/statements` 拉结算单，明细走 `GET /finance/202501/statements/{statement_id}/statement_transactions` 或按订单的 `GET /finance/202501/orders/{order_id}/statement_transactions`。付款记录用 `GET /finance/202605/payments`（东南亚不可用）。达人佣金走 Affiliate 订单接口。

---

## 五、附录

### 5.1 错误码（联调高频）

| code | 含义 | 处理 |
| --- | --- | --- |
| 0 | 成功 | — |
| 105005 | scope 未授权 | 检查 App scope 与 token granted_scopes，引导重新授权 |
| 36004004 | auth_code 无效/已使用/过期 | 重新发起授权，code 单次 30 分钟 |
| 36009033 | 请求 IP 不在应用白名单 | 控制台更新 IP 白名单 |
| 36009003 | 平台内部错误 | 退避重试；持续失败提工单 |
| 36009004 | timestamp 超出有效窗口 | 用秒级 Unix 时间，窗口为当前时间前 5 分钟到后 30 秒 |
| 36009002 | 限流（HTTP 同时可能是 429） | 按 `Retry-After` 退避；写操作只在有幂等键时重试 |

### 5.2 版本对照（本文收录版本）

| 模块 | 版本 | 备注 |
| --- | --- | --- |
| authorization | 202309 | shops |
| product | 202309 创建/库存/上下架；202502 搜索；202509 编辑与局部编辑 | |
| order | 202309 搜索；202507 详情（query `ids`） | |
| fulfillment | 202309 | ship、面单 `GET .../packages/{package_id}/shipping_documents` |
| logistics | 202309 仓库与承运商；202606 `seller_template/template_exist` | |
| return_refund | 202309 同意退货与取消审批；202601 决策资格；202602 搜索；202606 拒绝退货 | |
| finance | 202309 statements；202501 statement_transactions；202605 payments | |
| event | 202309 | `address` + 单个 `event_type` |

> 官方持续发布新日期版本（如 order 202507、logistics 202606、affiliate 202603）；升级版本时先读对应 Changelog，旧版本在废弃期后下线。

### 5.3 与敦煌网手册的概念对照

| 概念 | 敦煌网 | TikTok Shop |
| --- | --- | --- |
| 鉴权 | method + v + timestamp + access_token | app_key + timestamp + sign + x-tts-access-token + shop_cipher |
| 版本 | `dh.xxx.get$2.0` | `/{module}/{202309}/{resource}` |
| 商品发布 | `dh.item.add` | `POST /product/202309/products` |
| 订单列表 | `dh.order.list.get` | `POST /order/202309/orders/search` |
| 申报发货 | `dh.order.delivery.save` | `POST /fulfillment/202309/packages/{id}/ship` |
| 数据看板 | `dh.wis.*` | Analytics 模块 |
| 事件推送 | 无（纯拉） | Webhook（验签 + 2xx 确认） |

### 5.4 维护说明

- 全量英文稿在 `tts_API.md`，由 `script/scrape_tts_open_docs.py` 抓取、`script/generate_tts_api_md.py` 生成。本手册只保留联调用的路径、必填项和枚举。字段以 `tts_API.md` 对应接口页为准，不要补文档里没有的取值。
- 文档站更新后先重跑抓取再改本手册。同一能力以抓取稿里带日期版本的现行 path 为准。

### 5.5 参考资料

- 开发者指南总览：<https://partner.tiktokshop.com/docv2/page/tts-developer-guide>
- 签名：<https://partner.tiktokshop.com/docv2/page/sign-your-api-request>
- 公共参数/公共错误/限流：`common-parameters` / `common-errors` / `rate-limits`
- 授权指南：<https://partner.tiktokshop.com/docv2/page/creator-authorization-guide>（含 seller/creator 流程对比）
- Product Solution Guide：<https://partner.tiktokshop.com/docv2/page/10lt0djm>
- Return & Exchange Solution Guide：<https://partner.tiktokshop.com/docv2/page/71ztxsw4>
