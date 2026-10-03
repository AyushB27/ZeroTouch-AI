import React, { useEffect, useState, useRef } from 'react';
import {
  ArrowRight, Bot, Check, CheckCircle2, Clock3, LogOut,
  MessageCircle, Send, ShieldAlert, Sparkles, WalletCards,
  XCircle, CheckCheck, RefreshCw, FileText, ChevronRight, Lock,
  Plus, PanelLeftClose, PanelLeft, SlidersHorizontal, ArrowUpRight,
  User, CreditCard, ChevronDown, CheckSquare, ShieldCheck, HelpCircle
} from 'lucide-react';
import {
  getCustomerCases, getCustomerMessages, getCustomerProfile, getCustomerRefunds,
  getCustomerTransactions, sendChat
} from '../api';

const SCENARIO_CARDS = [
  {
    icon: '💸',
    title: 'Stuck UPI Payment',
    txId: 'TX9281',
    amount: '₹2,500',
    prompt: 'My ₹2,500 UPI payment was deducted but merchant didn’t receive it.',
    sub: 'Auto-reversal with prime credit limit check',
  },
  {
    icon: '🛡️',
    title: 'High-Value Transfer',
    txId: 'TX9342',
    amount: '₹18,000',
    prompt: 'My ₹18,000 payment is stuck and deducted from my bank.',
    sub: 'High-risk first-time user human escalation',
  },
  {
    icon: '⏱️',
    title: 'Delayed Refund SLA',
    txId: 'RF202',
    amount: '₹1,800',
    prompt: 'My ₹1,800 refund hasn’t arrived yet past the 5-day window.',
    sub: 'Automated bank escalation API follow-up',
  },
  {
    icon: '👛',
    title: 'Bounced Bank Refund',
    txId: 'RF204',
    amount: '₹2,500',
    prompt: 'My ₹2,500 refund bounced due to an invalid bank account.',
    sub: 'Instant Paytm Wallet credit resolution',
  },
  {
    icon: '📊',
    title: 'Settlement Shortfall',
    txId: 'S301',
    amount: '₹10,000',
    prompt: 'Why did I receive ₹9,650 instead of ₹10,000 settlement?',
    sub: 'Itemized platform fee & GST reconciliation',
  },
  {
    icon: '🔒',
    title: 'KYC Settlement Hold',
    txId: 'S306',
    amount: '₹45,000',
    prompt: 'Why is my ₹45,000 merchant payout on hold?',
    sub: 'Expired compliance KYC safety hold',
  },
];

const money = value => `₹${Number(value).toLocaleString('en-IN')}`;

function CaseStatusBadge({ status }) {
  const resolved = status === 'RESOLVED' || status === 'NO_ACTION';
  const waiting = status === 'ESCALATED' || status === 'HUMAN_REVIEW';
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
      resolved
        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
        : waiting
        ? 'bg-amber-50 text-amber-800 border border-amber-200'
        : 'bg-blue-50 text-[#07356b] border border-blue-200'
    }`}>
      {resolved ? <CheckCircle2 size={12}/> : waiting ? <Clock3 size={12}/> : <RefreshCw size={12} className="animate-spin"/>}
      {resolved ? 'Resolved & Verified' : waiting ? 'In Human Review' : 'Investigating'}
    </span>
  );
}

function LedgerRow({ label, value }) {
  const isErr = ['NOT_CREDITED', 'FAILED', 'BOUNCED', 'HELD'].some(flag => (value || '').includes(flag));
  const isPending = ['PENDING', 'UNKNOWN'].some(flag => (value || '').includes(flag));
  const friendly = {
    DEBITED: 'Debited (Confirmed)',
    SUCCESS: 'Success / Confirmed',
    CREDITED: 'Credited to Merchant',
    NOT_CREDITED: 'Not Credited',
    NOT_FOUND: 'Not Found / Absent',
    SETTLED: 'Settled to Bank',
    REVERSED: 'Reversed Successfully',
    PENDING_CREDIT: 'Pending Credit',
    SLA_BREACHED: 'SLA Breached',
    BOUNCED_INVALID_ACCOUNT: 'Bounced (Invalid A/c)',
    FAILED_RETURN: 'Return Failed',
    HELD_KYC_EXPIRED: 'KYC Expired (Held)',
    SETTLED_TO_NODAL: 'Settled to Nodal',
  }[value] || (value || 'Pending');

  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0 text-xs">
      <span className="text-slate-500 font-medium">{label}</span>
      <span className={`inline-flex items-center gap-1.5 font-semibold ${
        isErr ? 'text-rose-600' : isPending ? 'text-amber-600' : 'text-emerald-700'
      }`}>
        {!isErr && !isPending && <Check size={12} className="text-emerald-600 stroke-[3]" />}
        {isErr && <XCircle size={12} className="text-rose-500" />}
        {friendly}
      </span>
    </div>
  );
}

// Inline Interactive Verification Card inside Assistant responses
function VerificationCard({ tx, caseId, status, activity }) {
  if (!tx) return null;
  const isResolved = status === 'RESOLVED' || tx.resolution_status === 'RESOLVED';
  const isEscalated = status === 'ESCALATED' || tx.resolution_status === 'ESCALATED';

  return (
    <div className="mt-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-xs text-left max-w-2xl">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-extrabold text-[#07356b] bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
            {caseId || `ZT-${tx.transaction_id.slice(-5)}`}
          </span>
          <span className="font-mono text-xs text-slate-500 font-semibold">{tx.transaction_id}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-extrabold text-sm text-[#07356b]">{money(tx.amount)}</span>
          <CaseStatusBadge status={status || tx.resolution_status} />
        </div>
      </div>

      {/* 4 Core Ledgers Matrix */}
      <div className="mt-3 bg-slate-50 rounded-xl p-3 border border-slate-100">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">4-System Ledger Reconciliation</span>
          <span className="text-[10px] font-semibold text-emerald-700 flex items-center gap-1">
            <CheckCheck size={12} className="text-emerald-600"/> Verified Invariants
          </span>
        </div>
        <LedgerRow label="1. Bank Debit Ledger" value={tx.bank_status} />
        <LedgerRow label="2. Payment Network (NPCI)" value={tx.network_status} />
        <LedgerRow label="3. Merchant Ledger" value={tx.merchant_status} />
        <LedgerRow label="4. Settlement Account" value={tx.settlement_status} />
      </div>

      {/* Action Gateway verified reference badge */}
      {tx.action_id && (
        <div className="mt-2.5 flex items-center justify-between rounded-xl bg-emerald-50/80 border border-emerald-200 px-3 py-2 text-xs">
          <div className="flex items-center gap-2 text-emerald-900 font-bold">
            <CheckCircle2 size={15} className="text-emerald-600"/>
            Action Gateway Reference:
          </div>
          <span className="font-mono font-bold text-emerald-800 bg-white px-2 py-0.5 rounded border border-emerald-200">
            {tx.action_id}
          </span>
        </div>
      )}

      {/* Timeline items */}
      {activity && activity.length > 0 && (
        <div className="mt-3 pt-2.5 border-t border-slate-100">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
            Investigation Milestones ({activity.length})
          </span>
          <div className="space-y-1.5">
            {activity.slice(-3).map((item, idx) => (
              <div key={idx} className="flex items-center gap-2 text-xs text-slate-600">
                <span className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] ${
                  item.status === 'FAILED' ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'
                }`}>
                  {item.status === 'FAILED' ? '×' : '✓'}
                </span>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function CustomerPortal({ user, onLogout, onSwitchToOps }) {
  const [profile, setProfile] = useState(user);
  const [transactions, setTransactions] = useState([]);
  const [cases, setCases] = useState([]);
  const [refunds, setRefunds] = useState([]);
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [selectedCaseTx, setSelectedCaseTx] = useState(null);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  async function refresh() {
    const [p, tx, cs, msgs, refundRows] = await Promise.all([
      getCustomerProfile(),
      getCustomerTransactions(),
      getCustomerCases(),
      getCustomerMessages(),
      getCustomerRefunds()
    ]);
    setProfile(p);
    setTransactions(tx);
    setCases(cs);
    setMessages(msgs);
    setRefunds(refundRows);
  }

  useEffect(() => {
    refresh().catch(() => setError('Unable to load payment records.'));
    const timer = window.setInterval(() => refresh().catch(() => {}), 3500);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, busy]);

  async function submitChat(text = message) {
    const clean = text.trim();
    if (!clean || busy) return;
    setMessages(current => [
      ...current,
      { role: 'customer', content: clean, created_at: new Date().toISOString() }
    ]);
    setMessage('');
    setBusy(true);
    setSuggestions([]);
    setError('');

    try {
      const result = await sendChat(clean);
      if (result.options) setSuggestions(result.options);
      if (result.transaction_id) {
        const matchingTx = transactions.find(t => t.transaction_id === result.transaction_id);
        if (matchingTx) setSelectedCaseTx(matchingTx);
      }
      await refresh();
    } catch {
      setError('I couldn’t reach the ZeroTouch resolution engine. Please check backend connection.');
    } finally {
      setBusy(false);
    }
  }

  // Active / selected transaction details for right inspector
  const latestTxId = [...messages].reverse().find(m => m.transaction_id)?.transaction_id || selectedCaseTx?.transaction_id || (transactions[0]?.transaction_id);
  const activeTx = transactions.find(t => t.transaction_id === latestTxId) || transactions[0];
  const activeCase = cases.find(c => c.transaction_id === (activeTx?.transaction_id));

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white text-slate-900 font-sans">

      {/* ── ChatGPT-Style Collapsible Left Sidebar ── */}
      <aside
        className={`${
          sidebarOpen ? 'w-72' : 'w-0 -translate-x-full'
        } transition-all duration-300 ease-in-out shrink-0 bg-[#07356b] text-white flex flex-col h-full z-30 select-none overflow-hidden`}
      >
        {/* Sidebar Header */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-cyan-500 rounded-lg flex items-center justify-center text-white">
              <Bot size={16}/>
            </div>
            <div>
              <span className="font-extrabold text-sm tracking-tight text-white">ZeroTouch</span>
              <span className="text-[10px] font-semibold text-cyan-300 block -mt-0.5">CUSTOMER RESOLUTION</span>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-1.5 text-blue-200 hover:text-white hover:bg-white/10 rounded-lg transition"
            title="Close sidebar"
          >
            <PanelLeftClose size={17} />
          </button>
        </div>

        {/* New Resolution Button */}
        <div className="p-3 shrink-0">
          <button
            onClick={() => {
              setMessages([]);
              setSuggestions([]);
              setSelectedCaseTx(null);
            }}
            className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl border border-white/20 bg-white/10 hover:bg-white/15 text-white text-xs font-bold transition shadow-2xs group"
          >
            <div className="flex items-center gap-2">
              <Plus size={15} className="text-cyan-300" />
              <span>New Resolution</span>
            </div>
            <span className="text-[10px] text-blue-300 group-hover:text-white font-normal">Ask AI</span>
          </button>
        </div>

        {/* Cases & History List */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4">
          {/* Active Cases Section */}
          <div>
            <div className="text-[10px] font-extrabold uppercase tracking-wider text-blue-200/70 px-2 mb-2">
              Your Support Cases ({cases.length})
            </div>
            {cases.length === 0 ? (
              <p className="text-xs text-blue-200/60 px-2 italic">No cases opened yet.</p>
            ) : (
              <div className="space-y-1">
                {cases.map(c => {
                  const isActive = activeTx?.transaction_id === c.transaction_id;
                  return (
                    <button
                      key={c.case_id}
                      onClick={() => {
                        const target = transactions.find(t => t.transaction_id === c.transaction_id);
                        if (target) setSelectedCaseTx(target);
                        submitChat(`Check status of ${c.transaction_id}`);
                      }}
                      className={`w-full text-left p-2.5 rounded-xl transition flex flex-col gap-1 text-xs ${
                        isActive ? 'bg-white/20 text-white font-bold' : 'text-blue-100 hover:bg-white/10'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] text-cyan-300">{c.case_id}</span>
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${
                          c.status === 'RESOLVED' || c.status === 'NO_ACTION'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {c.status === 'RESOLVED' ? 'Resolved' : c.status === 'ESCALATED' ? 'Review' : 'Active'}
                        </span>
                      </div>
                      <div className="text-[11px] truncate text-slate-200 font-normal">
                        {c.issue} · {money(c.amount)}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div>
            <div className="text-[10px] font-extrabold uppercase tracking-wider text-blue-200/70 px-2 mb-2">
              My Refunds ({refunds.length})
            </div>
            {refunds.length === 0 ? (
              <p className="text-xs text-blue-200/60 px-2 italic">No refunds requested yet.</p>
            ) : (
              <div className="space-y-1">
                {refunds.map(refund => (
                  <div key={refund.refund_id} className="rounded-lg bg-white/5 px-2.5 py-2 text-[11px] text-blue-100">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-cyan-300">{refund.transaction_id}</span>
                      <span className="font-bold text-emerald-300">{refund.status}</span>
                    </div>
                    <div className="mt-1 flex items-center justify-between gap-2 text-blue-200/80">
                      <span className="font-mono">{refund.refund_id}</span><span>{money(refund.amount)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Transactions Selector */}
          <div>
            <div className="text-[10px] font-extrabold uppercase tracking-wider text-blue-200/70 px-2 mb-2">
              Recent Transactions ({transactions.length})
            </div>
            <div className="space-y-1">
              {transactions.slice(0, 6).map(tx => (
                <button
                  key={tx.transaction_id}
                  onClick={() => {
                    setSelectedCaseTx(tx);
                    submitChat(tx.transaction_id);
                  }}
                  className="w-full text-left px-2.5 py-2 rounded-lg text-xs text-blue-100 hover:bg-white/10 transition flex items-center justify-between"
                >
                  <span className="font-mono">{tx.transaction_id}</span>
                  <span className="text-[11px] font-semibold text-cyan-300">{money(tx.amount)}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar Footer User Card */}
        <div className="p-3 border-t border-white/10 shrink-0 bg-[#05284f]/60 space-y-2">
          {onSwitchToOps && (
            <button
              onClick={onSwitchToOps}
              className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-bold bg-white/10 hover:bg-white/20 text-cyan-200 transition"
            >
              <span>Support Ops Console</span>
              <ArrowUpRight size={13}/>
            </button>
          )}
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-cyan-400 text-[#07356b] flex items-center justify-center font-bold text-xs">
                {profile?.name?.[0] || 'A'}
              </div>
              <div className="text-left">
                <div className="text-xs font-bold text-white truncate max-w-[120px]">{profile?.name || 'Ayush'}</div>
                <div className="text-[10px] text-blue-300 font-mono">Customer Account</div>
              </div>
            </div>
            <button
              onClick={onLogout}
              className="p-1.5 text-blue-200 hover:text-white hover:bg-white/10 rounded-lg transition"
              title="Sign out"
            >
              <LogOut size={15}/>
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Chat Area (ChatGPT-Style Full-Height Expansive Canvas) ── */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#fdfdfd] relative">

        {/* Top Navbar */}
        <header className="h-14 border-b border-slate-100 bg-white/95 backdrop-blur px-4 flex items-center justify-between shrink-0 z-20">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
                title="Open sidebar"
              >
                <PanelLeft size={18} />
              </button>
            )}

            {/* Model Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl hover:bg-slate-50 border border-transparent hover:border-slate-200 transition cursor-default">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"/>
              <span className="text-xs font-bold text-slate-800">ZeroTouch 2.0</span>
              <span className="text-[10px] font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full font-mono">
                Autonomous AI Teammate
              </span>
            </div>
          </div>

          {/* Right Action Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setInspectorOpen(!inspectorOpen)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition ${
                inspectorOpen
                  ? 'bg-blue-50 text-[#07356b] border-blue-200'
                  : 'text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
              title="Toggle Ledger & Policy Inspector"
            >
              <SlidersHorizontal size={13}/>
              <span>4-Ledger Inspector</span>
              {activeTx && <span className="w-1.5 h-1.5 rounded-full bg-cyan-500"/>}
            </button>

            {onSwitchToOps && (
              <button
                onClick={onSwitchToOps}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-[#07356b] text-white hover:bg-[#05284f] transition shadow-xs"
              >
                <span>Ops Portal</span>
                <ArrowRight size={12}/>
              </button>
            )}
          </div>
        </header>

        {/* Message Stream (Centered Max-Width Container) */}
        <div className="flex-1 overflow-y-auto px-4 py-6 scroll-smooth">
          <div className="max-w-3xl mx-auto w-full space-y-6">

            {/* Empty State ChatGPT Welcome Hero */}
            {messages.length === 0 && (
              <div className="py-8 text-center animate-fade-in">
                <div className="w-14 h-14 bg-[#07356b] rounded-2xl flex items-center justify-center text-cyan-300 mx-auto mb-4 shadow-md">
                  <Bot size={28}/>
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-800 tracking-tight">
                  Hi {profile?.name || 'Ayush'}, how can I help?
                </h1>
                <p className="mt-2 text-sm text-slate-500 max-w-lg mx-auto leading-relaxed">
                  ZeroTouch autonomously investigates payment glitches, delayed refunds, and merchant settlement shortfalls across 4 core banking ledgers.
                </p>

                {/* 2x3 Grid of Interactive ChatGPT-Style Prompt Cards */}
                <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                  {SCENARIO_CARDS.map((card, idx) => (
                    <button
                      key={idx}
                      disabled={busy}
                      onClick={() => submitChat(card.prompt)}
                      className="p-4 rounded-2xl border border-slate-200 bg-white hover:border-cyan-400 hover:shadow-md transition text-left group flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xl">{card.icon}</span>
                          <span className="text-[10px] font-mono font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                            {card.amount}
                          </span>
                        </div>
                        <div className="text-xs font-bold text-slate-800 group-hover:text-[#07356b] transition">
                          {card.title}
                        </div>
                        <p className="text-[11px] text-slate-500 mt-1 leading-4">
                          {card.prompt}
                        </p>
                      </div>
                      <div className="mt-3 pt-2 border-t border-slate-100 text-[10px] font-semibold text-cyan-700 flex items-center justify-between">
                        <span>{card.sub}</span>
                        <ChevronRight size={12} className="opacity-60 group-hover:translate-x-0.5 transition-transform"/>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Conversation Messages */}
            {messages.map((item, index) => {
              const isUser = item.role === 'customer';
              const matchedTx = item.transaction_id ? transactions.find(t => t.transaction_id === item.transaction_id) : null;
              const matchedCase = item.transaction_id ? cases.find(c => c.transaction_id === item.transaction_id) : null;

              return (
                <div
                  key={`${item.created_at}-${index}`}
                  className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  {!isUser && (
                    <div className="w-8 h-8 rounded-xl bg-[#07356b] text-cyan-300 flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                      <Bot size={16}/>
                    </div>
                  )}

                  <div className={`max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
                    <div
                      className={`rounded-2xl px-5 py-3.5 text-sm leading-relaxed ${
                        isUser
                          ? 'bg-[#07356b] text-white rounded-tr-xs shadow-sm font-medium'
                          : 'bg-slate-50/90 text-slate-800 rounded-tl-xs border border-slate-200/80 shadow-2xs'
                      }`}
                    >
                      {!isUser && (
                        <div className="text-[10px] font-extrabold uppercase tracking-wider text-cyan-700 mb-1 flex items-center gap-1.5">
                          <span>ZeroTouch AI Resolution</span>
                        </div>
                      )}
                      <p className="whitespace-pre-wrap">{item.content}</p>
                    </div>

                    {/* Inline Verification Card for Assistant Answers referencing a transaction */}
                    {!isUser && matchedTx && (
                      <VerificationCard
                        tx={matchedTx}
                        caseId={matchedCase?.case_id}
                        status={matchedCase?.status || matchedTx.resolution_status}
                        activity={matchedCase?.timeline}
                      />
                    )}
                  </div>

                  {isUser && (
                    <div className="w-8 h-8 rounded-xl bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5 font-bold text-xs">
                      {profile?.name?.[0] || 'A'}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Suggestions buttons if ambiguous */}
            {suggestions.length > 0 && (
              <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-2">
                <span className="text-xs font-bold text-slate-700 block">Select the transaction you are inquiring about:</span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {suggestions.map(tx => (
                    <button
                      key={tx.transaction_id}
                      onClick={() => submitChat(tx.transaction_id)}
                      disabled={busy}
                      className="flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:border-cyan-500 hover:bg-cyan-50 transition text-left"
                    >
                      <div>
                        <span className="font-mono text-xs font-bold text-[#07356b] block">{tx.transaction_id}</span>
                        <span className="text-[10px] text-slate-400 capitalize">{tx.workflow_type} Exception</span>
                      </div>
                      <span className="text-xs font-extrabold text-slate-800">{money(tx.amount)}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Live Investigation Pulsing Status */}
            {busy && (
              <div className="flex gap-3 justify-start items-center">
                <div className="w-8 h-8 rounded-xl bg-[#07356b] text-cyan-300 flex items-center justify-center shrink-0 animate-pulse">
                  <Bot size={16}/>
                </div>
                <div className="rounded-2xl rounded-tl-xs bg-white border border-blue-200 px-4 py-3 text-xs text-slate-700 shadow-xs flex items-center gap-3">
                  <span className="w-2.5 h-2.5 rounded-full bg-cyan-500 animate-ping"/>
                  <span className="font-medium">
                    Reconciling 4 payment ledgers & evaluating deterministic safety rules…
                  </span>
                </div>
              </div>
            )}

            {error && (
              <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 font-semibold">
                {error}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Bottom Floating ChatGPT-Style Input Bar */}
        <div className="shrink-0 bg-gradient-to-t from-white via-white/95 to-transparent pt-3 pb-6 px-4">
          <div className="max-w-3xl mx-auto w-full">
            <form
              onSubmit={e => {
                e.preventDefault();
                submitChat();
              }}
              className="relative flex items-center rounded-2xl border border-slate-200/90 bg-white shadow-md focus-within:border-cyan-500 focus-within:ring-4 focus-within:ring-cyan-500/10 transition-all p-1.5"
            >
              <textarea
                value={message}
                onChange={e => setMessage(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    submitChat();
                  }
                }}
                disabled={busy}
                placeholder="Ask ZeroTouch to resolve a payment, refund, or settlement issue…"
                aria-label="Describe your payment issue"
                rows={1}
                className="flex-1 bg-transparent px-3 py-2.5 text-sm text-slate-800 placeholder-slate-400 outline-none resize-none max-h-32 min-h-[44px]"
              />

              <button
                type="submit"
                disabled={busy || !message.trim()}
                aria-label="Send message"
                className="w-10 h-10 rounded-xl bg-[#07356b] hover:bg-[#05284f] text-white flex items-center justify-center transition disabled:opacity-40 disabled:hover:bg-[#07356b] shrink-0"
              >
                <Send size={16}/>
              </button>
            </form>

            <div className="mt-2 text-center text-[10px] text-slate-400 flex items-center justify-center gap-1.5">
              <ShieldCheck size={11} className="text-emerald-600"/>
              <span>ZeroTouch AI uses deterministic policy ceilings & Action Gateway verification before executing financial movements.</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Slide-Over 4-Ledger Inspector Panel (Canvas/Copilot Style) ── */}
      {inspectorOpen && (
        <aside className="w-80 border-l border-slate-200 bg-white flex flex-col h-full z-20 shrink-0 shadow-lg animate-slide-left">
          <div className="h-14 px-4 border-b border-slate-100 flex items-center justify-between shrink-0 bg-slate-50/50">
            <div className="flex items-center gap-2">
              <SlidersHorizontal size={14} className="text-[#07356b]"/>
              <span className="text-xs font-bold text-slate-800">Ledger & State Inspector</span>
            </div>
            <button
              onClick={() => setInspectorOpen(false)}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"
            >
              ✕
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
            {activeTx ? (
              <>
                <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Selected Case</span>
                    <CaseStatusBadge status={activeCase?.status || activeTx.resolution_status} />
                  </div>
                  <div className="font-mono font-extrabold text-sm text-[#07356b]">
                    {activeCase?.case_id || `ZT-${activeTx.transaction_id.slice(-5)}`}
                  </div>
                  <div className="text-slate-600 font-semibold">{money(activeTx.amount)}</div>
                </div>

                <div>
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 block mb-2">
                    Core Banking Ledgers
                  </span>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 space-y-1">
                    <LedgerRow label="Bank Debit" value={activeTx.bank_status} />
                    <LedgerRow label="NPCI Network" value={activeTx.network_status} />
                    <LedgerRow label="Merchant" value={activeTx.merchant_status} />
                    <LedgerRow label="Settlement" value={activeTx.settlement_status} />
                  </div>
                </div>

                {activeTx.action_id && (
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 space-y-1">
                    <span className="text-[10px] font-bold text-emerald-800 uppercase block">Verified Action</span>
                    <div className="font-mono font-bold text-xs text-emerald-900">{activeTx.action_id}</div>
                    <p className="text-[10px] text-emerald-700">Verified by Action Gateway with idempotency protection.</p>
                  </div>
                )}

                {activeCase?.timeline && (
                  <div>
                    <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 block mb-2">
                      Event Log ({activeCase.timeline.length})
                    </span>
                    <div className="space-y-1.5 border-l-2 border-slate-200 pl-3">
                      {activeCase.timeline.map((ev, i) => (
                        <div key={i} className="text-[11px] text-slate-600">
                          <span className="font-medium text-slate-800">{ev.label}</span>
                          <span className="text-[9px] text-slate-400 block">{ev.status}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="text-slate-400 italic text-center py-8">Select or ask about any transaction to inspect live ledgers.</p>
            )}
          </div>
        </aside>
      )}

    </div>
  );
}
