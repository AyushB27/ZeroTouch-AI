import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity, ArrowUp, BarChart3, Bot, BriefcaseBusiness, Check, CheckCircle2,
  ChevronRight, CircleHelp, Clock3, Command, CreditCard, Headphones, Layers3,
  LogOut, Megaphone, MessageSquareText, MoreHorizontal, Plus, Search, ShieldCheck,
  Sparkles, Users, WalletCards, Wrench, X, Zap, LoaderCircle
} from 'lucide-react';
import {
  approveWorkforceTask, getWorkforceTasks, rejectWorkforceTask,
  runWorkforceAgent, executeWorkforceCommand
} from '../api';

const BOTS = [
  { id: 'home', label: 'Home', icon: Sparkles, bot: 'Your AI workspace' },
  { id: 'finance', label: 'Finance', icon: CreditCard, bot: 'Finance assistant' },
  { id: 'hr', label: 'HR', icon: Users, bot: 'People assistant' },
  { id: 'it', label: 'IT', icon: Wrench, bot: 'IT service desk' },
  { id: 'support', label: 'Support', icon: Headphones, bot: 'Customer support' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, soon: true },
  { id: 'marketing', label: 'Marketing', icon: Megaphone, soon: true },
  { id: 'sales', label: 'Sales', icon: BriefcaseBusiness, soon: true },
  { id: 'operations', label: 'Operations', icon: Layers3, soon: true },
];
const QUICK = [
  { label: 'Resolve a ticket', prompt: 'Review and resolve the highest priority support ticket', icon: Headphones, domain: 'support' },
  { label: 'Find a transaction', prompt: 'Find the latest transaction that needs attention', icon: Search, domain: 'finance' },
  { label: 'Create a report', prompt: 'Create a concise report of the latest operations activity', icon: BarChart3, domain: 'all' },
  { label: 'Onboard an employee', prompt: 'Prepare the next employee onboarding tasks', icon: Users, domain: 'hr' },
];
const done = task => ['APPROVED', 'AUTO_EXECUTED', 'COMPLETED'].includes(task?.status);
const statusClass = task => done(task) ? 'good' : task?.status === 'REJECTED' ? 'bad' : 'wait';
const time = value => { const d = new Date(value); return value && !Number.isNaN(d.getTime()) ? d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : 'Recently'; };

export default function EmployeeAgentWorkspace({ user, currentRole, onLogout }) {
  const [tasks, setTasks] = useState([]);
  const [botId, setBotId] = useState('home');
  const [selectedId, setSelectedId] = useState(null);
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [action, setAction] = useState('');
  const [notice, setNotice] = useState('');
  const refresh = async () => { try { const data = await getWorkforceTasks(); setTasks(data?.tasks || []); } catch { /* API may reconnect. */ } };
  useEffect(() => { refresh(); const timer = setInterval(refresh, 8000); return () => clearInterval(timer); }, []);
  const bot = BOTS.find(item => item.id === botId) || BOTS[0];
  const visibleTasks = useMemo(() => botId === 'home' ? tasks : tasks.filter(task => task.domain === botId), [tasks, botId]);
  const task = visibleTasks.find(item => item.case_id === selectedId) || visibleTasks[0] || null;
  const name = user?.name || currentRole?.name || 'there';

  async function ask(value = prompt, domain = botId) {
    const text = value.trim(); if (!text || busy) return;
    setPrompt(''); setMessages(items => [...items, { role: 'user', text }]); setBusy(true); setNotice('');
    try {
      const result = await executeWorkforceCommand(text, currentRole?.role_id || 'support_agent');
      setMessages(items => [...items, { role: 'assistant', text: result?.summary || result?.message || 'Your request is ready for review.', result }]);
      await refresh();
    } catch (error) { setMessages(items => [...items, { role: 'assistant', text: error.message || 'I could not complete that request. Please try again.' }]); }
    finally { setBusy(false); }
    if (domain !== 'all' && BOTS.some(item => item.id === domain)) setBotId(domain);
  }
  async function act(kind) {
    if (!task || action) return;
    let reason;
    if (kind === 'reject') { reason = window.prompt('Why does this task need a human specialist?'); if (!reason?.trim()) return; }
    setAction(kind); setNotice('');
    try {
      if (kind === 'bot') { const result = await runWorkforceAgent(task.case_id); setNotice(result?.agent_result?.fallback ? 'Bot is offline; a safe fallback recommendation is available.' : `${result?.agent_result?.provider || 'Workflow bot'} finished reviewing this task.`); }
      if (kind === 'approve') { await approveWorkforceTask(task.case_id, name); setNotice('Task approved and sent through its execution workflow.'); }
      if (kind === 'reject') { await rejectWorkforceTask(task.case_id, name, reason.trim()); setNotice('Task routed to a specialist for manual review.'); }
      await refresh();
    } catch (error) { setNotice(error.message || 'The action could not be completed.'); }
    finally { setAction(''); }
  }

  return <div className="zt-workspace">
    <header className="zt-topbar">
      <a className="zt-brand" href="#workspace"><span className="zt-brand-mark"><Zap size={17} fill="currentColor" /></span><span className="zt-brand-name">zero<span>touch</span></span><span className="zt-brand-pill">WORKSPACE</span></a>
      <div className="zt-system-state"><i /> All systems operational</div>
      <div className="zt-top-user"><button className="zt-icon-btn" aria-label="Help"><CircleHelp size={17} /></button><i className="zt-divider" /><span className="zt-avatar">{name.split(/\s+/).map(part => part[0]).slice(0, 2).join('').toUpperCase()}</span><span className="zt-user-copy"><b>{name}</b><small>Employee workspace</small></span><button className="zt-icon-btn" onClick={onLogout} aria-label="Sign out" title="Sign out"><LogOut size={16} /></button></div>
    </header>
    <div className="zt-grid">
      <aside className="zt-sidebar"><div className="zt-side-heading">YOUR WORKSPACE <MoreHorizontal size={16} /></div><div className="zt-nav-label">ALL BOTS</div><nav>{BOTS.map(({ id, label, icon: Icon, soon }) => <button key={id} disabled={soon} onClick={() => { setBotId(id); setNotice(''); }} className={`zt-nav-item ${botId === id ? 'active' : ''} ${soon ? 'soon' : ''}`}><Icon size={17} /><span>{label}</span>{soon ? <small>SOON</small> : id !== 'home' && <ChevronRight size={14} className="zt-chevron" />}</button>)}</nav><div className="zt-side-spacer" /><div className="zt-safe-card"><ShieldCheck size={16} /><div><b>Your data stays protected</b><span>Bot actions follow your team’s access rules.</span></div></div><div className="zt-side-footer"><b>Z</b> ZeroTouch AI <span>v1.0</span></div></aside>
      <main className="zt-main"><div className="zt-scroll">
        <section className="zt-welcome"><div><div className="zt-eyebrow">✦ &nbsp; YOUR AI WORKSPACE</div><h1>{botId === 'home' ? <>Good morning, {name.split(' ')[0]} <span>✳</span></> : `${bot.label} workspace`}</h1><p>{botId === 'home' ? 'What can I help you get done today?' : `${bot.bot} is ready to help you move work forward.`}</p></div><button className="zt-new-task" onClick={() => document.getElementById('zt-prompt')?.focus()}><Plus size={15} /> New task</button></section>
        <section className="zt-composer"><div className="zt-composer-title"><span><Sparkles size={17} /></span><div><b>Ask your AI teammate</b><small>Describe the outcome you need. Your assistant will plan the next steps.</small></div><MoreHorizontal size={17} className="zt-more" /></div><form onSubmit={event => { event.preventDefault(); ask(); }}><textarea id="zt-prompt" rows={2} value={prompt} onChange={event => setPrompt(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); ask(); } }} placeholder="Tell ZeroTouch what you want done…" /><div className="zt-prompt-bottom"><span><Command size={12} /> Enter to send · Shift + Enter for a new line</span><button disabled={!prompt.trim() || busy} aria-label="Send request">{busy ? <LoaderCircle size={16} className="zt-spin" /> : <ArrowUp size={17} />}</button></div></form><div className="zt-human-note"><ShieldCheck size={13} /> Human approval stays in control for sensitive actions</div></section>
        {messages.length > 0 && <section className="zt-conversation"><div className="zt-section-heading"><div><MessageSquareText size={15} /><h2>Conversation</h2></div><button onClick={() => setMessages([])}><X size={13} /> Clear</button></div>{messages.slice(-4).map((message, index) => <div className={`zt-message ${message.role}`} key={`${index}-${message.text}`}><span>{message.role === 'assistant' ? <Sparkles size={14} /> : name[0]}</span><div><b>{message.role === 'assistant' ? bot.bot : 'You'}</b><p>{message.text}</p>{message.result?.plan_steps?.length > 0 && <div className="zt-plan">{message.result.plan_steps.slice(0, 4).map(step => <div key={step.step_id}><CheckCircle2 size={13} />{step.action || step.detail}</div>)}</div>}</div></div>)}{busy && <div className="zt-working"><span>•••</span> Your teammate is working through the request…</div>}</section>}
        <section className="zt-quick"><div className="zt-section-heading"><div><Sparkles size={15} /><h2>Quick actions</h2></div><small>A good place to start</small></div><div className="zt-quick-grid">{QUICK.map(({ label, prompt: text, icon: Icon, domain }) => <button key={label} onClick={() => ask(text, domain)} disabled={busy}><span><Icon size={16} /></span><b>{label}</b><ArrowUp size={13} /></button>)}</div></section>
        <section className="zt-tasks"><div className="zt-section-heading"><div><Activity size={15} /><h2>{botId === 'home' ? 'Your tasks' : `${bot.label} tasks`}</h2><small>{visibleTasks.length}</small></div><button onClick={refresh}>Refresh <Activity size={12} /></button></div>{visibleTasks.length ? <div className="zt-task-list">{visibleTasks.slice(0, 6).map(item => <button key={item.case_id} onClick={() => setSelectedId(item.case_id)} className={`zt-task-row ${task?.case_id === item.case_id ? 'selected' : ''}`}><span className={`zt-task-icon ${item.domain || 'support'}`}>{item.domain === 'finance' ? <WalletCards size={16} /> : item.domain === 'hr' ? <Users size={16} /> : item.domain === 'it' ? <Wrench size={16} /> : <Headphones size={16} />}</span><span className="zt-task-copy"><b>{item.title || 'Work item'}</b><small>{item.case_id} · {item.domain || 'support'} · {time(item.created_at)}</small></span><span className={`zt-status ${statusClass(item)}`}>{(item.status || 'PREPARED').replace(/_/g, ' ')}</span><ChevronRight size={15} className="zt-task-chevron" /></button>)}</div> : <div className="zt-empty"><Check size={17} /><div><b>You’re all caught up</b><span>New work will show up here when it’s ready.</span></div></div>}</section>
      </div><footer className="zt-main-footer"><span>© 2026 ZeroTouch</span><span><i /> AI teammate is online</span><span>Privacy · Help</span></footer></main>
      <aside className="zt-context"><div className="zt-context-heading"><div><small>WORKSPACE</small><h2>Task context</h2></div><MoreHorizontal size={17} /></div>{notice && <div className="zt-notice"><CheckCircle2 size={14} />{notice}<button onClick={() => setNotice('')}><X size={12} /></button></div>}{task ? <>
        <section className="zt-current"><div className="zt-current-top"><small>CURRENT TASK</small><span className={`zt-status ${statusClass(task)}`}>{(task.status || 'PREPARED').replace(/_/g, ' ')}</span></div><h3>{task.title || 'Work item'}</h3><p>{task.case_id} · {task.domain || 'support'} workflow</p><div className="zt-progress-title"><span>Progress</span><b>{done(task) ? 'Complete' : task.status === 'PENDING_REVIEW' ? 'Needs your review' : 'Ready for review'}</b></div><div className="zt-progress"><i style={{ width: done(task) ? '100%' : '66%' }} /></div><div className="zt-stages"><span>✓ Gathered</span><span>✓ Prepared</span><span>{done(task) ? '✓' : '○'} Approved</span></div></section>
        {task.bot_assignment && <section className="zt-assigned"><span><Bot size={16} /></span><div><small>ASSIGNED BOT</small><b>{task.bot_assignment.name}</b></div><i>● Live</i><p>{(task.bot_assignment.tools || []).slice(0, 3).map(tool => tool.replace(/_/g, ' ')).join(' · ')}</p></section>}
        <section className="zt-actions"><small>ACTIONS</small><button className="zt-run" disabled={Boolean(action)} onClick={() => act('bot')}>{action === 'bot' ? <LoaderCircle size={15} className="zt-spin" /> : <Sparkles size={15} />} Run workflow bot <ArrowUp size={13} /></button>{!done(task) && task.status !== 'REJECTED' && <><button className="zt-approve" disabled={Boolean(action)} onClick={() => act('approve')}>{action === 'approve' ? <LoaderCircle size={15} className="zt-spin" /> : <Check size={15} />} Approve task</button><button className="zt-reject" disabled={Boolean(action)} onClick={() => act('reject')}>Send to human review</button></>}</section>
        <section className="zt-activity"><div className="zt-activity-head"><small>RECENT ACTIVITY</small><MoreHorizontal size={15} /></div>{(task.audit_log || []).slice(-4).reverse().map((entry, index) => <div className="zt-activity-row" key={`${entry.timestamp}-${index}`}><i className={index === 0 ? 'latest' : ''} /><div><b>{(entry.action || 'Updated').replace(/_/g, ' ').toLowerCase()}</b><span>{entry.actor || 'ZeroTouch'} · {time(entry.timestamp)}</span></div></div>)}{!task.audit_log?.length && <div className="zt-no-activity"><Clock3 size={14} /> Task activity will appear here</div>}</section>
      </> : <div className="zt-no-task"><span><Sparkles size={19} /></span><b>No task selected</b><p>Choose a task to see its progress, bot, and available actions.</p></div>}<div className="zt-context-note"><ShieldCheck size={14} /><span><b>Human in control</b>Sensitive actions wait for your approval.</span></div></aside>
    </div>
  </div>;
}
