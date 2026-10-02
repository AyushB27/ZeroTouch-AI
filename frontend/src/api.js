const BASE = '/api';

export async function getTransactions() {
  const res = await fetch(`${BASE}/transactions`);
  if (!res.ok) throw new Error('Failed to fetch transactions');
  return res.json();
}

export async function getTransaction(txId) {
  const res = await fetch(`${BASE}/transactions/${txId}`);
  if (!res.ok) throw new Error(`Failed to fetch transaction ${txId}`);
  return res.json();
}

export async function runResolution(txId) {
  const res = await fetch(`${BASE}/resolutions/${txId}/run`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || 'Resolution failed');
  }
  return res.json();
}

export async function getEvents(txId) {
  const res = await fetch(`${BASE}/resolutions/${txId}/events`);
  if (!res.ok) throw new Error('Failed to fetch events');
  return res.json();
}

export async function resetDemo() {
  const res = await fetch(`${BASE}/reset`, { method: 'POST' });
  if (!res.ok) throw new Error('Reset failed');
  return res.json();
}

export async function submitHumanDecision(txId, action, agentName, notes) {
  const res = await fetch(`${BASE}/resolutions/${txId}/human-decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, agent_name: agentName, notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || 'Decision submission failed');
  }
  return res.json();
}
