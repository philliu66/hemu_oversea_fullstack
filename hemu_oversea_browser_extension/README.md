# hemu_oversea_browser_extension

English | [简体中文](./README.zh.md)

**Browser extension platform** for the HeMu overseas commerce system. It runs in the user’s browser and executes collect / intercept / relay capabilities according to business types issued by the admin app. The extension does **not** talk to the business database; results are sent back through an agreed protocol to a signed-in admin page, which calls the backend API to persist them.

The project is organized as **platform core + business features**, so more scenarios can be added later—not only a single collection task.

---

## Platform role

| Role | Responsibility |
| --- | --- |
| Admin (`hemu_oversea_fastapiadmin`) | Detect extension, start jobs, receive payloads, call backend, refresh UI |
| This extension | Installed in the browser; routes `businessType` / `action` / `payload` to the matching feature |
| Backend (`hemu_oversea_fastapi`) | Business APIs and database (never accessed directly by the extension) |

**Messaging**：The admin origin and third-party sites (e.g. DHgate) are cross-origin and must not talk via bare `postMessage`. Traffic goes through the extension **background** as a message bus, then back to the admin tab that started the job.

```text
Admin page
  ↔ content script (admin)
  ↔ background (router / session / task queue)
  ↔ content script + site helpers (e.g. DHgate)
  ↔ target site page
```

The admin sends a common envelope, e.g. `businessType`, `action`, and `payload`. The extension responds by type; unknown types return a clear error so the admin can ask the user to upgrade the extension.

---

## First feature: DHgate hot-sell collection (`hotsell`)

The first feature captures DHgate **storefront** hot-sell listings and product details in the user’s browser (this is **not** the same path as official seller Data API / `dh.wis.*` shop analytics).

### Capabilities

- **Install check (on demand)**: Only when the user clicks a business action (e.g. “Start collection”) does the page send `PING`; **no global detection** on every admin page load. If missing, prompt to install (guidance later).
- **List collect `list_collect` (Phase B)**: Admin sends `collectConfig` (`openUrl` / `watchApiUrl` / `alertTip`); extension opens page, watches API, then `SYNC_CONFIRM` back for persist.
- **Detail fill `detail_fill`**: Admin sends `fillConfig` + product `openUrl`; extension opens the product page and shows `alertTip` (business logic reserved).
- **Throttling**: Background queue, rate limits, dedupe, and retries; on risk-control / captcha, pause and prompt the user.

### Runtime config (`mission_hotsale_dh_config`)

| Field | Meaning |
| --- | --- |
| `collectConfig.openUrl` | Hot-sell list page to open |
| `collectConfig.watchApiUrl` | API to watch on that page |
| `collectConfig.alertTip` | Tip on the list page |
| `fillConfig` | Detail-fill config (sent as-is; admin adds product `openUrl`) |
| `fillConfig.alertTip` | Tip on the product page |

### Hot-sell list workflow (Phase B)

```text
1. “Start collection” → START mode=list_collect + collectConfig
2. Extension opens page; panel alertTip + watch progress; “Finish” → SYNC_CONFIRM → persist
3. Row “Detail fill” → START mode=detail_fill + fillConfig + product openUrl (no confirm dialog)
4. Extension opens product page with tip; fill business logic comes later
```

### Hot-sell detail workflow

```text
1. User manually clicks “Collect details” in the admin
2. Extension visits each product URL and extracts key fields
3. On each success → relay to admin → update that row and refresh the list
4. Finish or user abort → admin shows final status
```

---

## Planned layout

When scaffolding lands, platform vs business will roughly look like (subject to the real tree):

```text
src/core/           # protocol, router, session, message bus
src/sites/          # site-level helpers (e.g. dhgate hook / in-page UI)
src/features/       # one folder per business type (first: hotsell)
entrypoints/        # WXT entries: background, admin/dhgate content, etc.
```

To add a business: add `features/<businessType>`, register it in the router, and have the admin send the new `businessType` and params—without dumping logic into the background script.

---

## Planned stack

- Manifest V3; Chrome / Edge (Chromium) first
- Scaffolding leaning **WXT** + TypeScript
- Response capture via page-world `fetch` / `XHR` hooks (not relying on webRequest response bodies)

### Phase A (landed)

- WXT + MV3 skeleton: `core` router/protocol, `features/hotsell`, `admin` content bridge
- On-demand `PING` / `PONG` (see [docs/ADMIN_BRIDGE.zh.md](./docs/ADMIN_BRIDGE.zh.md))

### Phase B (landed)

- `START`: open `openUrl`, bind admin tab
- DHgate content: `openTip` panel + `watchApiUrl` main-world fetch/XHR hook + progress
- Panel “Start collection” → `SYNC_CONFIRM` with latest response; “Cancel” ends the job
- Admin: listen and `console.log` (see bridge doc)

Dev: `npm install && npm run dev`, then load the Chrome output under `.output`. Detail crawl is Phase C.

---

## Notes & boundaries

- The extension is a general execution host for HeMu admin flows, not a general-purpose public scraper; users must install it and visit the relevant pages themselves.
- List capture keeps the latest API response in the extension until the user confirms on the target site; Phase B admin only logs, no DB write yet.
- Detail crawl does not auto-start after list sync; it requires an explicit admin action (Phase C).
- Feature / site config may need updates when the target site changes APIs or DOM.
- Respect the target site’s terms of service and applicable law; keep rate limits and compliant use.
