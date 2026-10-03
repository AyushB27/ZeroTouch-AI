import React, { useEffect, useRef, useState } from 'react';
import { Activity, ArrowUp, Bot, Check, ChevronDown, CircleHelp, Clock3, FileText, LayoutDashboard, LoaderCircle, LogOut, Menu, PanelLeftClose, PanelLeftOpen, Plus, Search, Settings, ShieldCheck, Sparkles, Users, WalletCards, Wrench, X } from 'lucide-react';
import { getAssistantConversation, sendAssistantMessage } from '../api';

const departments = [
  { id: 'all', label: 'Ask ZeroTouch', icon: Sparkles },
  { id: 'finance', label: 'Finance', icon: WalletCards },
  { id: 'hr', label: 'HR', icon: Users },
  { id: 'it', label: 'IT', icon: Wrench },
  { id: 'support', label: 'Customer Support', icon: CircleHelp },
  { id: 'analytics', label: 'Analytics', icon: Activity },
  { id: 'sales', label: 'Sales', icon: LayoutDashboard },
  { id: 'marketing', label: 'Marketing', icon: Sparkles },
  { id: 'operations', label: 'Operations', icon: ShieldCheck },
];
const suggestions = [
  'Resolve customer issue for TX9281',
  'Process refund for TX9281',
  "Prepare today's support report",
  'Onboard Rahul Sharma into Finance',
  'Find transaction TX9281',
  'Create an IT access request for Priya',
];
const statusStyle = {
  RUNNING: 'bg-blue-50 text-blue-700', COMPLETED: 'bg-emerald-50 text-emerald-700',
  WAITING: 'bg-amber-50 text-amber-800', NEEDS_INPUT: 'bg-amber-50 text-amber-800',
  FAILED: 'bg-rose-50 text-rose-700', ESCALATED: 'bg-violet-50 text-violet-700',
};

export default function EmployeeWorkspace({ user, onLogout }) {
  const [department, setDepartment] = useState('all');
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(() => localStorage.getItem('zerotouch_employee_conversation'));
  const [task, setTask] = useState(null);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const bottomRef = useRef(null);
  const currentDepartment = departments.find(item => item.id === department) || departments[0];
  const DepartmentIcon = currentDepartment.icon;

  useEffect(() => {
    if (!conversationId) return;
    getAssistantConversation(conversationId).then(data => { setMessages(data.messages || []); setTask(data.task || null); }).catch(() => {
      localStorage.removeItem('zerotouch_employee_conversation'); setConversationId(null);
    });
  }, []);
  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);

  function startNew() {
    setConversationId(null); setMessages([]); setTask(null); setError('');
    localStorage.removeItem('zerotouch_employee_conversation'); setSidebarOpen(false);
  }

  async function send(text = draft) {
    const clean = text.trim();
    if (!clean || busy) return;
    setError(''); setBusy(true);
    setMessages(previous => [...previous, { role: 'user', content: clean, created_at: new Date().toISOString() }]);
    setDraft('');
    try {
      const data = await sendAssistantMessage(clean, department, conversationId);
      setConversationId(data.conversation_id); localStorage.setItem('zerotouch_employee_conversation', data.conversation_id);
      setTask(data.task);
      setMessages(previous => [...previous, { role: 'assistant', content: data.reply, created_at: new Date().toISOString() }]);
    } catch (err) {
      setError(err.message || 'Could not reach ZeroTouch.');
      setMessages(previous => previous.slice(0, -1)); setDraft(clean);
    } finally { setBusy(false); }
  }

  const sidebar = <aside className={`flex h-full shrink-0 flex-col border-r border-slate-200 bg-white transition-[width] ${sidebarCollapsed ? 'w-[76px]' : 'w-[256px]'}`}>
    <div className={`flex h-[68px] items-center gap-3 border-b border-slate-100 ${sidebarCollapsed?'justify-center px-2':'px-5'}`}>
      <div className="grid h-9 w-9 place-items-center rounded-xl bg-[#07356b] text-white"><Sparkles size={18}/></div>
      {!sidebarCollapsed&&<div><div className="text-sm font-extrabold tracking-tight text-slate-900">ZeroTouch</div><div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Employee workspace</div></div>}
      <button onClick={()=>setSidebarCollapsed(value=>!value)} className={`hidden rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 lg:block ${sidebarCollapsed?'absolute left-[52px]':''}`} title={sidebarCollapsed?'Expand sidebar':'Collapse sidebar'} aria-label={sidebarCollapsed?'Expand sidebar':'Collapse sidebar'}>{sidebarCollapsed?<PanelLeftOpen size={15}/>:<PanelLeftClose size={15}/>}</button>
      <button className="ml-auto rounded-lg p-2 text-slate-400 hover:bg-slate-100 lg:hidden" onClick={() => setSidebarOpen(false)} aria-label="Close menu"><X size={16}/></button>
    </div>
    <div className={`pt-4 ${sidebarCollapsed?'px-2':'px-3'}`}><button onClick={startNew} title="New task" className={`flex w-full items-center justify-center gap-2 rounded-xl bg-[#07356b] py-2.5 text-xs font-bold text-white shadow-sm hover:bg-[#0b467f] ${sidebarCollapsed?'px-2':'px-3'}`}><Plus size={15}/>{!sidebarCollapsed&&'New task'}</button></div>
    <div className={`pt-5 ${sidebarCollapsed?'px-2':'px-3'}`}><div className="mb-2 px-2 text-[10px] font-bold uppercase tracking-[.16em] text-slate-400">{sidebarCollapsed?'':'Workspace'}</div>
      <button title="Home" onClick={() => {setDepartment('all'); setSidebarOpen(false)}} className={`mb-1 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs font-bold ${department === 'all' ? 'bg-blue-50 text-[#07356b]' : 'text-slate-600 hover:bg-slate-50'}`}><Sparkles size={16}/>{!sidebarCollapsed&&'Home'}</button>
      {!sidebarCollapsed&&<div className="mb-1 mt-4 px-2 text-[10px] font-bold uppercase tracking-[.16em] text-slate-400">All Bots</div>}
      {departments.slice(1).map(({id,label,icon:Icon}) => <button title={label} key={id} onClick={() => {setDepartment(id);setSidebarOpen(false)}} className={`mb-0.5 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs font-semibold ${department === id ? 'bg-blue-50 text-[#07356b]' : 'text-slate-600 hover:bg-slate-50'}`}><Icon size={15} className="text-slate-400"/>{!sidebarCollapsed&&label}</button>)}
    </div>
    <div className={`mt-auto border-t border-slate-100 py-3 ${sidebarCollapsed?'px-2':'p-4'}`}>
      <button onClick={()=>setHelpOpen(true)} title="Help" className="mb-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-50 hover:text-slate-900"><CircleHelp size={14}/>{!sidebarCollapsed&&'Help'}</button>
      <button onClick={()=>setHelpOpen(true)} title="Settings" className="mb-3 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-50 hover:text-slate-900"><Settings size={14}/>{!sidebarCollapsed&&'Settings'}</button>
      <div title={user.name} className={`mb-3 flex items-center gap-2 rounded-xl bg-slate-50 p-2 ${sidebarCollapsed?'justify-center':'p-3'}`}><div className="grid h-8 w-8 place-items-center rounded-full bg-blue-100 text-xs font-bold text-blue-800">{(user.name || 'U').split(' ').map(v=>v[0]).slice(0,2).join('')}</div>{!sidebarCollapsed&&<><div className="min-w-0 flex-1"><div className="truncate text-xs font-bold text-slate-800">{user.name}</div><div className="truncate text-[10px] text-slate-500">{user.email}</div></div><ChevronDown size={14} className="text-slate-400"/></>}</div>
      <button onClick={onLogout} title="Sign out" className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-50 hover:text-slate-900"><LogOut size={14}/>{!sidebarCollapsed&&'Sign out'}</button>
    </div>
  </aside>;

  return <div className="flex h-screen min-h-[620px] overflow-hidden bg-[#f7f9fc] text-slate-900">
    {helpOpen&&<div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4" onMouseDown={event=>{if(event.target===event.currentTarget)setHelpOpen(false)}}><section className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"><div className="flex items-center justify-between"><h2 className="text-base font-bold">Workspace settings & help</h2><button onClick={()=>setHelpOpen(false)} aria-label="Close" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><X size={16}/></button></div><p className="mt-2 text-xs leading-5 text-slate-600">Choose a department from All Bots or ask ZeroTouch to coordinate a cross-team request. Every business action appears in the task panel and is recorded for review.</p><div className="mt-4 rounded-xl bg-blue-50 p-3 text-[11px] leading-5 text-blue-900"><strong>Model status:</strong> The workspace uses Grok when the backend has an xAI key configured. Otherwise, common demo tasks use the deterministic local workflow.</div><button onClick={()=>setHelpOpen(false)} className="mt-5 rounded-lg bg-[#07356b] px-4 py-2 text-xs font-bold text-white">Done</button></section></div>}
    {sidebarOpen && <button className="fixed inset-0 z-30 bg-slate-950/30 lg:hidden" onClick={() => setSidebarOpen(false)} aria-label="Dismiss menu"/>}
    <div className={`fixed inset-y-0 left-0 z-40 transition-transform lg:static lg:z-auto lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>{sidebar}</div>
    <main className="flex min-w-0 flex-1 flex-col">
      <header className="flex h-[68px] shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 sm:px-7">
        <button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden" onClick={() => setSidebarOpen(true)} aria-label="Open menu"><Menu size={18}/></button>
        <div className="grid h-9 w-9 place-items-center rounded-xl bg-blue-50 text-blue-700"><DepartmentIcon size={18}/></div>
        <div className="min-w-0"><div className="truncate text-sm font-bold">{currentDepartment.label}</div><div className="text-[10px] text-slate-500">One workspace · specialist agents collaborate behind the scenes</div></div>
        <div className="ml-auto hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-[10px] font-bold text-emerald-700 sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500"/>Secure workspace</div>
      </header>
      <div className="flex min-h-0 flex-1">
        <section className="flex min-w-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8 lg:px-12">
            <div className="mx-auto max-w-3xl">
              {messages.length === 0 ? <div className="flex min-h-[55vh] flex-col justify-center pb-8">
                <div className="mb-5 grid h-12 w-12 place-items-center rounded-2xl bg-blue-100 text-[#07356b]"><Bot size={25}/></div>
                <p className="mb-2 text-xs font-bold uppercase tracking-[.14em] text-blue-700">Hi, I’m ZeroTouch</p>
                <h1 className="max-w-2xl text-3xl font-bold leading-tight tracking-tight sm:text-[38px]">Tell me what you need done.</h1>
                <p className="mt-3 max-w-xl text-sm leading-6 text-slate-500">Ask in plain language. ZeroTouch can coordinate HR, Finance, IT, Support, and Operations while keeping every action visible.</p>
                <div className="mt-8 grid gap-2 sm:grid-cols-2">{suggestions.map((item,index)=><button key={item} onClick={()=>send(item)} className="group flex min-h-[58px] items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-xs font-semibold text-slate-700 shadow-sm transition hover:border-blue-300 hover:bg-blue-50"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-500 group-hover:bg-white group-hover:text-blue-700">{index===0?<Users size={14}/>:index===1?<Search size={14}/>:index===2?<Wrench size={14}/>:<FileText size={14}/>}</span>{item}</button>)}</div>
              </div> : <div className="space-y-6 pb-8">{messages.map((item,index)=><div key={item.message_id || `${item.created_at}-${index}`} className={`flex gap-3 ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {item.role !== 'user' && <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-[#07356b] text-white"><Sparkles size={15}/></div>}
                <div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-6 ${item.role === 'user' ? 'rounded-br-md bg-[#07356b] text-white' : 'rounded-bl-md border border-slate-200 bg-white text-slate-700 shadow-sm'}`}><div className="whitespace-pre-wrap">{item.content}</div><div className={`mt-1.5 text-[9px] ${item.role === 'user' ? 'text-blue-200' : 'text-slate-400'}`}>{item.created_at ? new Date(item.created_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : ''}</div></div>
              </div>)}{busy && <div className="flex items-center gap-2 pl-11 text-xs text-slate-500"><LoaderCircle size={15} className="animate-spin"/> Coordinating specialist agents…</div>}<div ref={bottomRef}/></div>}
              {error && <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-700">{error}</div>}
            </div>
          </div>
          <div className="shrink-0 border-t border-slate-200 bg-white px-4 py-4 sm:px-8 lg:px-12"><form onSubmit={event=>{event.preventDefault();send()}} className="mx-auto max-w-3xl">
            <div className="flex items-end gap-3 rounded-2xl border border-slate-300 bg-white p-2 shadow-sm focus-within:border-blue-400 focus-within:ring-4 focus-within:ring-blue-100"><textarea value={draft} onChange={event=>setDraft(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}}} rows={1} placeholder={`Message ${currentDepartment.label}…`} className="max-h-36 min-h-10 flex-1 resize-y bg-transparent px-3 py-2 text-sm outline-none placeholder:text-slate-400"/><button type="submit" disabled={!draft.trim()||busy} aria-label="Send message" className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#07356b] text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-40"><ArrowUp size={18}/></button></div>
            <div className="mt-2 flex items-center justify-between px-1 text-[10px] text-slate-400"><span>Enter to send · Shift + Enter for a new line</span><span className="flex items-center gap-1"><ShieldCheck size={11}/> Actions are tracked</span></div>
          </form></div>
        </section>
        <aside className="hidden w-[310px] shrink-0 flex-col border-l border-slate-200 bg-white xl:flex">
          <div className="border-b border-slate-100 px-5 py-5"><div className="text-xs font-bold text-slate-900">Task activity</div><p className="mt-1 text-[10px] text-slate-500">Live plan, agents, and verified actions</p></div>
          {!task ? <div className="flex flex-1 flex-col items-center justify-center px-8 text-center"><div className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-slate-400"><Activity size={22}/></div><div className="text-xs font-bold text-slate-700">Ready when you are</div><p className="mt-1 text-[11px] leading-5 text-slate-500">Your plan and results will appear here after you send a request.</p></div> : <div className="min-h-0 flex-1 overflow-y-auto p-5">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3"><div className="mb-2 flex items-start justify-between gap-2"><span className="text-xs font-bold leading-5 text-slate-800">{task.title}</span><span className={`shrink-0 rounded-full px-2 py-1 text-[9px] font-bold ${statusStyle[task.status] || statusStyle.RUNNING}`}>{(task.status||'RUNNING').replace('_',' ')}</span></div><div className="font-mono text-[9px] text-slate-400">{task.task_id}</div></div>
            <div className="mt-5"><div className="mb-3 text-[10px] font-bold uppercase tracking-wider text-slate-400">Plan & timeline</div><div className="space-y-0">{(task.plan_steps||[]).map((step,index)=><div key={`${step.label}-${index}`} className="relative flex gap-3 pb-4 last:pb-0"><div className="relative flex w-4 shrink-0 justify-center"><span className={`relative z-10 mt-0.5 grid h-4 w-4 place-items-center rounded-full ${step.status==='COMPLETED'?'bg-emerald-100 text-emerald-700':step.status==='WAITING'?'bg-amber-100 text-amber-700':'bg-blue-100 text-blue-700'}`}>{step.status==='COMPLETED'?<Check size={10}/>:<Clock3 size={10}/>}</span>{index < task.plan_steps.length-1&&<span className="absolute top-4 h-full w-px bg-slate-200"/>}</div><div className="text-[11px] leading-4 text-slate-700">{step.label}<div className="mt-0.5 text-[9px] font-semibold uppercase text-slate-400">{step.status}</div></div></div>)}</div></div>
            {!!task.agents_involved?.length&&<div className="mt-5"><div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">Agents involved</div><div className="flex flex-wrap gap-1.5">{task.agents_involved.map(agent=><span key={agent} className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[9px] font-semibold text-slate-600">{agent}</span>)}</div></div>}
            {!!task.actions?.length&&<div className="mt-5"><div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">Business actions</div><div className="space-y-2">{task.actions.map((action,index)=><details key={`${action.tool}-${index}`} className="rounded-lg border border-slate-200 bg-white"><summary className="cursor-pointer list-none p-2.5"><div className="text-[10px] font-bold text-slate-700">{action.agent}</div><div className="mt-1 flex items-center justify-between gap-2"><span className="text-[9px] text-slate-500">{action.tool}</span><span className={`rounded px-1.5 py-0.5 text-[8px] font-bold ${action.status==='FAILED'?'bg-rose-50 text-rose-700':'bg-emerald-50 text-emerald-700'}`}>{action.status}</span></div></summary><pre className="max-h-48 overflow-auto border-t border-slate-100 p-2 text-[9px] text-slate-500">{JSON.stringify(action.result,null,2)}</pre></details>)}</div></div>}
            {task.result&&<div className="mt-5 rounded-xl border border-blue-100 bg-blue-50 p-3"><div className="mb-1 text-[10px] font-bold text-blue-900">Outcome</div><p className="whitespace-pre-wrap text-[10px] leading-5 text-blue-900">{task.result}</p></div>}
          </div>}
          <div className="flex items-center gap-2 border-t border-slate-100 px-5 py-3 text-[9px] text-slate-400"><ShieldCheck size={13} className="text-emerald-600"/> Auditable actions · least privilege</div>
        </aside>
      </div>
    </main>
  </div>;
}
