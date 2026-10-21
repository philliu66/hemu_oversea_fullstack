# 管理端对接说明（阶段 A + B）

扩展**不会**在打开管理端时全局检测是否安装。仅当业务页在用户点击按钮等时机主动 `postMessage` 时，注入的 content script 才会转发并回复。

## 加载扩展（开发）

```bash
cd hemu_oversea_browser_extension
npm install
npm run dev
```

Chrome → 扩展程序 → 开发者模式 →「加载已解压的扩展程序」→ 选择 `.output/chrome-mv3`（以 WXT 实际输出目录为准）。

管理端需跑在 `http://localhost` / `http://127.0.0.1` 任意端口（已匹配）。敦煌采集页需能访问 `*.dhgate.com`。

## 按需 PING（检测是否安装）

在「开始采集 / 单次补充」等按钮的点击处理里调用（管理端已封装 `pingExtension` / `requestExtension`）。

未安装或 content script 未注入时：短超时后视为失败，提示用户安装采集插件。

## 配置结构（`config.mission_hotsale_dh_config`）

```json
{
  "collectConfig": {
    "openUrl": "https://seller.dhgate.com/.../toprofileNew.do",
    "watchApiUrl": "https://seller.dhgate.com/.../productrankNew.do",
    "alertTip": "请在本页筛选/翻页以加载热卖列表，确认后点击完成采集"
  },
  "fillConfig": {
    "alertTip": "请在商品详情页完成补充采集"
  }
}
```

| 子对象 | 用途 |
| --- | --- |
| `collectConfig` | **列表采集**（第一次，部分信息） |
| `fillConfig` | **单次补充**（详细信息）；管理端会再附加当前商品 `openUrl` |

## 扩展 START 模式

| mode | 场景 | payload |
| --- | --- | --- |
| `list_collect` | 工具栏「开始采集」 | `{ mode, collectConfig }`（嵌套，勿扁平展开） |
| `detail_fill` | 行内「单次补充」 | `{ mode, openUrl: 商品链接, fillConfig }`（嵌套，勿扁平展开） |

同名字段（如 `alertTip`）分属 `collectConfig` / `fillConfig`，必须嵌套传递，禁止 `...collectConfig` / `...fillConfig` 摊平到 payload 顶层。

### 列表采集流程

```text
1. 管理端：PING → 拉配置 → START list_collect + collectConfig
2. 扩展：按 openUrl 开新标签；页顶展示 alertTip；监听 watchApiUrl
3. 用户点「完成采集」→ 最新响应 SYNC_CONFIRM 回管理端 → 入库
```

### 单次补充流程（业务逻辑预留）

```text
1. 管理端：PING → 拉配置 → START detail_fill + fillConfig + 商品 openUrl（无二次确认）
2. 扩展：打开商品页；页顶展示 alertTip（样式同列表采集）
3. 「完成补充」目前仅占位关页回管理端；后续再接 FILL_CONFIRM
```

### 消息约定

| 字段 | 页面 → 扩展 | 扩展 → 页面 |
| --- | --- | --- |
| `source` | `hemu-admin-page` | `hemu-browser-ext` |
| `version` | `1` | `1` |
| 安装检测 | `action: 'PING'` | `action: 'PONG'` |
| 开始任务 | `businessType: 'hotsell'`, `action: 'START'`, `payload.mode` | `STATUS` |
| 列表确认回传 | （敦煌页「完成采集」） | `action: 'SYNC_CONFIRM'` |
| 补充回传（预留） | （敦煌页「完成补充」） | `action: 'FILL_CONFIRM'` |
