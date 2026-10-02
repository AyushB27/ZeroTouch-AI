import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  LayoutDashboard, ArrowLeftRight, Banknote, BarChart2,
  HelpCircle, Bell, Search, ChevronDown, RefreshCw,
  Zap, Eye, AlertTriangle, CheckCircle2, Clock, XCircle,
  X, ShieldAlert, Loader2, User, MoreVertical, Play,
  Smartphone, Store, Info, SplitSquareVertical, ArrowUpRight, LogOut, ScrollText
} from 'lucide-react';
import AgentTrace from './components/AgentTrace';
import HITLQueue  from './components/HITLQueue';
import ClientExperienceView from './components/ClientExperienceView';
import UserRolesModal from './components/UserRolesModal';
import { getTransactions, runResolution, resetDemo, getEvents, getAdminAuditLogs } from './api';
import { getCurrentUser, logout } from './api';
import LoginScreen from './components/LoginScreen';
import CustomerPortal from './components/CustomerPortal';

// ── constants ─────────────────────────────────────────────────────────────────
const WF_LABELS = { W1: 'Failed Payment', W2: 'Refund SLA', W3: 'Settlement' };
const WF_PILL = {
  W1: 'bg-blue-100 text-blue-700',
  W2: 'bg-purple-100 text-purple-700',
  W3: 'bg-orange-100 text-orange-700',
};

const STATUS_META = {
  PENDING:   { label: 'Pending',    dot: 'bg-amber-400',   pill: 'bg-amber-50  text-amber-700  border-amber-200'  },
  RESOLVED:  { label: 'Resolved',   dot: 'bg-emerald-500', pill: 'bg-emerald-50 text-emerald-700 border-emerald-200'},
  ESCALATED: { label: 'Escalated',  dot: 'bg-rose-500',    pill: 'bg-rose-50   text-rose-700   border-rose-200'   },
  NO_ACTION: { label: 'Consistent', dot: 'bg-slate-400',   pill: 'bg-slate-50  text-slate-600  border-slate-200'  },
};

// ── Sidebar ───────────────────────────────────────────────────────────────────
function Sidebar({ activeNav, onSelectNav, onOpenRolesModal }) {
  const navItems = [
    { id: 'transactions', icon: ArrowLeftRight,  label: 'Exceptions (Ops)' },
    { id: 'audit_logs',   icon: ScrollText,       label: 'Audit trail' },
    { id: 'client_view',  icon: Smartphone,      label: 'Client Simulator' },
    { id: 'split_view',   icon: SplitSquareVertical, label: 'Split Integration' },
  ];

  return (
    <aside className="w-56 bg-paytm-dark flex flex-col shrink-0 h-full select-none">
      {/* Logo */}
      <div className="h-16 flex items-center px-5 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-paytm-primary rounded flex items-center justify-center">
            <Zap size={14} className="text-white" />
          </div>
          <div>
            <div className="text-white font-extrabold text-sm leading-none tracking-tight">
              Zero<span className="text-paytm-primary">Touch</span>
            </div>
            <div className="text-blue-300 text-[9px] font-semibold leading-none mt-0.5">AUTONOMOUS SUPPORT</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-1 px-2">
        <div className="text-[10px] font-bold text-blue-300/70 uppercase px-3 mb-2 tracking-wider">
          Portals & Views
        </div>
        {navItems.map(({ id, icon: Icon, label }) => {
          const active = activeNav === id;
          return (
            <button
              key={id}
              onClick={() => onSelectNav(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold transition-all ${
                active
                  ? 'bg-paytm-primary text-white shadow-sm'
                  : 'text-blue-200 hover:bg-white/10 hover:text-white'
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          );
        })}

        <div className="pt-4 mt-4 border-t border-white/10">
          <div className="text-[10px] font-bold text-blue-300/70 uppercase px-3 mb-2 tracking-wider">
            Architecture
          </div>
          <button
            onClick={onOpenRolesModal}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold text-blue-200 hover:bg-white/10 hover:text-white transition-colors"
          >
            <Info size={16} />
            Who Uses What?
          </button>
        </div>
      </nav>

      {/* Bottom badge */}
      <div className="p-4 border-t border-white/10">
        <div className="bg-paytm-primary/10 border border-paytm-primary/30 rounded-lg p-3">
          <div className="text-[10px] font-bold text-paytm-primary uppercase tracking-wider mb-1">ZeroTouch AI</div>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[11px] text-emerald-300 font-semibold">Autonomous Mode</span>
          </div>
          <div className="text-[10px] text-blue-300 mt-1 font-mono">LANGGRAPH + RAG</div>
        </div>
      </div>
    </aside>
  );
}

// ── Status pill ───────────────────────────────────────────────────────────────
function StatusPill({ status }) {
  const m = STATUS_META[status] || STATUS_META.PENDING;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold ${m.pill}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${m.dot}`} />
      {m.label}
    </span>
  );
}

// ── Stats row ─────────────────────────────────────────────────────────────────
function StatsRow({ txList }) {
  const total     = txList.length;
  const resolved  = txList.filter(t => t.resolution_status === 'RESOLVED').length;
  const escalated = txList.filter(t => t.resolution_status === 'ESCALATED').length;
  const pending   = txList.filter(t => t.resolution_status === 'PENDING').length;

  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      {[
        { label: 'Total Exceptions',  value: total,     sub: 'All workflows',       color: 'text-paytm-dark' },
        { label: 'Auto-Resolved',     value: resolved,  sub: 'No ticket raised',    color: 'text-emerald-600'},
        { label: 'Escalated Cases',   value: escalated, sub: 'Awaiting human review',color:'text-rose-600'   },
        { label: 'Pending',           value: pending,   sub: 'Awaiting agent run',  color: 'text-amber-600' },
      ].map(c => (
        <div key={c.label} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <p className="text-xs text-slate-500 font-medium mb-1">{c.label}</p>
          <p className={`text-3xl font-extrabold ${c.color}`}>{c.value}</p>
          <p className="text-[11px] text-slate-400 mt-1">{c.sub}</p>
        </div>
      ))}
    </div>
  );
}

// ── Transactions table ────────────────────────────────────────────────────────
function TxTable({ txList, onInvestigate, onView, busyId }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 bg-slate-50">
            {['Tx ID & Customer', 'Amount', 'CIBIL', 'Tenure', 'Workflow', 'Bank Status', 'Status', 'Action'].map(h => (
              <th key={h} className="text-left text-[11px] font-bold text-slate-400 uppercase tracking-wider px-4 py-3 whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50">
          {txList.map(tx => {
            const wf = WF_LABELS[tx.workflow_type] || tx.workflow_type;
            const isResolvable = tx.resolution_status === 'PENDING';
            const isBusy = busyId === tx.transaction_id;
            const cibil = tx.cibil_score || 750;
            const isFTU = tx.is_first_time_user;

            return (
              <tr key={tx.transaction_id} className="hover:bg-slate-50/60 transition-colors">
                <td className="px-4 py-3.5">
                  <span className="font-bold text-slate-800 font-mono text-xs">{tx.transaction_id}</span>
                  <span className="text-[11px] text-slate-500 font-medium block truncate max-w-[130px]">
                    {tx.customer_name || 'Paytm User'}
                  </span>
                </td>
                <td className="px-4 py-3.5 font-semibold text-slate-700 whitespace-nowrap">
                  ₹{tx.amount.toLocaleString('en-IN')}
                </td>
                <td className="px-4 py-3.5 whitespace-nowrap">
                  <span className={`inline-flex items-center gap-1 font-mono font-bold text-xs px-2 py-0.5 rounded-full ${
                    cibil >= 750 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                    cibil >= 650 ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                    'bg-rose-50 text-rose-700 border border-rose-200'
                  }`}>
                    {cibil}
                    <span className="text-[9px] font-sans font-medium opacity-80">
                      ({cibil >= 750 ? 'Prime' : cibil >= 650 ? 'Good' : 'Subprime'})
                    </span>
                  </span>
                </td>
                <td className="px-4 py-3.5 whitespace-nowrap">
                  {isFTU ? (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                      ⭐ First-Time
                    </span>
                  ) : (
                    <span className="text-[11px] text-slate-400 font-medium">Regular</span>
                  )}
                </td>
                <td className="px-4 py-3.5">
                  <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${WF_PILL[tx.workflow_type] || 'bg-slate-100 text-slate-600'}`}>
                    {wf}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-slate-600 text-xs whitespace-nowrap">{tx.bank_status}</td>
                <td className="px-4 py-3.5">
                  <StatusPill status={tx.resolution_status} />
                </td>
                <td className="px-4 py-3.5">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onView(tx)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-paytm-dark hover:bg-slate-100 transition-colors"
                      title="View details"
                    >
                      <Eye size={15} />
                    </button>
                    {isResolvable && (
                      <button
                        onClick={() => onInvestigate(tx.transaction_id)}
                        disabled={!!busyId}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-paytm-primary text-white text-xs font-bold hover:bg-paytm-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                        title="Run ZeroTouch agent"
                      >
                        {isBusy
                          ? <><Loader2 size={12} className="animate-spin"/> Running...</>
                          : <><Play size={12}/> Investigate</>
                        }
                      </button>
                    )}
                    {!isResolvable && (
                      <button
                        onClick={() => onView(tx)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 text-slate-600 text-xs font-bold hover:bg-slate-200 transition-colors whitespace-nowrap"
                      >
                        <Eye size={12}/> View Result
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Right slide-over panel ────────────────────────────────────────────────────
function SlidePanel({ open, onClose, title, children, badge, width = "w-[540px]" }) {
  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/20 z-30 backdrop-blur-sm"
          onClick={onClose}
        />
      )}
      {/* Panel */}
      <div className={`fixed right-0 top-0 h-full ${width} max-w-[95vw] bg-white shadow-2xl z-40 flex flex-col transition-transform duration-300 ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 bg-slate-50 shrink-0">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-800 text-sm">{title}</span>
            {badge}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-400 hover:text-slate-700 transition-colors">
            <X size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-hidden">{children}</div>
      </div>
    </>
  );
}

// ── Transaction detail slide-over ─────────────────────────────────────────────
function TxDetailPanel({ tx, events, result, isRunning, onRun, onClose }) {
  if (!tx) return null;
  const [tab, setTab] = useState('details');

  const fields = [
    ['Transaction ID', tx.transaction_id],
    ['Customer Name',  tx.customer_name || 'Paytm User'],
    ['CIBIL Score',    `${tx.cibil_score || 750} (${(tx.cibil_score || 750) >= 750 ? 'Prime' : (tx.cibil_score || 750) >= 650 ? 'Good' : 'Subprime'})`],
    ['Tenure',         tx.is_first_time_user ? '⭐ First-Time User' : 'Regular Customer'],
    ['Amount',         `₹${tx.amount.toLocaleString('en-IN')}`],
    ['Workflow',       WF_LABELS[tx.workflow_type] || tx.workflow_type],
    ['Bank Status',    tx.bank_status],
    ['Network Status', tx.network_status],
    ['Merchant Status',tx.merchant_status],
    ['Settlement',     tx.settlement_status],
    ['Risk Score',     `${(tx.risk_score * 100).toFixed(0)}%`],
    ['Prior Refund',   tx.previous_refund ? 'Yes' : 'No'],
    ['Resolution',     tx.resolution_status],
    ...(tx.action_id ? [['Action Ref', tx.action_id]] : []),
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="flex border-b border-slate-100 shrink-0 bg-slate-50/50">
        {[
          { id: 'details', label: 'Details' },
          { id: 'trace',   label: 'Agent Trace' },
          { id: 'client',  label: 'Client Impact' },
          { id: 'hitl',   label: 'HITL' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-3 text-xs font-bold border-b-2 transition-colors ${
              tab === t.id
                ? 'border-paytm-primary text-paytm-dark bg-white'
                : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            {t.label}
            {t.id === 'trace' && isRunning && (
              <Loader2 size={10} className="inline ml-1 animate-spin text-paytm-primary" />
            )}
          </button>
        ))}
      </div>

      {tab === 'details' && (
        <div className="flex-1 overflow-y-auto">
          {/* Header */}
          <div className="px-5 py-5 border-b border-slate-50 bg-paytm-dark/5">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-extrabold text-paytm-dark text-xl font-mono">{tx.transaction_id}</div>
                <div className="flex items-center gap-2 mt-1.5">
                  <StatusPill status={tx.resolution_status}/>
                  <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${WF_PILL[tx.workflow_type]||'bg-slate-100 text-slate-600'}`}>
                    {WF_LABELS[tx.workflow_type]}
                  </span>
                </div>
              </div>
              <div className="text-2xl font-extrabold text-paytm-dark">₹{tx.amount.toLocaleString('en-IN')}</div>
            </div>
          </div>

          {/* Fields */}
          <div className="px-5 py-4 space-y-0">
            {fields.map(([k,v])=>(
              <div key={k} className="flex justify-between items-center py-3 border-b border-slate-50">
                <span className="text-xs text-slate-400 font-medium">{k}</span>
                <span className="text-xs font-bold text-slate-800 font-mono max-w-[200px] text-right truncate">{v}</span>
              </div>
            ))}
          </div>

          {/* Action */}
          <div className="p-5">
            {tx.resolution_status === 'PENDING' ? (
              <button
                onClick={() => { setTab('trace'); onRun(tx.transaction_id); }}
                disabled={isRunning}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm bg-paytm-primary hover:bg-paytm-dark text-white transition-colors disabled:opacity-60 shadow-sm"
              >
                {isRunning ? <><Loader2 size={15} className="animate-spin"/>Running ZeroTouch...</> : <><Zap size={15}/>Run ZeroTouch Agent</>}
              </button>
            ) : (
              <div className={`w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm border ${
                tx.resolution_status==='RESOLVED'  ? 'bg-emerald-50 border-emerald-200 text-emerald-700' :
                tx.resolution_status==='ESCALATED' ? 'bg-rose-50 border-rose-200 text-rose-700' :
                'bg-slate-50 border-slate-200 text-slate-600'
              }`}>
                {tx.resolution_status==='RESOLVED'  && <><CheckCircle2 size={15}/>Auto-Resolved</>}
                {tx.resolution_status==='ESCALATED' && <><AlertTriangle size={15}/>Escalated to HITL</>}
                {tx.resolution_status==='NO_ACTION' && <><CheckCircle2 size={15}/>No Action Required</>}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'trace' && (
        <AgentTrace events={events} result={result} isRunning={isRunning}/>
      )}

      {tab === 'client' && (
        <div className="flex-1 overflow-hidden">
          <ClientExperienceView selectedTxId={tx.transaction_id} result={result} />
        </div>
      )}

      {tab === 'hitl' && (
        tx.resolution_status === 'ESCALATED'
          ? <HITLQueue escalated={[tx]} onDecision={onClose}/>
          : (
            <div className="flex-1 flex flex-col items-center justify-center gap-2 text-slate-400 px-6 text-center p-8">
              <CheckCircle2 size={36} className="opacity-30"/>
              <p className="text-sm">This case is not escalated.</p>
              <p className="text-xs">HITL queue only shows cases that ZeroTouch has escalated to human review.</p>
            </div>
          )
      )}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
function OperationsConsole({ onLogout }) {
  const [activeNav,    setActiveNav]    = useState('transactions'); // 'transactions' | 'client_view' | 'split_view'
  const [txList,       setTxList]       = useState([]);
  const [selectedTx,   setSelectedTx]   = useState(null);
  const [panelOpen,    setPanelOpen]    = useState(false);
  const [hitlOpen,     setHitlOpen]     = useState(false);
  const [rolesModalOpen, setRolesModalOpen] = useState(false);
  const [activeResult, setActiveResult] = useState(null);
  const [activeEvents, setActiveEvents] = useState([]);
  const [busyId,       setBusyId]       = useState(null);
  const [isResetting,  setIsResetting]  = useState(false);
  const [error,        setError]        = useState(null);
  const [backendDown,  setBackendDown]  = useState(false);
  const [searchQ,      setSearchQ]      = useState('');
  const [auditLogs,    setAuditLogs]     = useState([]);

  const loadTx = useCallback(async () => {
    try {
      setBackendDown(false);
      const txs = await getTransactions();
      setTxList(txs);
    } catch (e) {
      if (e.message.includes('fetch')) setBackendDown(true);
    }
  }, []);

  useEffect(() => { loadTx(); }, [loadTx]);
  useEffect(() => {
    if (activeNav === 'audit_logs') getAdminAuditLogs().then(setAuditLogs).catch(e => setError(e.message));
  }, [activeNav]);

  // keep selectedTx in sync with live txList
  useEffect(() => {
    if (selectedTx) {
      const fresh = txList.find(t => t.transaction_id === selectedTx.transaction_id);
      if (fresh) setSelectedTx(fresh);
    }
  }, [txList]);

  const escalated = txList.filter(t => t.resolution_status === 'ESCALATED');

  const handleInvestigate = async (txId) => {
    setBusyId(txId);
    setActiveResult(null);
    setActiveEvents([]);
    setError(null);
    try {
      const res = await runResolution(txId);
      setActiveResult(res);
      setActiveEvents(res.events || []);
      await loadTx();
    } catch (e) {
      if (e.message.includes('fetch')) setBackendDown(true);
      else setError(e.message);
    } finally {
      setBusyId(null);
    }
  };

  const handleView = (tx) => {
    setSelectedTx(tx);
    if (tx.resolution_status !== 'PENDING') {
      getEvents(tx.transaction_id).then(setActiveEvents).catch(()=>{});
    } else {
      setActiveEvents([]);
      setActiveResult(null);
    }
    setPanelOpen(true);
  };

  const handleReset = async () => {
    setIsResetting(true);
    setActiveResult(null); setActiveEvents([]); setError(null);
    try { await resetDemo(); await loadTx(); setPanelOpen(false); }
    catch { setError('Reset failed'); }
    finally { setIsResetting(false); }
  };

  const filtered = txList.filter(t =>
    !searchQ ||
    t.transaction_id.toLowerCase().includes(searchQ.toLowerCase()) ||
    t.resolution_status.toLowerCase().includes(searchQ.toLowerCase()) ||
    (WF_LABELS[t.workflow_type]||'').toLowerCase().includes(searchQ.toLowerCase())
  );

  if (backendDown) return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow border border-slate-200 p-8 text-center max-w-sm">
        <div className="w-12 h-12 bg-paytm-dark rounded-xl flex items-center justify-center mx-auto mb-4">
          <Zap size={20} className="text-white"/>
        </div>
        <div className="font-bold text-slate-800 mb-2">Backend offline</div>
        <code className="text-xs bg-slate-100 px-2 py-1.5 rounded block mb-4 text-slate-600">
          python -m uvicorn backend.main:app --port 8000 --reload
        </code>
        <button onClick={loadTx} className="text-sm text-paytm-primary font-bold hover:underline">Retry</button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F5F7FA] flex h-screen overflow-hidden">

      {/* ── Sidebar ── */}
      <Sidebar
        activeNav={activeNav}
        onSelectNav={setActiveNav}
        onOpenRolesModal={() => setRolesModalOpen(true)}
      />

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Top header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center px-6 gap-4 shrink-0 shadow-sm z-20">
          <div>
            <h1 className="font-extrabold text-slate-800 text-base leading-none">
              {activeNav === 'transactions' && 'Transaction Exceptions & Ops'}
              {activeNav === 'audit_logs'   && 'Audit trail'}
              {activeNav === 'client_view'  && 'Client Surface Simulator (Customer & Merchant)'}
              {activeNav === 'split_view'   && 'Real-Time Integration Split View'}
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">ZeroTouch Command Center · Autonomous AI Resolution Engine</p>
          </div>

          {/* Quick Nav Mode Pills */}
          <div className="hidden lg:flex items-center gap-1 bg-slate-100 p-1 rounded-xl ml-4">
            <button
              onClick={() => setActiveNav('transactions')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeNav === 'transactions'
                  ? 'bg-white text-paytm-dark shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <ArrowLeftRight size={13} /> Ops Dashboard
            </button>
            <button
              onClick={() => setActiveNav('client_view')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeNav === 'client_view'
                  ? 'bg-white text-paytm-dark shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <Smartphone size={13} /> Client Experience
            </button>
            <button
              onClick={() => setActiveNav('split_view')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeNav === 'split_view'
                  ? 'bg-white text-paytm-dark shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <SplitSquareVertical size={13} /> Split View
            </button>
          </div>

          {/* Search (only on transactions) */}
          {activeNav === 'transactions' && (
            <div className="hidden md:flex items-center gap-2 bg-slate-100 rounded-lg px-3 py-2 ml-auto w-60">
              <Search size={14} className="text-slate-400 shrink-0"/>
              <input
                className="bg-transparent text-sm outline-none w-full placeholder-slate-400"
                placeholder="Search transactions..."
                value={searchQ}
                onChange={e => setSearchQ(e.target.value)}
              />
            </div>
          )}

          <div className="ml-auto flex items-center gap-3">
            {error && (
              <div className="flex items-center gap-1.5 text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-1.5">
                <XCircle size={12}/>{error}
              </div>
            )}

            {/* Architecture Info Pill */}
            <button
              onClick={() => setRolesModalOpen(true)}
              className="hidden sm:flex items-center gap-1.5 text-xs font-semibold text-paytm-dark bg-blue-50 hover:bg-blue-100 border border-blue-200 px-3 py-2 rounded-lg transition-colors"
            >
              <Info size={13} className="text-paytm-primary" />
              <span>Who Uses This?</span>
            </button>

            {/* HITL badge */}
            {escalated.length > 0 && (
              <button
                onClick={() => setHitlOpen(true)}
                className="relative flex items-center gap-2 bg-rose-600 hover:bg-rose-700 text-white px-3 py-2 rounded-lg text-xs font-bold transition-colors"
              >
                <ShieldAlert size={14}/>
                HITL Queue
                <span className="absolute -top-2 -right-2 w-5 h-5 bg-white text-rose-600 border-2 border-white rounded-full text-[10px] font-black flex items-center justify-center shadow">
                  {escalated.length}
                </span>
              </button>
            )}

            <button
              onClick={handleReset}
              disabled={isResetting || !!busyId}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 border border-slate-200 rounded-lg px-3 py-2 hover:bg-slate-50 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={13} className={isResetting ? 'animate-spin' : ''}/>
              Reset Demo
            </button>

            {/* Avatar */}
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-paytm-dark flex items-center justify-center">
                <User size={15} className="text-white"/>
              </div>
              <button onClick={onLogout} className="hidden sm:inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50" aria-label="Sign out">
                <LogOut size={13}/> Sign out
              </button>
            </div>
          </div>
        </header>

        {/* ── Content Router ── */}
        {activeNav === 'transactions' && (
          <main className="flex-1 overflow-y-auto p-6">
            <StatsRow txList={txList}/>

            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-bold text-slate-700">
                Payment Exceptions & Edge Cases <span className="text-slate-400 font-normal ml-1">({filtered.length})</span>
              </h2>
            </div>

            <TxTable
              txList={filtered}
              onInvestigate={handleInvestigate}
              onView={handleView}
              busyId={busyId}
            />
          </main>
        )}

        {activeNav === 'audit_logs' && (
          <main className="flex-1 overflow-y-auto p-6">
            <div className="mx-auto max-w-5xl">
              <div className="mb-5 flex items-end justify-between gap-4">
                <div><h2 className="text-lg font-extrabold text-slate-800">Investigation audit trail</h2><p className="mt-1 text-xs text-slate-500">Recorded evidence checks, policy decisions, actions, verification and customer updates.</p></div>
                <span className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-bold text-paytm-dark">{auditLogs.length} events</span>
              </div>
              {auditLogs.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center"><ScrollText size={28} className="mx-auto text-slate-300"/><p className="mt-3 text-sm font-bold text-slate-700">No audit events yet</p><p className="mt-1 text-xs text-slate-500">Run an investigation to see its recorded timeline here.</p></div>
              ) : (
                <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                  {auditLogs.map((event, index) => (
                    <div key={`${event.transaction_id}-${event.timestamp}-${index}`} className="grid grid-cols-[118px_1fr] gap-4 border-b border-slate-100 px-4 py-4 last:border-0 sm:grid-cols-[150px_104px_1fr] sm:px-5">
                      <time className="text-[11px] font-medium text-slate-400">{new Date(event.timestamp).toLocaleString()}</time>
                      <div className="hidden sm:block"><span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-bold text-slate-600">{event.transaction_id}</span></div>
                      <div><div className="flex flex-wrap items-center gap-2"><span className="text-xs font-bold capitalize text-slate-800">{event.step.replaceAll('_', ' ')}</span><span className={`rounded px-1.5 py-0.5 text-[9px] font-extrabold ${event.status === 'FAILED' ? 'bg-rose-50 text-rose-700' : event.status === 'INFO' ? 'bg-blue-50 text-blue-700' : 'bg-emerald-50 text-emerald-700'}`}>{event.status}</span><span className="text-[10px] text-slate-400 sm:hidden">{event.transaction_id}</span></div><p className="mt-1 text-xs leading-5 text-slate-500">{event.message}</p></div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </main>
        )}

        {activeNav === 'client_view' && (
          <main className="flex-1 overflow-hidden">
            <ClientExperienceView
              selectedTxId={selectedTx?.transaction_id}
              result={activeResult}
              onSelectTx={(id) => {
                const found = txList.find(t => t.transaction_id === id);
                if (found) setSelectedTx(found);
              }}
            />
          </main>
        )}

        {activeNav === 'split_view' && (
          <main className="flex-1 flex overflow-hidden">
            {/* Left 50%: Ops Transactions Table & Trigger */}
            <div className="w-1/2 border-r border-slate-200 flex flex-col overflow-y-auto p-5 bg-white">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Internal Ops Trigger</h3>
                  <p className="text-[11px] text-slate-400">Click Investigate on any transaction to watch the client side update live</p>
                </div>
              </div>
              <TxTable
                txList={filtered}
                onInvestigate={handleInvestigate}
                onView={handleView}
                busyId={busyId}
              />
            </div>

            {/* Right 50%: Client Experience Screen */}
            <div className="w-1/2 flex flex-col overflow-hidden bg-slate-100">
              <ClientExperienceView
                selectedTxId={busyId || selectedTx?.transaction_id || 'TX9281'}
                result={activeResult}
              />
            </div>
          </main>
        )}

      </div>

      {/* ── Transaction detail slide-over ── */}
      <SlidePanel
        open={panelOpen}
        onClose={() => setPanelOpen(false)}
        title={selectedTx?.transaction_id || 'Transaction'}
        badge={selectedTx && <StatusPill status={selectedTx.resolution_status}/>}
      >
        <TxDetailPanel
          tx={selectedTx}
          events={activeEvents}
          result={activeResult}
          isRunning={!!busyId}
          onRun={handleInvestigate}
          onClose={() => setPanelOpen(false)}
        />
      </SlidePanel>

      {/* ── HITL slide-over ── */}
      <SlidePanel
        open={hitlOpen}
        onClose={() => setHitlOpen(false)}
        title="HITL Review Queue"
        badge={
          <span className="bg-rose-100 text-rose-700 text-[10px] font-black px-2 py-0.5 rounded-full border border-rose-200">
            {escalated.length} pending
          </span>
        }
      >
        <HITLQueue escalated={escalated} onDecision={async () => { await loadTx(); }}/>
      </SlidePanel>

      {/* ── User Roles & Architecture Modal ── */}
      <UserRolesModal
        open={rolesModalOpen}
        onClose={() => setRolesModalOpen(false)}
      />

    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    if (!localStorage.getItem('zerotouch_token')) { setCheckingSession(false); return; }
    getCurrentUser().then(setUser).catch(() => logout()).finally(() => setCheckingSession(false));
  }, []);

  const handleLogin = async () => setUser(await getCurrentUser());
  const handleLogout = () => { logout(); setUser(null); };

  if (checkingSession) return <div className="grid min-h-screen place-items-center bg-[#f4f8fc] text-sm font-semibold text-slate-500">Loading ZeroTouch…</div>;
  if (!user) return <LoginScreen onLogin={handleLogin}/>;
  if (user.role === 'CUSTOMER') return <CustomerPortal user={user} onLogout={handleLogout}/>;
  return <OperationsConsole onLogout={handleLogout}/>;
}
