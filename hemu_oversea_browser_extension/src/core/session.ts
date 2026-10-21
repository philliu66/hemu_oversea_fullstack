/** 与管理端采集会话绑定（阶段 A 仅预留；B/C 使用） */
export interface ExtSession {
  sessionId: string;
  adminTabId: number;
  businessType: string;
  createdAt: number;
}

let current: ExtSession | null = null;

export function getSession(): ExtSession | null {
  return current;
}

export function setSession(session: ExtSession | null): void {
  current = session;
}

export function bindAdminTab(tabId: number, businessType: string, sessionId?: string): ExtSession {
  const next: ExtSession = {
    sessionId: sessionId || `s_${Date.now()}_${tabId}`,
    adminTabId: tabId,
    businessType,
    createdAt: Date.now(),
  };
  current = next;
  return next;
}
