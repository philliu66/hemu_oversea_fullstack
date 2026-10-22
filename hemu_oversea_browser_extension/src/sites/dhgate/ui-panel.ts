export type HotsellPanelState = {
  /** 页顶提示（配置 alertTip） */
  alertTip: string;
  hasLatest: boolean;
  /** 列表采集：最新一次响应解析出的品类 */
  currentCategory?: string;
  /** 列表采集：最新一次响应中的商品条数 */
  itemCount?: number;
  /** 次要状态（回传中 / 失败等） */
  statusText?: string;
  /** 确认按钮文案 */
  confirmLabel?: string;
  /**
   * 是否必须有最新数据才可点确认。
   * 列表采集为 true；无需监听接口时可为 false。
   */
  requireLatest?: boolean;
};

export type HotsellPanelHandlers = {
  onConfirm: () => void;
  onCancel: () => void;
};

const ROOT_ID = 'hemu-hotsell-panel-root';

export function removeHotsellPanel(): void {
  document.getElementById(ROOT_ID)?.remove();
}

export function mountHotsellPanel(
  state: HotsellPanelState,
  handlers: HotsellPanelHandlers,
): { update: (patch: Partial<HotsellPanelState>) => void } {
  removeHotsellPanel();

  const root = document.createElement('div');
  root.id = ROOT_ID;
  root.attachShadow({ mode: 'open' });

  const style = document.createElement('style');
  style.textContent = `
    :host { all: initial; }
    .wrap {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 2147483646;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
      pointer-events: none;
    }
    .card {
      margin: 12px auto 0;
      max-width: 720px;
      background: #fff;
      border: 1px solid #d9d9d9;
      border-radius: 8px;
      box-shadow: 0 6px 24px rgba(0,0,0,.12);
      padding: 14px 16px;
      pointer-events: auto;
      color: #262626;
    }
    .tip {
      font-size: 14px;
      line-height: 1.55;
      margin: 0 0 10px;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .progress {
      font-size: 14px;
      color: #595959;
      margin: 0 0 12px;
      padding: 10px 12px;
      background: #fafafa;
      border-radius: 6px;
      border: 1px dashed #e8e8e8;
      line-height: 1.6;
    }
    .progress .hl {
      color: #1677ff;
      font-weight: 700;
      font-size: 18px;
      margin: 0 2px;
    }
    .progress .status {
      margin-top: 6px;
      font-size: 12px;
      color: #8c8c8c;
    }
    .actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }
    button {
      appearance: none;
      border-radius: 6px;
      padding: 6px 14px;
      font-size: 13px;
      cursor: pointer;
      border: 1px solid #d9d9d9;
      background: #fff;
      color: #262626;
    }
    button.primary {
      background: #1677ff;
      border-color: #1677ff;
      color: #fff;
    }
    button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
    button:hover:not(:disabled) { filter: brightness(0.98); }
  `;

  const card = document.createElement('div');
  card.className = 'wrap';
  card.innerHTML = `
    <div class="card">
      <p class="tip"></p>
      <div class="progress"></div>
      <div class="actions">
        <button type="button" class="cancel">取消</button>
        <button type="button" class="primary confirm">完成采集</button>
      </div>
    </div>
  `;

  root.shadowRoot!.append(style, card);
  document.documentElement.appendChild(root);

  const tipEl = root.shadowRoot!.querySelector('.tip') as HTMLElement;
  const progressEl = root.shadowRoot!.querySelector('.progress') as HTMLElement;
  const confirmBtn = root.shadowRoot!.querySelector('.confirm') as HTMLButtonElement;
  const cancelBtn = root.shadowRoot!.querySelector('.cancel') as HTMLButtonElement;

  let current: HotsellPanelState = {
    requireLatest: true,
    confirmLabel: '完成采集',
    ...state,
  };

  const render = () => {
    tipEl.textContent = current.alertTip;
    confirmBtn.textContent = current.confirmLabel || '完成采集';

    if (current.hasLatest && current.currentCategory != null) {
      const cat = escapeHtml(current.currentCategory);
      const count = Number(current.itemCount) || 0;
      let html = `当前已采集<span class="hl">${cat}</span>品类下共计<span class="hl">${count}</span>条热卖品数据`;
      if (current.statusText) {
        html += `<div class="status">${escapeHtml(current.statusText)}</div>`;
      }
      progressEl.innerHTML = html;
      progressEl.style.display = '';
    } else if (current.statusText) {
      progressEl.innerHTML = `<div class="status">${escapeHtml(current.statusText)}</div>`;
      progressEl.style.display = '';
    } else {
      progressEl.innerHTML = '';
      progressEl.style.display = 'none';
    }

    const requireLatest = current.requireLatest !== false;
    confirmBtn.disabled = requireLatest ? !current.hasLatest : false;
  };

  confirmBtn.addEventListener('click', () => handlers.onConfirm());
  cancelBtn.addEventListener('click', () => handlers.onCancel());

  render();

  return {
    update(patch) {
      current = { ...current, ...patch };
      render();
    },
  };
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
