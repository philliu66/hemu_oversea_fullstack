# hemu_oversea_browser_extension

[English](./README.md) | 简体中文

HeMu 跨境系统的 **浏览器扩展平台**：运行在用户本机浏览器中，按管理端下发的业务类型执行采集、拦截、回传等能力。扩展**不直连业务数据库**；结果经约定协议回传已登录的管理端页面，由管理端调用后端 API 完成持久化。

本工程按「平台内核 + 业务 Feature」组织，便于后续接入多种场景，而不仅限于单一采集任务。

---

## 平台定位

| 角色 | 职责 |
| --- | --- |
| 管理端（`hemu_oversea_fastapiadmin`） | 检测扩展、发起业务指令、接收回传、调后端入库、刷新列表 |
| 本扩展 | 安装于浏览器；按 `businessType` / `action` / `payload` 路由到对应 Feature 执行 |
| 后端（`hemu_oversea_fastapi`） | 业务 API 与数据库（扩展不直接访问） |

**通信要点**：管理端页与第三方站点（如敦煌）不同源，不能互相直接 `postMessage`。统一经扩展 Background 做消息总线，再回传到发起指令的管理端 Tab。

```text
管理端页面
  ↔ content script（管理端）
  ↔ background（路由 / 会话 / 任务队列）
  ↔ content script + 站点能力（如敦煌）
  ↔ 目标网站页面
```

管理端通过统一信封传参，例如：`businessType`（业务类型）、`action`（动作）、`payload`（业务参数）。扩展根据类型做不同响应；未知类型返回明确错误，便于提示升级扩展。

---

## 已规划 / 首期业务：敦煌热卖品数据采集（`hotsell`）

首个接入的 Feature，用于在用户浏览器中采集敦煌网前台热卖列表与商品详情（与官方卖家 Data API / `dh.wis.*` 店铺经营数据不是同一条链路）。

### 主要能力

- **安装检测（按需）**：仅在具体业务按钮（如「开始采集」）点击时由页面发 `PING` 检测；**不做管理端全局检测**。未安装则提示先安装（引导方式后续细化）。
- **列表采集 `list_collect`（阶段 B）**：下发 `collectConfig`（`openUrl` / `watchApiUrl` / `alertTip`）；扩展开页、监听、确认后 `SYNC_CONFIRM` 回传入库。
- **单次补充 `detail_fill`**：下发 `fillConfig` + 当前商品 `openUrl`；扩展打开商品页并展示 `alertTip`（业务逻辑预留）。
- **任务节流**：后台排队、限速、去重与失败重试；遇风控/验证码可暂停并提示用户。

### 热卖运行配置（`mission_hotsale_dh_config`）

| 字段 | 说明 |
| --- | --- |
| `collectConfig.openUrl` | 列表采集打开的热卖页 |
| `collectConfig.watchApiUrl` | 列表页监听的接口 |
| `collectConfig.alertTip` | 列表页顶部提示 |
| `fillConfig` | 单次补充配置（原样下发；管理端再附加商品 `openUrl`） |
| `fillConfig.alertTip` | 商品页顶部提示 |

### 热卖列表工作流（阶段 B）

```text
1. 「开始采集」→ START mode=list_collect + collectConfig
2. 扩展开页；面板 alertTip + 监听进度；「完成采集」→ SYNC_CONFIRM → 入库
3. 行内「单次补充」→ START mode=detail_fill + fillConfig + 商品 openUrl（无二次确认）
4. 扩展打开商品页并展示提示；补充业务逻辑后续接入
```

### 热卖详情工作流

```text
1. 用户在管理端手动点击「采集详细信息」
2. 扩展按列表逐个访问商品 URL 并提取关键字段
3. 每提取成功一条 → 回传管理端 → 更新该条并刷新列表
4. 全部完成或用户中止 → 管理端展示最终状态
```

---

## 工程结构（规划）

后续脚手架落地时，大致按下列方式区分平台与业务（以实际代码为准）：

```text
src/core/           # 协议、路由、会话、消息总线
src/sites/          # 站点级能力（如 dhgate 的 hook / 页内 UI）
src/features/       # 按业务类型分目录（首期：hotsell）
entrypoints/        # WXT 入口：background、admin/dhgate content 等
```

新增业务时：新增 `features/<businessType>`、在路由中注册，管理端改传对应 `businessType` 与参数即可，无需把逻辑堆进 Background。

---

## 技术选型（规划）

- Manifest V3，优先 Chrome / Edge（Chromium）
- 脚手架倾向 **WXT** + TypeScript
- 接口响应捕获：目标页主世界 `fetch` / `XHR` hook（而非依赖 webRequest 读 body）

### 阶段 A（已落地）

- WXT + MV3 骨架：`core` 路由 / 协议、`features/hotsell`、`admin` content 桥
- 按需 `PING` / `PONG`（见 [docs/ADMIN_BRIDGE.zh.md](./docs/ADMIN_BRIDGE.zh.md)）

### 阶段 B（已落地）

- `START`：按配置 `openUrl` 开标签，绑定管理端 tab
- 敦煌 content：`openTip` 顶部面板 + `watchApiUrl` 主世界 fetch/XHR 监听 + 进度
- 面板「开始采集」→ `SYNC_CONFIRM` 回传最新响应；「取消」结束任务
- 管理端：接收回传并 `console.log`（见对接文档）

开发：`npm install && npm run dev`，加载 `.output` 下 Chrome 产物。详情队列为阶段 C。

---

## 说明与边界

- 扩展是通用执行端，不是通用公网爬虫工具；需用户主动安装，并在浏览器中访问相关页面。
- 列表数据先在扩展侧缓存「最新一次」接口响应，经用户在目标站点「开始采集」后再回传管理端；阶段 B 管理端仅打印，不写库。
- 详情采集不自动跟随列表同步，须管理端手动开启（阶段 C）。
- 目标站接口或页面结构变更时，对应 Feature / 站点配置可能需要更新。
- 请遵守目标站点服务条款与适用法律法规；控制采集频率与合规使用。
