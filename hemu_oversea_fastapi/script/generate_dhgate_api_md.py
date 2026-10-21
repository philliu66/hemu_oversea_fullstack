"""根据 scrape 产出 + 关联知识，生成 AI 联调用 dhgate_API.md。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRAPE = Path(__file__).resolve().parent / "_dhgate_doc_scrape"
OUT = ROOT / "dhgate_API.md"

# 模块级关联（给 AI 串链路用）
MODULE_REL: dict[str, str] = {
    "相册API": (
        "素材链路：`dh.album.list` → `dh.album.repeat.get`(可选去重) → "
        "`dh.album.img.upload` → `dh.album.img.post`(入相册) → 图片 URL/MD5 填入 "
        "`dh.item.add` 的 `itemImgList`。"
    ),
    "基础API": "合规看板：处罚查询可与 `dh.user.seller.get`、经营数据 `dh.wis.*` 并列展示。",
    "类目API": (
        "发布前置：`dh.category.list`(树) → `dh.category.get`(属性/限制) → "
        "`dh.category.itemname.valid` / `dh.category.is3Ccategory` → 再 `dh.item.add`。"
        "变更同步用 `dh.categoryid.list` 增量拉 ID 后再 get。"
    ),
    "客户评论API": "评价列表/详情与订单 `orderNo` / 产品 `itemCode` 关联；回复后可用列表复核状态。",
    "物流API": (
        "发布取 `dh.shipping.template.list` → `shippingModelId`；发货取 "
        "`dh.shipping.typelist` + `dh.order.delivery.save`；轨迹 `dh.shipping.trackinfo.list`。"
        "算运费：`dh.shipping.compute.item` / `package`（国家可用公共 `dh.base.countrys.get`）。"
    ),
    "站内信API": (
        "`dh.message.count` → `dh.message.list` → `dh.message.get` → "
        "`dh.message.info.reply` / `dh.message.send` → `dh.message.status.update`。"
    ),
    "订单API": (
        "`dh.order.list.get` → `dh.order.get` / `dh.order.product.get` → "
        "请款 `applymoney.check`→`applymoney.get`；发货 `delivery.save`；"
        "纠纷 `dispute*.list`→`dispute.detail.get`。"
    ),
    "产品API": (
        "上新：类目+相册+运费+售后就绪后 `dh.item.add` → `dh.item.upshelf.list`。"
        "运维：`dh.item.list`→`dh.item.get`→`update` / `price.update` / 备货系列。"
        "更新务必 get 全量再改字段提交，勿按 add 映射裁剪。"
    ),
    "用户API": "店铺身份与权限：`dh.user.seller.get` / `isapiseller`；基础用户信息 `dh.user.base.get`。",
    "在线发货API": (
        "`dh.online.channel.list` → `dh.online.freight.estimate` → "
        "`dh.online.order.place` → `dh.online.label.get` → `dh.online.trackinfo.list`。"
        "与平台运费/发货接口场景不同，勿混用。"
    ),
    "数据API(限免)": (
        "经营分析三件套：`dh.wis.core.info`(店铺核心指标) ↔ "
        "`dh.wis.detail.page`(单品分析分页) ↔ `dh.wis.keywordtop10.info`(关键词 TOP)。"
        "广告消耗见「增值API」。"
    ),
    "增值API": (
        "广告报表：`dh.seller.ad.order.report.page`(订单维) / "
        "`dh.seller.ad.prod.report.page`(产品维)；`itemcode` 可来自 `dh.item.list`。"
    ),
}

# 按 method 前缀的关联补充（覆盖官网表未写清的上下游）
METHOD_REL: list[tuple[str, str]] = [
    (r"^dh\.album\.img\.upload", "上传后：返回 `imgUrl`/`imgMd5` → `item.add.itemImgList` 或 `album.img.post`。"),
    (r"^dh\.album\.img\.post", "入参图片一般来自 `dh.album.img.upload`；相册 ID 来自 `dh.album.list`。"),
    (r"^dh\.album\.repeat\.get", "上传前去重；已存在则直接复用返回的 `imgUrl`。"),
    (r"^dh\.category\.list", "返回 `catePubId` → `category.get` / `item.add`。"),
    (r"^dh\.category\.get", "产出属性与限制 → 填 `item.add` 的 `itemAttrList` 等。"),
    (r"^dh\.category\.is3C", "3C 时必须配 `dh.item.aftersale.list` 的售后模板 ID。"),
    (r"^dh\.item\.add", "依赖：类目 get、图片 upload、运费 template.list、售后 aftersale.list；成功后可 upshelf。"),
    (r"^dh\.item\.update$", "先 `dh.item.get` 取全量，改字段后原样提交（保留 skuId/skuMD5）。"),
    (r"^dh\.item\.get$", "详情底稿：供 update / 改价 / 备货等写接口使用。"),
    (r"^dh\.item\.list", "列表筛品 → 再 `item.get` 或批量上下架/删除。"),
    (r"^dh\.item\.update\.stock", "设置备货模式后，再用 `item.update.sku.stock.quantity` 改 SKU 数量。"),
    (r"^dh\.order\.list\.get", "时间跨度注意文档上限；拿到 `orderNo` 再 get/发货/纠纷。"),
    (r"^dh\.order\.applymoney\.check", "请款前必调；通过后再 `order.applymoney.get`。"),
    (r"^dh\.order\.delivery\.save", "`shippingType` 参考 `shipping.typelist`；轨迹用 `shipping.trackinfo.list`。"),
    (r"^dh\.wis\.core\.info", "店铺看板；下钻单品用 `wis.detail.page`，关键词用 `wis.keywordtop10.info`。"),
    (r"^dh\.wis\.detail\.page", "产品维分析；`itemCode` 可对照 `item.list`/`item.get`。"),
    (
        r"^dh\.wis\.keywordtop10",
        "关键词 TOP；按字段名联调：`itemCode`=产品编码，`siteId`/`platformId`/`searchDateType` 见取值说明。"
        "（官网参数「说明」列对 itemCode 等可能有笔误，以字段名+试跑为准。）",
    ),
    (r"^dh\.seller\.ad\.", "广告消耗报表；与 `wis.*` 经营数据互补，勿与 Data 限免三接口混淆。"),
    (r"^dh\.online\.order\.place", "在线发货下单；前置渠道 list + 运费 estimate，后取 label。"),
]

# 表格解析失败时的关键入参兜底（来自官网既有整理）
FALLBACK_PARAMS: dict[str, list[dict]] = {
    "dh.album.img.upload$2.1": [
        {"name": "funType", "type": "String", "required": "必须", "values": "", "desc": "功能类型（商品图片）"},
        {"name": "imgName", "type": "String", "required": "必须", "values": "", "desc": "图片名称"},
        {"name": "imgBase64", "type": "String", "required": "必须", "values": "", "desc": "图片 BASE64 内容"},
        {"name": "imgBannerName", "type": "String", "required": "可选", "values": "", "desc": "Banner 名"},
        {"name": "markPosition", "type": "String", "required": "可选", "values": "", "desc": "水印位置"},
    ],
    "dh.item.add$2.0": [
        {"name": "catePubId", "type": "String", "required": "必须", "values": "", "desc": "叶子类目 ID←category.list/get"},
        {"name": "shippingModelId", "type": "String", "required": "必须", "values": "", "desc": "运费模板←shipping.template.list"},
        {"name": "afterSaleTemplateId", "type": "String", "required": "条件必须", "values": "", "desc": "3C 类目售后模板←item.aftersale.list"},
        {"name": "itemBase", "type": "Object", "required": "必须", "values": "JSON", "desc": "标题/短描等基础信息"},
        {"name": "itemPackage", "type": "Object", "required": "必须", "values": "JSON", "desc": "包装重量尺寸等"},
        {"name": "itemImgList", "type": "List", "required": "必须", "values": "JSON", "desc": "图片列表←album.img.upload"},
        {"name": "itemSkuList", "type": "List", "required": "必须", "values": "JSON", "desc": "SKU 与价格库存"},
        {"name": "itemAttrList", "type": "List", "required": "必须", "values": "JSON", "desc": "类目属性←category.get"},
        {"name": "itemAttrGroupList", "type": "List", "required": "可选", "values": "JSON", "desc": "属性组"},
        {"name": "itemWholesaleRangeList", "type": "List", "required": "可选", "values": "JSON", "desc": "阶梯批发价"},
        {"name": "itemShiptoSettingList", "type": "List", "required": "可选", "values": "JSON", "desc": "目的国设置"},
        {"name": "itemSaleSetting", "type": "Object", "required": "可选", "values": "JSON", "desc": "销售设置"},
        {"name": "itemSpecSelfDefList", "type": "List", "required": "可选", "values": "JSON", "desc": "自定义规格"},
        {"name": "itemCustomTypeInfo", "type": "Object", "required": "可选", "values": "JSON", "desc": "定制信息"},
    ],
}


def md_escape(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


def method_of(name: str) -> str:
    return name.split("$", 1)[0]


def version_of(name: str) -> str:
    return name.split("$", 1)[1] if "$" in name else ""


def rel_for(name: str, module: str) -> str:
    bits = [MODULE_REL.get(module, "")]
    for pat, tip in METHOD_REL:
        if re.search(pat, method_of(name)):
            bits.append(tip)
            break
    return " ".join(b for b in bits if b)


def clean_params(rows: list[dict] | None) -> list[dict]:
    out = []
    for r in rows or []:
        name = (r.get("name") or "").strip()
        if not name or name in ("参数名称", "名称"):
            continue
        out.append(r)
    return out


def param_table(rows: list[dict], *, title: str) -> str:
    if not rows:
        return f"*{title}：官网详情页未解析到表格；联调时打开下方「官网详情」核对，或看兜底说明。*\n\n"
    lines = [
        f"**{title}**",
        "",
        "| 参数 | 类型 | 必须 | 取值说明 | 说明 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        name = md_escape(r.get("name") or "")
        typ = md_escape(r.get("type") or "")
        req = md_escape(r.get("required") or "")
        values = md_escape(r.get("values") or "")
        desc = md_escape(r.get("desc") or "")
        raw = r.get("raw") or []
        if len(raw) >= 5 and (not typ or not desc):
            typ = md_escape(raw[1])
            req = md_escape(raw[2])
            values = md_escape(raw[3])
            desc = md_escape(raw[4])
        lines.append(f"| `{name}` | {typ} | {req} | {values} | {desc} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def header() -> str:
    return """# 敦煌网开放平台 API 手册（AI 联调版）

> 数据来源：官网 [API文档](https://open.dhgate.com/docs/api) 各模块列表页 + 接口详情页（Playwright 抓取）。  
> **用途**：给 AI / 开发者做本仓库 `testAPI/dhgate` 联调对照——接口做什么、关键参数必传什么、可选值、模块间如何串。  
> **版本策略**：同一 `method` 多版本时只展开**最高版本**；旧版见各模块折叠区。  
> **统一入口**：`http://api.dhgate.com/dop/router`；公共参数：`method` / `v` / `timestamp` / `access_token`。

---

## 〇、AI 联调约定（必读）

1. **先 OAuth2**：店铺授权拿到 `access_token`，失效先 refresh，再调业务接口。
2. **本仓库联调路径**：`POST /api/v1/common/testAPI/dhgate/...`（单店）或 `.../dhgate/commerce/...`（多店编排）；底层仍调官网 `method`+`v`。
3. **读说明顺序**：做什么 → 业务必填参数与取值说明 → 返回关键字段 →「关联」链路。
4. **枚举勿编造**：仅使用「取值说明」列或官网详情写明的可选值；不确定就用联调 `raw` 回包校准。
5. **复杂 Object/List**：按 JSON 字符串提交（如 `itemBase`、`itemSkuList`）；发布/更新产品以 `item.get` 结构为底稿。

### 典型链路（优先级）

```text
授权 access_token
  ├─ 类目：category.list → category.get →（可选）itemname.valid / is3Ccategory
  ├─ 素材：album.list → album.img.upload →（可选）album.img.post
  ├─ 模板：shipping.template.list + item.aftersale.list + item.group.list / template.list
  ├─ 发布：item.add → item.upshelf.list
  ├─ 运维：item.list → item.get → item.update / price.update / 备货系列
  ├─ 订单：order.list.get → order.get → delivery.save / applymoney.* / dispute*
  ├─ 数据：wis.core.info / wis.detail.page / wis.keywordtop10.info
  └─ 广告：seller.ad.order.report.page / seller.ad.prod.report.page（增值API）
```

```mermaid
flowchart TD
    A["OAuth2 access_token"] --> B["category.list / get"]
    B --> C["album.img.upload"]
    C --> D["shipping.template.list + aftersale.list"]
    D --> E["item.add"]
    E --> F["item.upshelf.list"]
    A --> G["order.list.get → order.get"]
    G --> H["delivery.save / applymoney / dispute"]
    A --> I["wis.core / detail / keywordtop10"]
```

---

## 一、公共参数（所有接口）

| 参数 | 类型 | 必须 | 说明 |
| --- | --- | --- | --- |
| `method` | String | 是 | API 名，如 `dh.item.get`（不含 `$版本`） |
| `v` | String | 是 | 版本号，如 `2.0`（对应文档名 `$` 后一段） |
| `timestamp` | String | 是 | 毫秒时间戳（北京时间，允许 ±30 分钟） |
| `access_token` | String | 是 | OAuth2 令牌 |

- 幂等查询可用 GET，写入/上传建议统一 **POST**。
- 授权级别：A 读 / B 更新 / C 计算 / D 复合；App 另有控制台权限档位。
- 错误响应见官网「平台错误码」「授权错误响应」。

---

"""


PUBLIC_API_SECTION = """
## 二点五、公共 API（补充）

> 侧栏「公共 API」与卖家模块分开；本次自动抓取未稳定探到列表页，以下按官网既有能力整理，供联调取字典数据。入口同样是 `dop/router` + 公共参数。

| 接口 | 做什么 | 关键入参 | 关联 |
| --- | --- | --- | --- |
| `dh.base.countrys.get$1.0` | 国家列表 | 无业务必填 | 运费/发货国家下拉；`shipping.compute.*`、`online.freight.estimate` |
| `dh.base.exchangerate.get$2.0` | 两币种汇率 | `fromCurrency`、`toCurrency` 必填 | 多币种定价；可配 `dropshipping.currency.list` |
| `dh.base.measures.get$1.0` | 计量单位列表 | 无业务必填 | `item.add` 包装 `measureId` |
| `dh.dropshipping.currency.list$1.0` | 分销币种列表 | — | `publicVisit=0`，需开通；配汇率接口 |
| `dh.dropshipping.dispcategory.list$1.0` | 分销展示类目树 | `parentId`/`cateDispId` 可选 | 展示类目≠发布类目；发布仍用 `category.list/get` |

"""


def flows_and_appendix(modules: list) -> str:
    return (
        PUBLIC_API_SECTION
        + """
## 三、典型业务联动链路（详）

### 3.1 选品发布

```mermaid
flowchart TD
    A["access_token"] --> B["dh.category.list"]
    B --> C["dh.category.get"]
    C --> D["dh.category.itemname.valid"]
    D --> E["dh.album.img.upload"]
    E --> F["dh.shipping.template.list"]
    F --> G["dh.item.aftersale.list / item.template.list"]
    G --> H["dh.item.add"]
    H --> I["dh.item.upshelf.list"]
```

- `catePubId` 贯穿类目与发布；图片先 upload 再进 `itemImgList`；3C 需售后模板。

### 3.2 订单履约

```mermaid
flowchart TD
    A["dh.order.list.get"] --> B["dh.order.get"]
    B --> C["dh.order.product.get"]
    B --> D["applymoney.check → applymoney.get"]
    B --> E["delivery.save"]
    E --> F["shipping.trackinfo.list"]
    B --> G["dispute* / refund.list"]
```

- 在线发货改走 `online.channel.list` → `order.place` → `label.get`。

### 3.3 产品运维

`item.list` → `item.get` → `item.update` / `price.update` / `wholesale.update.list` / `update.stock` → `update.sku.stock.quantity`；下架 `downshelf.list` → 删除 `delete.list`。

### 3.4 经营数据

`wis.core.info`（店铺）↔ `wis.detail.page`（单品）↔ `wis.keywordtop10.info`（关键词）；广告消耗见增值 `seller.ad.*.report.page`。

---

## 四、附录

### 4.1 维护命令

```bash
python script/scrape_dhgate_open_docs.py
python script/rescrape_empty_details.py   # 可选：补抓空参数表
python script/generate_dhgate_api_md.py
```

### 4.2 版本替代（常见）

| 旧 | 新 |
| --- | --- |
| `dh.albums.get$1.0` | `dh.album.list$2.0` |
| `dh.categorys.get$1.0` | `dh.category.list$2.0` |
| `dh.products.get$1.0` / `dh.product.get$1.1` | `dh.item.list$2.0` / `dh.item.get$2.0` |
| `dh.messages.get$1.0` | `dh.message.list$2.0` |
| `dh.order.list.get$1.x` | `dh.order.list.get$2.0` |
| `dh.album.img.upload$2.0` | `dh.album.img.upload$2.1` |

### 4.3 官网模块代码

""" + "\n".join(
        f"- `{m['code']}` {m['module']} — {m['url']}" for m in modules
    ) + """

文档来源：<https://open.dhgate.com/docs/api>（卖家 API 侧栏模块；公共/分销若侧栏可探到会一并收录）。
"""
    )


def main() -> None:
    modules = json.loads((SCRAPE / "modules.json").read_text(encoding="utf-8"))
    details = json.loads((SCRAPE / "details.json").read_text(encoding="utf-8"))

    parts: list[str] = [header()]

    parts.append("## 二、模块与接口详情（对照官网）\n\n")
    for i, mod in enumerate(modules, 1):
        parts.append(
            f"{i}. [{mod['module']}](#{mod['code']}) — "
            f"[列表]({mod['url']}) — preferred **{len(mod.get('apis_preferred') or [])}**\n"
        )
    parts.append("\n")

    for mod in modules:
        code = mod["code"]
        parts.append(f"### {mod['module']} {{#{code}}}\n\n")
        parts.append(f"- **官网列表**：<{mod['url']}>\n")
        if mod.get("intro"):
            parts.append(f"- **模块说明**：{md_escape(mod['intro'])}\n")
        rel = MODULE_REL.get(mod["module"])
        if rel:
            parts.append(f"- **模块关联**：{rel}\n")
        parts.append(
            f"- **收录**：全量 {len(mod.get('apis_all') or [])} 版本条目；"
            f"下文 preferred {len(mod.get('apis_preferred') or [])}（最高版本）\n\n"
        )

        parts.append("| 接口 | method | v | 官网描述 |\n| --- | --- | --- | --- |\n")
        for api in mod.get("apis_preferred") or []:
            n = api["name"]
            parts.append(
                f"| [`{n}`]({api['href']}) | `{method_of(n)}` | `{version_of(n)}` | "
                f"{md_escape(api.get('desc') or '')} |\n"
            )
        parts.append("\n")

        preferred_names = {a["name"] for a in (mod.get("apis_preferred") or [])}
        obsolete = [
            a for a in (mod.get("apis_all") or []) if a["name"] not in preferred_names
        ]
        if obsolete:
            parts.append("<details><summary>同模块其它版本（联调默认不用）</summary>\n\n")
            for a in obsolete:
                parts.append(f"- `{a['name']}` — {md_escape(a.get('desc') or '')}\n")
            parts.append("\n</details>\n\n")

        for api in mod.get("apis_preferred") or []:
            name = api["name"]
            d = details.get(name) or {}
            ov = d.get("overview") or {}
            desc = ov.get("desc") or api.get("desc") or ""
            # 官网有时把「超时控制」错解析进 desc
            if desc in ("超时控制", "接口说明") or not desc:
                desc = api.get("desc") or d.get("list_desc") or ""

            parts.append(f"#### `{name}`\n\n")
            parts.append(f"- **做什么**：{md_escape(desc)}\n")
            parts.append(f"- **method / v**：`{method_of(name)}` / `{version_of(name)}`\n")
            parts.append(f"- **官网详情**：<{api['href']}>\n")
            if ov.get("timeout"):
                parts.append(f"- **超时**：{md_escape(ov['timeout'])}\n")
            if ov.get("level"):
                parts.append(f"- **授权级别**：{md_escape(ov['level'])}\n")
            if ov.get("publicVisit"):
                parts.append(f"- **公网访问**：{md_escape(ov['publicVisit'])}\n")
            tip = rel_for(name, mod["module"])
            if tip:
                parts.append(f"- **关联**：{tip}\n")
            parts.append("\n")

            req = clean_params(d.get("requestParams"))
            if not req and name in FALLBACK_PARAMS:
                req = FALLBACK_PARAMS[name]
                parts.append("> 下表为联调兜底关键字段（官网详情表未结构化解析到时使用）。\n\n")
            parts.append(param_table(req, title="业务请求参数"))

            # requestText 兜底摘录
            if not clean_params(d.get("requestParams")) and d.get("requestText"):
                excerpt = md_escape(d["requestText"][:1200])
                parts.append(f"<details><summary>官网「请求参数」正文摘录</summary>\n\n{excerpt}\n\n</details>\n\n")

            parts.append(param_table(clean_params(d.get("responseParams")), title="响应关键字段"))
            errs = clean_params(d.get("errorCodes"))
            if errs:
                parts.append(param_table(errs, title="业务错误码"))

            parts.append("\n")

    parts.append(flows_and_appendix(modules))
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {OUT} size={OUT.stat().st_size} lines={OUT.read_text(encoding='utf-8').count(chr(10))+1}")


if __name__ == "__main__":
    main()
