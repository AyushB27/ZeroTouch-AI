import React, { useState, useEffect } from 'react';
import {
  Terminal, Search, Filter, RefreshCw, CheckCircle2,
  Clock, ShieldCheck, AlertTriangle, Layers, ChevronDown,
  ArrowRight, Bot, Cpu, FileText, Check, ExternalLink
} from 'lucide-react';
import { getWorkforceTraceLogs } from '../api';

const AGENT_META = {
  'Ledger Investigator Agent': { icon: '🕵️', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  'Risk & Credit Profiling Agent': { icon: '📊', color: 'bg-purple-50 text-purple-700 border-purple-200' },
  'Policy & Compliance Supervisor': { icon: '⚖️', color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  'Action Gateway': { icon: '🛡️', color: 'bg-emerald-50 text-emerald-800 border-emerald-200' },
  'Independent Verifier': { icon: '🔍', color: 'bg-teal-50 text-teal-800 border-teal-200' },
  'Dynamic Communication Agent': { icon: '✍️', color: 'bg-cyan-50 text-cyan-800 border-cyan-200' },
  'Connector Execution Gateway': { icon: '🔑', color: 'bg-amber-50 text-amber-800 border-amber-200' },
  'ZeroTouch Agent': { icon: '🤖', color: 'bg-slate-50 text-slate-700 border-slate-200' },
};

export default function AgentTraceLogsExplorer({ initialTxId = null, isEmbedded = false }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(initialTxId || '');
  const [selectedAgent, setSelectedAgent] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedWorkflow, setSelectedWorkflow] = useState('all');
  const [expandedLogId, setExpandedLogId] = useState(null);

  async function fetchLogs() {
    setLoading(true);
    try {
      const res = await getWorkforceTraceLogs({
        tx_id: search || undefined,
        actor: selectedAgent !== 'all' ? selectedAgent : undefined,
        status: selectedStatus !== 'all' ? selectedStatus : undefined,
        limit: 150,
      });
      if (res?.logs) setLogs(res.logs);
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchLogs();
  }, [selectedAgent, selectedStatus]);

  // Client-side search & workflow filter
  const filteredLogs = logs.filter(l => {
    const matchSearch =
      !search ||
      l.transaction_id?.toLowerCase().includes(search.toLowerCase()) ||
      l.case_id?.toLowerCase().includes(search.toLowerCase()) ||
      l.message?.toLowerCase().includes(search.toLowerCase()) ||
      l.step?.toLowerCase().includes(search.toLowerCase());

    const matchWf =
      selectedWorkflow === 'all' ||
      (selectedWorkflow === 'W1' && l.workflow_type === 'W1') ||
      (selectedWorkflow === 'W2' && l.workflow_type === 'W2') ||
      (selectedWorkflow === 'W3' && l.workflow_type === 'W3');

    return matchSearch && matchWf;
  });

  return (
    <div className={`space-y-4 text-slate-800 ${isEmbedded ? '' : 'p-4 sm:p-6 bg-slate-50 min-h-full'}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-3xl border border-slate-200 shadow-2xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Live Agent Telemetry Feed
            </span>
          </div>
          <h2 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Bot size={20} className="text-[#07356b]" />
            Agent Trace & Analysis Logs
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Transparent, chronological record of every step performed by the 5 autonomous agents and Action Gateway.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs font-bold text-slate-700 transition disabled:opacity-50"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            <span>Refresh Logs</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-3xl border border-slate-200 shadow-2xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {/* Search by Tx or Case */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search Tx, Case, or message..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full text-xs pl-8 pr-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#07356b]"
            />
          </div>

          {/* Filter by Agent */}
          <div className="relative">
            <select
              value={selectedAgent}
              onChange={e => setSelectedAgent(e.target.value)}
              aria-label="Filter by agent"
              className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 bg-white font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#07356b]"
            >
              <option value="all">All 5 Segregated Agents</option>
              <option value="Ledger Investigator Agent">🕵️ Ledger Investigator Agent</option>
              <option value="Risk & Credit Profiling Agent">📊 Risk & Credit Profiling Agent</option>
              <option value="Policy & Compliance Supervisor">⚖️ Policy & Compliance Supervisor</option>
              <option value="Action Gateway">🛡️ Action Gateway</option>
              <option value="Independent Verifier">🔍 Independent Verifier</option>
              <option value="Dynamic Communication Agent">✍️ Dynamic Communication Agent</option>
            </select>
          </div>

          {/* Filter by Workflow */}
          <div className="relative">
            <select
              value={selectedWorkflow}
              onChange={e => setSelectedWorkflow(e.target.value)}
              aria-label="Filter by workflow"
              className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 bg-white font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#07356b]"
            >
              <option value="all">All Workflows</option>
              <option value="W1">W1: Failed Payments (UPI Debit)</option>
              <option value="W2">W2: Refund SLAs & Bounces</option>
              <option value="W3">W3: Merchant Settlements</option>
            </select>
          </div>

          {/* Filter by Status */}
          <div className="relative">
            <select
              value={selectedStatus}
              onChange={e => setSelectedStatus(e.target.value)}
              aria-label="Filter by status"
              className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 bg-white font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#07356b]"
            >
              <option value="all">All Statuses (SUCCESS & INFO)</option>
              <option value="SUCCESS">✅ SUCCESS</option>
              <option value="INFO">ℹ️ INFO</option>
              <option value="FLAGGED">⚠️ FLAGGED</option>
            </select>
          </div>
        </div>

        {/* Quick pill stats */}
        <div className="flex flex-wrap items-center justify-between text-[11px] pt-1 border-t border-slate-100 text-slate-500 font-medium">
          <div className="flex items-center gap-3">
            <span>Showing <strong className="text-slate-800 font-bold">{filteredLogs.length}</strong> trace events</span>
            {search && (
              <button onClick={() => setSearch('')} className="text-cyan-700 hover:underline">
                Clear search
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-emerald-700 font-bold">
              <ShieldCheck size={13} /> SHA-256 Idempotency Enforced
            </span>
          </div>
        </div>
      </div>

      {/* Log Feed Table / List */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-2xs overflow-hidden">
        {filteredLogs.length === 0 ? (
          <div className="text-center py-16 text-slate-400 text-xs">
            {loading ? 'Fetching agent trace telemetry...' : 'No trace logs found matching the filter criteria.'}
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredLogs.map(log => {
              const meta = AGENT_META[log.agent] || AGENT_META['ZeroTouch Agent'];
              const isSuccess = log.status === 'SUCCESS';
              const isExpanded = expandedLogId === log.id;

              return (
                <div
                  key={log.id || `${log.transaction_id}-${log.timestamp}-${log.step}`}
                  className="p-4 hover:bg-slate-50/70 transition-colors flex flex-col gap-2 text-xs"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      {/* Agent Badge */}
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-bold text-[11px] border ${meta.color}`}>
                        <span>{meta.icon}</span>
                        <span>{log.agent}</span>
                      </span>

                      {/* Step Name */}
                      <span className="font-mono text-[10px] font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                        {log.step}
                      </span>

                      {/* Case & Tx Pill */}
                      <span className="font-mono text-[10px] font-extrabold text-[#07356b] bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                        {log.case_id || log.transaction_id}
                      </span>

                      {log.amount > 0 && (
                        <span className="font-extrabold text-slate-700 text-[11px]">
                          ₹{Number(log.amount).toLocaleString('en-IN')}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                      <span className={`font-bold px-2 py-0.5 rounded-full ${
                        isSuccess ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {log.status}
                      </span>
                      <span>{log.timestamp ? log.timestamp.slice(11, 19) + ' UTC' : 'T+0'}</span>
                    </div>
                  </div>

                  {/* Message / Narrative */}
                  <p className="text-xs text-slate-800 leading-relaxed font-sans bg-slate-50/50 p-2.5 rounded-xl border border-slate-100">
                    {log.message}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
