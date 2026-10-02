const BASE = '/api';

function authHeaders(extra = {}) {
  const token = localStorage.getItem('zerotouch_token');
  return { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...extra };
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, { ...options, headers: authHeaders(options.headers || {}) });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Request failed (${res.status})` }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export async function login(email, password) {
  const res = await fetch(`${BASE}/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Sign in failed');
  localStorage.setItem('zerotouch_token', data.token);
  return data.user;
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
export const getCustomerMessages = () => request('/customer/messages');
export const sendChat = message => request('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }) });
export const getAdminAuditLogs = () => request('/admin/audit-logs');
export const getOpsCase = txId => request(`/ops/cases/${encodeURIComponent(txId)}`);

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
