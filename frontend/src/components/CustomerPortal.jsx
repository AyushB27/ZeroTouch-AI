import React, { useEffect, useState } from 'react';
import { ArrowRight, Bot, Check, CheckCircle2, Clock3, LogOut, MessageCircle, Send, ShieldAlert, Sparkles, WalletCards, XCircle } from 'lucide-react';
import { getCustomerCases, getCustomerMessages, getCustomerProfile, getCustomerTransactions, sendChat } from '../api';

const PROMPTS = [
  'My ₹2,500 payment was deducted but the merchant didn’t receive it.',
  'My refund hasn’t arrived yet.',
  'My payment failed but money was deducted.',
  'Why did I receive ₹9,650 instead of ₹10,000?',
  'I want to talk to a human.',
];
const money = value => `₹${Number(value).toLocaleString('en-IN')}`;

function CaseStatus({ status }) {
  const resolved = status === 'RESOLVED' || status === 'NO_ACTION';
  const waiting = status === 'ESCALATED';
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold ${resolved ? 'bg-emerald-50 text-emerald-700' : waiting ? 'bg-amber-50 text-amber-800' : 'bg-slate-100 text-slate-600'}`}>{resolved ? <CheckCircle2 size={12}/> : waiting ? <Clock3 size={12}/> : <Clock3 size={12}/>} {resolved ? 'Resolved' : waiting ? 'Human review' : 'Investigating'}</span>;
}

function ActivityCard({ response, working }) {
  if (working) return <section className="rounded-2xl border border-blue-100 bg-white p-5 shadow-sm"><div className="flex items-center gap-2 text-sm font-bold text-[#07356b]"><span className="h-2 w-2 animate-pulse rounded-full bg-cyan-500"/>ZeroTouch is investigating</div><div className="mt-4 space-y-3 text-xs text-slate-500">{['Identifying the payment', 'Checking bank, network and merchant records', 'Applying policy and verifying the outcome'].map((step, index) => <div key={step} className="flex items-center gap-2"><span className={`grid h-5 w-5 place-items-center rounded-full ${index === 0 ? 'bg-cyan-50 text-cyan-700' : 'bg-slate-50 text-slate-400'}`}>{index + 1}</span>{step}</div>)}</div></section>;
  if (!response) return <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-2 text-sm font-bold text-slate-800"><Sparkles size={16} className="text-cyan-600"/>Investigation activity</div><p className="mt-3 text-xs leading-5 text-slate-500">As soon as you send a payment question, ZeroTouch checks the evidence, evaluates the policy and shows you what it did.</p></section>;
  const items = response.activity || [];
  return <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between gap-2"><div className="flex items-center gap-2 text-sm font-bold text-slate-800"><Sparkles size={16} className="text-cyan-600"/>Investigation activity</div><CaseStatus status={response.status}/></div><div className="mt-4 space-y-3">{items.map((item, index) => <div key={`${item.label}-${index}`} className="flex items-start gap-2.5"><span className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full ${item.status === 'FAILED' ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-600'}`}>{item.status === 'FAILED' ? <XCircle size={13}/> : <Check size={13}/>}</span><div><p className="text-xs font-semibold text-slate-800">{item.label || 'Payment update'}</p></div></div>)}</div><div className="mt-4 border-t border-slate-100 pt-3 text-[11px] text-slate-500">Case <span className="font-mono font-bold text-slate-700">{response.case_id}</span> · Payment <span className="font-mono font-bold text-slate-700">{response.transaction_id}</span></div></section>;
}

export default function CustomerPortal({ user, onLogout }) {
  const [profile, setProfile] = useState(user);
  const [transactions, setTransactions] = useState([]);
  const [cases, setCases] = useState([]);
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [activity, setActivity] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [error, setError] = useState('');

  async function refresh() {
    const [p, tx, cs, msgs] = await Promise.all([getCustomerProfile(), getCustomerTransactions(), getCustomerCases(), getCustomerMessages()]);
    setProfile(p); setTransactions(tx); setCases(cs); setMessages(msgs);
  }
  useEffect(() => {
    refresh().catch(() => setError('Your payment information is temporarily unavailable. Please try again shortly.'));
    const timer = window.setInterval(() => refresh().catch(() => {}), 3500);
    return () => window.clearInterval(timer);
  }, []);

  async function submitChat(text = message) {
    const clean = text.trim(); if (!clean || busy) return;
    setMessages(current => [...current, { role: 'customer', content: clean, created_at: new Date().toISOString() }]);
    setMessage(''); setBusy(true); setActivity(null); setSuggestions([]); setError(''); setActiveTab('chat');
    try {
      const result = await sendChat(clean);
      setActivity(result.needs_selection ? null : result);
      setSuggestions(result.options || []);
      await refresh();
    } catch { setError('I couldn’t reach the payment service just now. Please try again shortly.'); }
    finally { setBusy(false); }
  }

  const activeCases = cases.filter(item => item.status === 'ESCALATED' || item.status === 'PENDING');
  const resolvedCases = cases.filter(item => item.status === 'RESOLVED' || item.status === 'NO_ACTION');
  const latestTxId = activity?.transaction_id || [...messages].reverse().find(item => item.transaction_id)?.transaction_id;
  const focusedTx = transactions.find(tx => tx.transaction_id === latestTxId);
  const focusedCase = cases.find(item => item.transaction_id === latestTxId);
  const activityView = suggestions.length ? null : activity || (focusedCase ? {
    case_id: focusedCase.case_id, transaction_id: focusedCase.transaction_id,
    status: focusedCase.status, activity: focusedCase.timeline,
  } : null);
  const friendlyStatus = value => ({ DEBITED: 'Confirmed', SUCCESS: 'Confirmed', CREDITED: 'Received', NOT_CREDITED: 'Not received', NOT_FOUND: 'Not found', SETTLED: 'Settled', PENDING_CREDIT: 'Pending' }[value] || 'Checking');

  return <div className="min-h-screen bg-[#f4f8fc] text-slate-900">
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/95 backdrop-blur"><div className="mx-auto flex h-[68px] max-w-7xl items-center justify-between px-4 sm:px-7"><div className="flex items-center gap-3"><div className="grid h-9 w-9 place-items-center rounded-xl bg-[#07356b] text-cyan-300"><WalletCards size={19}/></div><div><div className="text-sm font-extrabold tracking-tight">ZeroTouch</div><div className="text-[10px] font-semibold tracking-wider text-slate-400">PAYMENT SUPPORT</div></div></div><nav className="hidden items-center gap-1 sm:flex">{[['chat', 'Assistant'], ['cases', `Cases${cases.length ? ` · ${cases.length}` : ''}`], ['transactions', 'Transactions']].map(([id, label]) => <button key={id} onClick={() => setActiveTab(id)} className={`rounded-lg px-3 py-2 text-xs font-bold ${activeTab === id ? 'bg-blue-50 text-[#07356b]' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'}`}>{label}</button>)}</nav><div className="flex items-center gap-2"><div className="hidden text-right sm:block"><div className="text-xs font-bold">{profile?.name || 'Vansh'}</div><div className="text-[10px] text-slate-400">Customer account</div></div><button onClick={onLogout} aria-label="Sign out" title="Sign out" className="grid h-9 w-9 place-items-center rounded-lg text-slate-500 hover:bg-slate-100"><LogOut size={16}/></button></div></div></header>

    <main className="mx-auto max-w-7xl px-4 py-7 sm:px-7 sm:py-10">
      <div className="mb-6 flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[.18em] text-cyan-700">Your payment companion</p><h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">Hello {profile?.name || 'Vansh'} <span aria-hidden="true">👋</span></h1><p className="mt-1.5 text-sm text-slate-500">Tell us what happened. ZeroTouch will investigate it across your payment records.</p></div><div className="hidden items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-[11px] font-bold text-emerald-700 sm:flex"><span className="h-2 w-2 rounded-full bg-emerald-500"/>Secure demo environment</div></div>

      <div className="mb-5 grid grid-cols-3 gap-3 sm:gap-4">{[[transactions.length, 'Transactions'], [activeCases.length, 'Needs attention'], [resolvedCases.length, 'Resolved cases']].map(([value, label]) => <div key={label} className="rounded-xl border border-slate-200/80 bg-white px-3 py-3.5 shadow-sm sm:px-5"><div className="text-xl font-extrabold text-[#07356b]">{value}</div><div className="mt-1 text-[11px] text-slate-500 sm:text-xs">{label}</div></div>)}</div>

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,2.3fr)_minmax(280px,.9fr)]">
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div className="flex items-center gap-2.5"><div className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-50 text-cyan-700"><Bot size={17}/></div><div><div className="text-sm font-bold">ZeroTouch assistant</div><div className="text-[11px] text-slate-500">Your autonomous payment teammate</div></div></div><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold text-emerald-700">Ready to help</span></div>
          <div className="min-h-[310px] max-h-[470px] space-y-4 overflow-y-auto bg-[#fbfdff] px-4 py-5 sm:px-6" aria-live="polite">
            {messages.length === 0 && <div className="mx-auto max-w-md py-5 text-center"><div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-[#07356b] text-cyan-300"><MessageCircle size={22}/></div><h2 className="mt-4 text-lg font-bold">Hi {profile?.name || 'there'}, what can I check?</h2><p className="mt-1 text-sm text-slate-500">I can help with payments, refunds and settlement issues.</p></div>}
            {messages.map((item, index) => <div key={`${item.created_at}-${index}`} className={`flex ${item.role === 'customer' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-6 ${item.role === 'customer' ? 'rounded-br-md bg-[#07356b] text-white' : 'rounded-bl-md border border-slate-200 bg-white text-slate-700 shadow-sm'}`}>{item.role === 'assistant' && <div className="mb-1 text-[10px] font-extrabold uppercase tracking-wider text-cyan-700">ZeroTouch</div>}{item.content}</div></div>)}
            {suggestions.length > 0 && <div className="space-y-2">{suggestions.map(tx => <button key={tx.transaction_id} onClick={() => submitChat(tx.transaction_id)} disabled={busy} className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 text-left hover:border-cyan-400 hover:bg-cyan-50 disabled:opacity-50"><span><span className="block text-xs font-bold text-slate-800">{tx.workflow_type === 'W3' ? 'Merchant settlement' : tx.workflow_type === 'W2' ? 'Refund' : 'Payment'} · {tx.transaction_id}</span><span className="mt-1 block text-[10px] text-slate-500">{tx.resolution_status === 'PENDING' ? 'Needs review' : tx.resolution_status.toLowerCase().replaceAll('_', ' ')}</span></span><span className="text-sm font-bold text-[#07356b]">{money(tx.amount)}</span></button>)}</div>}
            {busy && <div className="flex justify-start"><div className="rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 text-xs font-medium text-slate-600 shadow-sm"><span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-cyan-500"/>ZeroTouch is checking your payment records…</div></div>}
            {error && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">{error}</p>}
          </div>
          {messages.length === 0 && <div className="border-t border-slate-100 px-4 py-4 sm:px-6"><div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">Try asking</div><div className="flex flex-wrap gap-2">{PROMPTS.map(prompt => <button key={prompt} disabled={busy} onClick={() => submitChat(prompt)} className="rounded-full border border-slate-200 bg-white px-3 py-2 text-left text-[11px] font-semibold text-slate-600 transition hover:border-cyan-300 hover:bg-cyan-50 hover:text-[#07356b] disabled:opacity-50">{prompt}</button>)}</div></div>}
          <form onSubmit={event => { event.preventDefault(); submitChat(); }} className="flex items-center gap-2 border-t border-slate-100 p-3 sm:p-4"><input value={message} onChange={e => setMessage(e.target.value)} disabled={busy} placeholder="Describe your payment issue…" aria-label="Describe your payment issue" className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-cyan-500 focus:bg-white focus:ring-4 focus:ring-cyan-500/10 disabled:opacity-60"/><button disabled={busy || !message.trim()} aria-label="Send message" className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-[#07356b] text-white transition hover:bg-[#05284f] disabled:opacity-40"><Send size={17}/></button></form>
        </section>

        <div className="space-y-4"><ActivityCard response={activityView} working={busy}/>
          {focusedTx && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-start justify-between gap-3"><div><h2 className="text-sm font-bold">Payment details</h2><p className="mt-1 font-mono text-[11px] text-slate-500">{focusedTx.transaction_id}</p></div><div className="text-right"><div className="text-lg font-extrabold text-[#07356b]">{money(focusedTx.amount)}</div><p className="text-[10px] text-slate-500">{focusedCase?.case_id || 'Payment issue'}</p></div></div><div className="mt-4 space-y-2 border-t border-slate-100 pt-3">{[['Bank', focusedTx.bank_status], ['Network', focusedTx.network_status], ['Merchant', focusedTx.merchant_status]].map(([label, value]) => <div key={label} className="flex items-center justify-between text-xs"><span className="text-slate-500">{label}</span><span className={`font-semibold ${['NOT_CREDITED', 'FAILED', 'BOUNCED'].some(flag => value.includes(flag)) ? 'text-rose-600' : 'text-emerald-700'}`}>{friendlyStatus(value)}</span></div>)}</div><div className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs"><span className="text-slate-500">Resolution · </span><span className="font-semibold text-slate-700">{focusedTx.resolution_status === 'ESCALATED' ? 'Support review' : focusedTx.resolution_status === 'RESOLVED' ? 'Reversal or action completed' : focusedTx.resolution_status === 'NO_ACTION' ? 'No action needed' : 'Investigation in progress'}</span></div></section>}
          {activeTab === 'chat' && <><section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><h2 className="text-sm font-bold">Recent transactions</h2><button onClick={() => setActiveTab('transactions')} className="flex items-center gap-1 text-[11px] font-bold text-cyan-700">All transactions <ArrowRight size={13}/></button></div><div className="mt-3 divide-y divide-slate-100">{transactions.slice(0, 3).map(tx => <div key={tx.transaction_id} className="flex items-center justify-between py-3"><div><div className="text-xs font-bold text-slate-800">{tx.transaction_id}</div><div className="mt-0.5 text-[10px] text-slate-500">{tx.workflow_type === 'W2' ? 'Refund' : tx.workflow_type === 'W3' ? 'Settlement' : 'UPI payment'}</div></div><div className="text-right"><div className="text-xs font-bold">{money(tx.amount)}</div><CaseStatus status={tx.resolution_status}/></div></div>)}</div></section>
          <section className="rounded-2xl border border-blue-100 bg-[#edf7ff] p-4"><div className="flex gap-2.5"><ShieldAlert size={16} className="mt-0.5 shrink-0 text-[#07356b]"/><p className="text-xs leading-5 text-slate-600"><span className="font-bold text-[#07356b]">Controlled autonomy.</span> ZeroTouch checks the evidence and policy before taking action. High-risk cases go to a support agent.</p></div></section></>}
          {activeTab === 'cases' && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-sm font-bold">Your support cases</h2>{cases.length === 0 ? <p className="mt-4 text-xs text-slate-500">No cases yet. Ask ZeroTouch to investigate a payment.</p> : <div className="mt-3 space-y-3">{cases.map(item => <article key={item.case_id} className="rounded-xl border border-slate-100 p-3"><div className="flex items-start justify-between gap-2"><div><div className="text-xs font-bold">{item.case_id} <span className="font-normal text-slate-400">· {item.transaction_id}</span></div><div className="mt-1 text-[11px] text-slate-500">{item.issue} · {money(item.amount)}</div></div><CaseStatus status={item.status}/></div>{item.action_id && <div className="mt-2 text-[10px] text-emerald-700">Action reference: {item.action_id}</div>}<details className="mt-3 border-t border-slate-100 pt-2"><summary className="cursor-pointer text-[11px] font-semibold text-[#07356b]">Investigation timeline · {item.timeline?.length || 0} events</summary><ol className="mt-2 space-y-2 pl-1">{(item.timeline || []).map((event, index) => <li key={`${event.timestamp}-${index}`} className="border-l-2 border-blue-100 pl-3"><div className="text-[10px] font-bold capitalize text-slate-700">{event.label || 'Payment update'} <span className="font-medium text-slate-400">· {event.status.toLowerCase()}</span></div></li>)}</ol></details></article>)}</div>}</section>}
          {activeTab === 'transactions' && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-sm font-bold">Transactions</h2><div className="mt-3 divide-y divide-slate-100">{transactions.map(tx => <div key={tx.transaction_id} className="flex items-center justify-between py-3"><div><div className="text-xs font-bold">{tx.transaction_id}</div><div className="mt-0.5 text-[10px] text-slate-500">{tx.workflow_type === 'W2' ? 'Refund' : tx.workflow_type === 'W3' ? 'Merchant settlement' : 'UPI payment'} · {tx.bank_status.toLowerCase().replaceAll('_', ' ')}</div></div><div className="text-right"><div className="text-xs font-bold">{money(tx.amount)}</div><CaseStatus status={tx.resolution_status}/></div></div>)}</div></section>}
        </div>
      </div>
      <footer className="mt-8 text-center text-[10px] text-slate-400">Demo environment · Fictional payment records · <button className="font-bold text-slate-500 sm:hidden" onClick={() => setActiveTab(activeTab === 'chat' ? 'cases' : 'chat')}>{activeTab === 'chat' ? 'View cases' : 'Back to assistant'}</button></footer>
    </main>
  </div>;
}
