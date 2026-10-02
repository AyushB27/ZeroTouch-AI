import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  LayoutDashboard, ArrowLeftRight, Banknote, BarChart2,
  HelpCircle, Bell, Search, ChevronDown, RefreshCw,
  Zap, Eye, AlertTriangle, CheckCircle2, Clock, XCircle,
  X, ShieldAlert, Loader2, User, MoreVertical, Play
} from 'lucide-react';
import AgentTrace from './components/AgentTrace';
import HITLQueue  from './components/HITLQueue';
import { getTransactions, runResolution, resetDemo, getEvents } from './api';

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
const NAV = [
  { icon: LayoutDashboard, label: 'Dashboard'    },
  { icon: ArrowLeftRight,  label: 'Transactions', active: true },
  { icon: Banknote,        label: 'Settlements'  },
  { icon: BarChart2,       label: 'Reports'      },
  { icon: HelpCircle,      label: 'Help'         },
];

function Sidebar() {
  return (
    <aside className="w-56 bg-paytm-dark flex flex-col shrink-0 h-full">
      {/* Logo */}
      <div className="h-16 flex items-center px-5 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-paytm-primary rounded flex items-center justify-center">
            <Zap size={14} className="text-white" />
          </div>
          <div>
            <div className="text-white font-extrabold text-sm leading-none tracking-tight">
              pay<span className="text-paytm-primary">tm</span>
            </div>
            <div className="text-blue-300 text-[9px] font-semibold leading-none mt-0.5">for Business</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-0.5 px-2">
        {NAV.map(({ icon: Icon, label, active }) => (
          <button
            key={label}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              active
                ? 'bg-paytm-primary/20 text-paytm-primary'
                : 'text-blue-200 hover:bg-white/10 hover:text-white'
            }`}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </nav>

      {/* Bottom badge */}
      <div className="p-4 border-t border-white/10">
        <div className="bg-paytm-primary/10 border border-paytm-primary/30 rounded-lg p-3">
          <div className="text-[10px] font-bold text-paytm-primary uppercase tracking-wider mb-1">ZeroTouch AI</div>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[11px] text-emerald-300 font-semibold">Autonomous Mode</span>
          </div>
          <div className="text-[10px] text-blue-300 mt-1 font-mono">PROTOTYPE</div>
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
            {['Transaction ID','Amount','Workflow','Bank Status','Network','Risk','Status','Action'].map(h => (
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

            return (
              <tr key={tx.transaction_id} className="hover:bg-slate-50/60 transition-colors">
                <td className="px-4 py-3.5">
                  <span className="font-bold text-slate-800 font-mono">{tx.transaction_id}</span>
                </td>
                <td className="px-4 py-3.5 font-semibold text-slate-700 whitespace-nowrap">
                  ₹{tx.amount.toLocaleString('en-IN')}
                </td>
                <td className="px-4 py-3.5">
                  <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${WF_PILL[tx.workflow_type] || 'bg-slate-100 text-slate-600'}`}>
                    {wf}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-slate-600 text-xs whitespace-nowrap">{tx.bank_status}</td>
                <td className="px-4 py-3.5 text-slate-600 text-xs whitespace-nowrap">{tx.network_status}</td>
                <td className="px-4 py-3.5">
                  <span className={`text-xs font-bold ${tx.risk_score >= 0.5 ? 'text-rose-600' : tx.risk_score >= 0.3 ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {(tx.risk_score * 100).toFixed(0)}%
                  </span>
                </td>
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
function SlidePanel({ open, onClose, title, children, badge }) {
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
      <div className={`fixed right-0 top-0 h-full w-[460px] bg-white shadow-2xl z-40 flex flex-col transition-transform duration-300 ${open ? 'translate-x-0' : 'translate-x-full'}`}>
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
      <div className="flex border-b border-slate-100 shrink-0">
        {[{id:'details',label:'Details'},{id:'trace',label:'Agent Trace'},{id:'hitl',label:'HITL'}].map(t=>(
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-5 py-3 text-xs font-bold border-b-2 transition-colors ${
              tab===t.id ? 'border-paytm-primary text-paytm-dark' : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            {t.label}
            {t.id==='trace' && isRunning && <Loader2 size={10} className="inline ml-1 animate-spin text-paytm-primary"/>}
          </button>
        ))}
      </div>

      {tab==='details' && (
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
            {tx.resolution_status==='PENDING' ? (
              <button
                onClick={()=>{setTab('trace'); onRun(tx.transaction_id);}}
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

      {tab==='trace' && (
        <AgentTrace events={events} result={result} isRunning={isRunning}/>
      )}

      {tab==='hitl' && (
        tx.resolution_status==='ESCALATED'
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
export default function App() {
  const [txList,       setTxList]       = useState([]);
  const [selectedTx,   setSelectedTx]   = useState(null);
  const [panelOpen,    setPanelOpen]    = useState(false);
  const [hitlOpen,     setHitlOpen]     = useState(false);
  const [activeResult, setActiveResult] = useState(null);
  const [activeEvents, setActiveEvents] = useState([]);
  const [busyId,       setBusyId]       = useState(null);
  const [isResetting,  setIsResetting]  = useState(false);
  const [error,        setError]        = useState(null);
  const [backendDown,  setBackendDown]  = useState(false);
  const [searchQ,      setSearchQ]      = useState('');

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
    // Restore existing events for already-resolved transactions
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
      <Sidebar />

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Top header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center px-6 gap-4 shrink-0 shadow-sm">
          <div>
            <h1 className="font-extrabold text-slate-800 text-base leading-none">Transaction Exceptions</h1>
            <p className="text-xs text-slate-400 mt-0.5">ZeroTouch AI · Payment Operations</p>
          </div>

          {/* Search */}
          <div className="flex items-center gap-2 bg-slate-100 rounded-lg px-3 py-2 ml-6 w-64">
            <Search size={14} className="text-slate-400 shrink-0"/>
            <input
              className="bg-transparent text-sm outline-none w-full placeholder-slate-400"
              placeholder="Search transactions..."
              value={searchQ}
              onChange={e => setSearchQ(e.target.value)}
            />
          </div>

          <div className="ml-auto flex items-center gap-3">
            {error && (
              <div className="flex items-center gap-1.5 text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-1.5">
                <XCircle size={12}/>{error}
              </div>
            )}

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

            {/* Notification bell */}
            <button className="relative w-9 h-9 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors">
              <Bell size={18} className="text-slate-500"/>
              {escalated.length > 0 && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full"/>
              )}
            </button>

            {/* Avatar */}
            <div className="flex items-center gap-2 cursor-pointer">
              <div className="w-8 h-8 rounded-full bg-paytm-dark flex items-center justify-center">
                <User size={15} className="text-white"/>
              </div>
              <ChevronDown size={14} className="text-slate-400"/>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <StatsRow txList={txList}/>

          {/* Table header */}
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold text-slate-700">
              All Exceptions <span className="text-slate-400 font-normal ml-1">({filtered.length})</span>
            </h2>
          </div>

          <TxTable
            txList={filtered}
            onInvestigate={handleInvestigate}
            onView={handleView}
            busyId={busyId}
          />
        </main>
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

    </div>
  );
}
