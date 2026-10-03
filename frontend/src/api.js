const BASE = '/api';

function authHeaders(extra = {}) {
  const token = localStorage.getItem('zerotouch_token');
  return { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...extra };
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeout || 8000);
  try {
    const res = await fetch(`${BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: authHeaders(options.headers || {})
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Request failed (${res.status})` }));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error('Server request timed out');
    }
    throw err;
  }
}

export async function login(email, password) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 8000);
  try {
    const res = await fetch(`${BASE}/auth/login`, {
      method: 'POST',
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    clearTimeout(timeoutId);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'Sign in failed');
    localStorage.setItem('zerotouch_token', data.token);
    return data.user;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') throw new Error('Sign in timed out. Please check backend.');
    throw err;
  }
}

export function logout() {
  const token = localStorage.getItem('zerotouch_token');
  if (token) fetch(`${BASE}/auth/logout`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
  localStorage.removeItem('zerotouch_token');
}

export const getCurrentUser = () => request('/auth/me');
export const getCustomerProfile = () => request('/customer/profile');
export const getCustomerTransactions = () => request('/customer/transactions');
export const getCustomerCases = () => request('/customer/cases');
export const getCustomerRefunds = () => request('/customer/refunds');
export const getCustomerMessages = () => request('/customer/messages');
export const sendChat = message => request('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }) });
export const getAdminAuditLogs = () => request('/admin/audit-logs');
export const getOpsCases = () => request('/ops/cases');
export const getOpsCase = identifier => request(`/ops/cases/${encodeURIComponent(identifier)}`);
export const getEvaluationReport = () => request('/admin/evaluation', { timeout: 20000 });


export async function getTransactions() {
  return request('/transactions');
}


export async function getTransaction(txId) {
  return request(`/transactions/${encodeURIComponent(txId)}`);
}

export async function runResolution(txId) {
  return request(`/resolutions/${encodeURIComponent(txId)}/run`, { method: 'POST' });
}

export async function getEvents(txId) {
  return request(`/resolutions/${encodeURIComponent(txId)}/events`);
}

export async function resetDemo() {
  return request('/reset', { method: 'POST' });
}

export async function submitHumanDecision(txId, action, agentName, notes) {
  return request(`/resolutions/${encodeURIComponent(txId)}/human-decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, agent_name: agentName, notes }),
  });
}

// ── ZeroTouch Workforce Platform APIs ────────────────────────────────────────

export const getWorkforceRoles = () => request('/workforce/roles');
export const getWorkforceTasks = (domain, status) => {
  const params = new URLSearchParams();
  if (domain && domain !== 'all') params.append('domain', domain);
  if (status && status !== 'all') params.append('status', status);
  const q = params.toString() ? `?${params.toString()}` : '';
  return request(`/workforce/tasks${q}`);
};
export const approveWorkforceTask = (caseId, approver, notes) =>
  request(`/workforce/tasks/${encodeURIComponent(caseId)}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approver, notes }),
  });
export const editWorkforceTask = (caseId, approver, editedMessage, editedAmount, editNotes) =>
  request(`/workforce/tasks/${encodeURIComponent(caseId)}/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approver, edited_message: editedMessage, edited_amount: editedAmount, edit_notes: editNotes }),
  });
export const rejectWorkforceTask = (caseId, approver, rejectionReason) =>
  request(`/workforce/tasks/${encodeURIComponent(caseId)}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approver, rejection_reason: rejectionReason }),
  });
export const executeWorkforceCommand = (command, role) =>
  request('/workforce/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, role }),
  });
export const getWorkforceSkills = () => request('/workforce/skills');
export const teachWorkforceSkill = (domain, taskName, actions, whyNote, owner) =>
  request('/workforce/skills/teach', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain, task_name: taskName, actions, why_note: whyNote, owner }),
  });
export const backtestWorkforceSkill = spec =>
  request('/workforce/skills/backtest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(spec),
  });
export const publishWorkforceSkill = (spec, approver) =>
  request('/workforce/skills/publish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ spec, approver }),
  });
export const toggleWorkforceKillSwitch = user =>
  request('/workforce/governor/kill-switch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user }),
  });
export const getWorkforceGovernorState = () => request('/workforce/governor/state');
export const getWorkforceDashboard = (teamSize = 10, repetitivePct = 0.40, skillCoveragePct = 0.60, handlingTimeSavedPct = 0.80) => {
  const q = `?team_size=${teamSize}&repetitive_pct=${repetitivePct}&skill_coverage_pct=${skillCoveragePct}&handling_time_saved_pct=${handlingTimeSavedPct}`;
  return request(`/workforce/dashboard${q}`);
};
export const getFinanceReconciliation = () => request('/workforce/finance/reconciliation');
export const getAcademyCase = () => request('/workforce/academy/case');
export const submitAcademyCase = (joinerId, answers) =>
  request('/workforce/academy/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ joiner_id: joinerId, answers }),
  });
export const resetWorkforcePlatform = () =>
  request('/workforce/reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });

