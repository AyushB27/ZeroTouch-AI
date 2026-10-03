import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity, ArrowUp, BarChart3, BookOpen, Bot, BriefcaseBusiness, Check, CheckCircle2,
  ChevronRight, CircleHelp, Clock3, Command, CreditCard, ExternalLink, GraduationCap, Headphones,
  Layers3, LogOut, Megaphone, MessageSquareText, MoreHorizontal, Plus, Search, ShieldCheck,
  Sparkles, Users, WalletCards, Wrench, X, Zap, LoaderCircle, ShieldAlert, FileText, Scale
} from 'lucide-react';
import {
  approveWorkforceTask, getWorkforceTasks, rejectWorkforceTask,
  runWorkforceAgent, executeWorkforceCommand, sendWorkforceChat, getWorkforceBots
} from '../api';

const BOTS = [
  { id: 'home', label: 'Home', icon: Sparkles, bot: 'Your AI workspace', tagline: 'Unified enterprise autonomous operations' },
  { id: 'support', label: 'Support', icon: Headphones, bot: 'Support & Payments Bot', tagline: 'Real-time payment resolution, RBI SLA compliance & wallet credits' },
  { id: 'finance', label: 'Finance', icon: CreditCard, bot: 'Finance Reconciliation Bot', tagline: '3-way statement matching, fee variance & duplicate payout prevention' },
  { id: 'it', label: 'IT', icon: Wrench, bot: 'IT Access & Service Desk Bot', tagline: 'Zero-touch software licensing, deprovisioning & root guardrails' },
  { id: 'hr', label: 'HR', icon: Users, bot: 'Talent & HR Operations Bot', tagline: 'Bias-free rubric scoring, automated panel scheduling & onboarding' },
  { id: 'academy', label: 'Academy', icon: GraduationCap, bot: 'New Joiner Academy Coach', tagline: 'Safe historical dispute replay sandbox & L1 skill synthesis' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, soon: true },
  { id: 'marketing', label: 'Marketing', icon: Megaphone, soon: true },
  { id: 'sales', label: 'Sales', icon: BriefcaseBusiness, soon: true },
  { id: 'operations', label: 'Operations', icon: Layers3, soon: true },
];

const DOMAIN_PAIN_POINTS = {
  support: [
    {
      id: 'stuck_upi',
      title: 'Stuck UPI Debited Without Credit',
      desc: 'Customer bank debited but NPCI/merchant switch indicates uncredited or pending.',
      prompt: 'Reconcile stuck UPI payment and execute instant reversal if verified',
      edgeCases: ['Subprime CIBIL (<650) held', 'SHA-256 Idempotency lock'],
      guardrail: 'RULE_PAYMENT_REVERSAL_01 (Prime CIBIL ≥ 750)',
    },
    {
      id: 'rbi_sla_chase',
      title: 'RBI T+1 SLA Breach with Compensation',
      desc: 'Track refunds past T+1 mandate, calculate ₹100/day statutory penalty, dispatch bank chase.',
      prompt: 'Chase all refunds past SLA and calculate RBI penalty compensation',
      edgeCases: ['₹100/day statutory penalty', 'Nodal verified before chase'],
      guardrail: 'RBI Harmonisation Mandate §3',
    },
    {
      id: 'bounced_wallet',
      title: 'Bounced Bank Refund due to Frozen Account',
      desc: 'Detect bank return codes (ACCOUNT_FROZEN) and credit customer digital wallet.',
      prompt: 'Remediate bounced bank refund by crediting customer digital wallet',
      edgeCases: ['Wallet credit fallback', 'KYC limit verified'],
      guardrail: 'RULE_WALLET_FALLBACK_CREDIT',
    },
  ],
  finance: [
    {
      id: 'nodal_variance',
      title: '3-Way Nodal Statement Reconciliation Variance',
      desc: 'Decompose bank payout variance into base MDR (₹847.46) + 18% GST (₹152.54).',
      prompt: 'Reconcile nodal bank statement variance against MDR fee and GST schedule',
      edgeCases: ['MDR + GST exact match', '>₹5,000 routes to Controller'],
      guardrail: 'SOX Section 404 Escrow Recon',
    },
    {
      id: 'duplicate_payout',
      title: 'Duplicate Payout Detection & Prevention',
      desc: 'Flag identical payout lines, halt automated clearing, draft AP clawback hold.',
      prompt: 'Audit bank statement for duplicate payout lines and draft clawback hold',
      edgeCases: ['Immediate halt on DUPLICATE_FLAG', 'Offset future payables'],
      guardrail: 'RULE_DUPLICATE_PAYOUT_HALT',
    },
    {
      id: 'kyc_hold',
      title: 'Expired KYC Merchant Settlement Hold',
      desc: 'Hold escrow settlement if merchant GSTIN or Director PAN expired.',
      prompt: 'Verify compliance holds and check expired merchant KYC settlement eligibility',
      edgeCases: ['RBI Payout §4.2 enforced', 'Dual sign-off required'],
      guardrail: 'RBI Master Direction §4.2 KYC Gate',
    },
  ],
  it: [
    {
      id: 'standard_licensing',
      title: 'Repetitive Standard Software Licensing (Okta)',
      desc: 'Verify role in Okta and auto-grant pre-approved Figma Pro or GitHub Enterprise.',
      prompt: 'Verify employee role entitlement in Okta and auto-grant standard tool license',
      edgeCases: ['Pre-approved RBAC bundle', 'Non-standard tools to manager'],
      guardrail: 'RULE_STANDARD_ROLE_ENTITLEMENT',
    },
    {
      id: 'privileged_access',
      title: 'High-Risk Privileged Access Attempt (AWS Root)',
      desc: 'Intercept root / prod DB requests and unconditionally enforce CISO dual approval.',
      prompt: 'Audit access request for high-risk privileged credentials and enforce guardrails',
      edgeCases: ['Zero-Touch root blocked', 'Dual CISO signature required'],
      guardrail: 'NEVER_AUTOMATE_PRIVILEGED_ACCESS',
    },
    {
      id: 'role_deprovisioning',
      title: 'Zero-Touch Deprovisioning on Role Change',
      desc: 'Deprovision obsolete SaaS seats upon team transfer to eliminate license waste.',
      prompt: 'Audit employee role transition and deprovision obsolete software licenses',
      edgeCases: ['Revoke obsolete seats', 'Asset ownership protected'],
      guardrail: 'Principle of Least Privilege',
    },
  ],
  hr: [
    {
      id: 'unconscious_bias',
      title: 'Unconscious Bias & PII in Candidate Screening',
      desc: 'Strip gender, age, photo, and college pedigree; score technical criteria only.',
      prompt: 'Run bias-free candidate evaluation with protected attributes stripped',
      edgeCases: ['PII & demographics stripped', 'AI cannot auto-reject'],
      guardrail: 'RULE_FAIRNESS_ANONYMIZATION',
    },
    {
      id: 'panel_scheduling',
      title: 'Interview Panel Scheduling Overhead',
      desc: 'Dispatch calendar invites for candidates scoring ≥80% on rubric.',
      prompt: 'Schedule 4-person technical interview panel for qualified candidate',
      edgeCases: ['Threshold ≥80% required', 'Backup interviewer pool'],
      guardrail: 'Recruiter Consent Gate',
    },
    {
      id: 'onboarding_roadmap',
      title: 'Automated New-Hire Onboarding Roadmap',
      desc: 'Generate 30-60-90 day ramp roadmap and track IT laptop hardware delivery.',
      prompt: 'Generate 30-60-90 day onboarding roadmap and coordinate IT/HR setup',
      edgeCases: ['Laptop courier tracked', 'Timezone adaptive sync'],
      guardrail: 'Day 1 Readiness Baseline SLA',
    },
  ],
  academy: [
    {
      id: 'dispute_ramp',
      title: 'Slow Operator Ramp-Up on Complex Disputes',
      desc: 'Load historical UPI dispute replay case in zero-risk production sandbox.',
      prompt: 'Load anonymized historical dispute replay case and grade joiner decisions',
      edgeCases: ['100% production isolated', 'Zero live customer funds'],
      guardrail: 'Zero-Risk Production Isolation',
    },
    {
      id: 'inconsistent_decisions',
      title: 'Inconsistent Decision-Making Across Junior Operators',
      desc: 'Grade trainee multi-ledger reasoning against canonical banking policy.',
      prompt: 'Run interactive simulation on conflicting ledger dispute and test invariants',
      edgeCases: ['Boundary condition testing', 'Threshold ≥85% for L1'],
      guardrail: 'Policy Adherence Scoring',
    },
    {
      id: 'skill_synthesis',
      title: 'Standardizing Expert Workflows into L1 Skills',
      desc: 'Synthesize SkillSpec from recorded actions and run 12-case backtest.',
      prompt: 'Synthesize versioned skill spec from recorded actions and run 12-case backtest',
      edgeCases: ['12-case historical backtest', 'L1 supervised promotion'],
      guardrail: 'Governor Invariant Gate',
    },
  ],
};

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
  const [showDocModal, setShowDocModal] = useState(false);

  const refresh = async () => {
    try {
      const data = await getWorkforceTasks();
      setTasks(data?.tasks || []);
    } catch { /* reconnect */ }
  };

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 8000);
    return () => clearInterval(timer);
  }, []);

  const bot = BOTS.find(item => item.id === botId) || BOTS[0];
  const activeDomain = botId === 'home' ? 'support' : botId;
  const currentPainPoints = DOMAIN_PAIN_POINTS[botId] || (botId === 'home' ? [
    DOMAIN_PAIN_POINTS.support[0],
    DOMAIN_PAIN_POINTS.finance[0],
    DOMAIN_PAIN_POINTS.it[0],
    DOMAIN_PAIN_POINTS.hr[0],
  ] : []);

  const visibleTasks = useMemo(() => botId === 'home' ? tasks : tasks.filter(task => task.domain === botId), [tasks, botId]);
  const task = visibleTasks.find(item => item.case_id === selectedId) || visibleTasks[0] || null;
  const name = user?.name || currentRole?.name || 'Aarav Sharma';

  async function ask(value = prompt, targetDomain = botId) {
    const text = value.trim();
    if (!text || busy) return;
    setPrompt('');
    setMessages(items => [...items, { role: 'user', text }]);
    setBusy(true);
    setNotice('');

    // Shortcut for resolving open ticket
    if (/\b(resolve|close|handle)\b/i.test(text) && /\b(ticket|support case|support task)\b/i.test(text)) {
      const rank = { URGENT: 0, HIGH: 1, NORMAL: 2, LOW: 3 };
      const openSupportTasks = tasks.filter(item => item.domain === 'support' && !done(item) && item.status !== 'REJECTED')
        .sort((a, b) => (rank[a.priority] ?? 4) - (rank[b.priority] ?? 4));
      const nextTask = openSupportTasks[0];
      setBotId('support');
      if (nextTask) setSelectedId(nextTask.case_id);
      setMessages(items => [...items, {
        role: 'assistant',
        text: nextTask
          ? `I found highest-priority open support task: ${nextTask.title}. Review its evidence in Task Context, then approve it to execute the workflow.`
          : 'There are no open support tasks to resolve right now.',
        provider: 'ZeroTouch Domain Intelligence'
      }]);
      setBusy(false);
      return;
    }

    try {
      const effDomain = targetDomain === 'home' ? 'support' : targetDomain;
      const result = await sendWorkforceChat(text, effDomain, `${effDomain}_bot`);
      setMessages(items => [...items, {
        role: 'assistant',
        text: result?.message || result?.summary || 'Analysis complete.',
        provider: result?.provider || 'xAI Grok / Domain Intelligence',
        fallbackLabel: result?.fallback_label,
        planSteps: result?.plan_steps || [],
        edgeCases: result?.edge_cases || [],
        guardrails: result?.guardrails || [],
        caseId: result?.case_id,
        ragContext: result?.rag_context,
      }]);
      await refresh();
    } catch {
      // Fallback to command bar planner
      try {
        const cmdRes = await executeWorkforceCommand(text, currentRole?.role_id || 'support_agent');
        setMessages(items => [...items, {
          role: 'assistant',
          text: cmdRes?.summary || cmdRes?.message || 'Request executed.',
          provider: 'Command Bar Planner',
          planSteps: cmdRes?.plan_steps || [],
        }]);
        await refresh();
      } catch (err) {
        setMessages(items => [...items, {
          role: 'assistant',
          text: err.message || 'I could not complete that request. Please try again.',
          provider: 'ZeroTouch Assistant'
        }]);
      }
    } finally {
      setBusy(false);
      if (targetDomain !== 'all' && targetDomain !== 'home' && BOTS.some(item => item.id === targetDomain)) {
        setBotId(targetDomain);
      }
    }
  }

  async function act(kind) {
    if (!task || action) return;
    let reason;
    if (kind === 'reject') {
      reason = window.prompt('Why does this task need a human specialist?');
      if (!reason?.trim()) return;
    }
    setAction(kind);
    setNotice('');
    try {
      if (kind === 'bot') {
        const result = await runWorkforceAgent(task.case_id);
        const pName = result?.agent_result?.provider || 'Workflow bot';
        setNotice(result?.agent_result?.fallback
          ? `${pName} reviewed task with local intelligence. Timeline updated.`
          : `${pName} finished reviewing this task. Timeline updated.`);
        // Immediately update local task state with the returned case data (includes new audit_log entry)
        if (result?.case) {
          setTasks(prev => prev.map(t => t.case_id === result.case.case_id ? { ...t, ...result.case } : t));
          setSelectedId(result.case.case_id);
        }
      }
      if (kind === 'approve') {
        await approveWorkforceTask(task.case_id, name);
        setNotice('Task approved and sent through its execution workflow.');
      }
      if (kind === 'reject') {
        await rejectWorkforceTask(task.case_id, name, reason.trim());
        setNotice('Task routed to a specialist for manual review.');
      }
      await refresh();
    } catch (error) {
      setNotice(error.status === 500
        ? 'The task action failed in the backend (HTTP 500). Check backend terminal.'
        : error.message || 'The action could not be completed.');
    } finally {
      setAction('');
    }
  }

  return (
    <div className="zt-workspace">
      {/* Top Navigation Bar */}
      <header className="zt-topbar">
        <a className="zt-brand" href="#workspace">
          <span className="zt-brand-mark"><Zap size={17} fill="currentColor" /></span>
          <span className="zt-brand-name">zero<span>touch</span></span>
          <span className="zt-brand-pill">AI WORKFORCE</span>
        </a>
        <div className="zt-system-state">
          <i /> xAI Grok & Domain Bots Active
        </div>
        <div className="zt-top-user">
          <button
            className="zt-icon-btn"
            style={{ width: 'auto', padding: '0 12px', gap: '6px', fontSize: '11px', fontWeight: 600, display: 'inline-flex' }}
            onClick={() => setShowDocModal(true)}
            title="View Domain Bots & Edge Cases Documentation"
          >
            <BookOpen size={15} /> Domain Guide & Edge Cases
          </button>
          <i className="zt-divider" />
          <span className="zt-avatar">{name.split(/\s+/).map(p => p[0]).slice(0, 2).join('').toUpperCase()}</span>
          <span className="zt-user-copy">
            <b>{name}</b>
            <small>Enterprise Operator</small>
          </span>
          <button className="zt-icon-btn" onClick={onLogout} aria-label="Sign out" title="Sign out">
            <LogOut size={16} />
          </button>
        </div>
      </header>

      {/* Main Grid Layout */}
      <div className="zt-grid">
        {/* Left Sidebar */}
        <aside className="zt-sidebar">
          <div className="zt-side-heading">
            DOMAIN BOTS <MoreHorizontal size={16} />
          </div>
          <div className="zt-nav-label">SPECIALIZED WORKFORCE</div>
          <nav>
            {BOTS.map(({ id, label, icon: Icon, soon }) => (
              <button
                key={id}
                disabled={soon}
                onClick={() => { setBotId(id); setNotice(''); }}
                className={`zt-nav-item ${botId === id ? 'active' : ''} ${soon ? 'soon' : ''}`}
              >
                <Icon size={17} />
                <span>{label}</span>
                {soon ? <small>SOON</small> : id !== 'home' && <ChevronRight size={14} className="zt-chevron" />}
              </button>
            ))}
          </nav>
          <div className="zt-side-spacer" />
          <div className="zt-safe-card" onClick={() => setShowDocModal(true)} style={{ cursor: 'pointer' }}>
            <ShieldCheck size={16} />
            <div>
              <b>Pain Points & Guardrails</b>
              <span>Click to view edge cases and RBI/SOX rules.</span>
            </div>
          </div>
          <div className="zt-side-footer">
            <b>Z</b> ZeroTouch AI <span>v1.0 · Grok Integrated</span>
          </div>
        </aside>

        {/* Center Main Stage */}
        <main className="zt-main">
          <div className="zt-scroll">
            {/* Header / Persona */}
            <section className="zt-welcome">
              <div>
                <div className="zt-eyebrow">✦ &nbsp; {botId === 'home' ? 'MULTI-DOMAIN AI WORKFORCE' : `${bot.label.toUpperCase()} DOMAIN BOT`}</div>
                <h1>{botId === 'home' ? <>Good day, {name.split(' ')[0]} <span>✳</span></> : `${bot.bot}`}</h1>
                <p>{bot.tagline || `${bot.bot} is standing by to resolve domain pain points with full compliance.`}</p>
              </div>
              <button className="zt-new-task" onClick={() => document.getElementById('zt-prompt')?.focus()}>
                <Plus size={15} /> New request
              </button>
            </section>

            {/* Natural Language Composer */}
            <section className="zt-composer">
              <div className="zt-composer-title">
                <span><Sparkles size={17} /></span>
                <div>
                  <b>Ask {bot.bot}</b>
                  <small>Powered by xAI Grok with local read-only tool execution & compliance guardrails.</small>
                </div>
                <MoreHorizontal size={17} className="zt-more" />
              </div>
              <form onSubmit={e => { e.preventDefault(); ask(); }}>
                <textarea
                  id="zt-prompt"
                  rows={2}
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(); } }}
                  placeholder={`Describe a ${botId === 'home' ? 'task or issue' : `${bot.label} issue (e.g. pain points below)`}…`}
                />
                <div className="zt-prompt-bottom">
                  <span><Command size={12} /> Enter to send · Shift + Enter for new line</span>
                  <button disabled={!prompt.trim() || busy} aria-label="Send request">
                    {busy ? <LoaderCircle size={16} className="zt-spin" /> : <ArrowUp size={17} />}
                  </button>
                </div>
              </form>
              <div className="zt-human-note">
                <ShieldCheck size={13} /> Least-privilege tools: sensitive mutations strictly require human sign-off
              </div>
            </section>

            {/* 2-3 Key Pain Points Tackled by this Bot */}
            {currentPainPoints.length > 0 && (
              <section className="zt-pain-section">
                <div className="zt-pain-heading">
                  <div>
                    <Sparkles size={16} />
                    <h2>{botId === 'home' ? 'Key Pain Points Handled Across Domains' : `${bot.label} Pain Points Handled by AI Bot`}</h2>
                  </div>
                  <small>{currentPainPoints.length} Key Scenarios Tackled</small>
                </div>
                <div className="zt-pain-grid">
                  {currentPainPoints.map(point => (
                    <div key={point.id} className="zt-pain-card">
                      <div>
                        <div className="zt-pain-card-header">
                          <b>{point.title}</b>
                        </div>
                        <p className="zt-pain-card-desc">{point.desc}</p>
                      </div>
                      <div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '8px' }}>
                          {(point.edgeCases || []).map((edge, i) => (
                            <span key={i} className="zt-edge-tag">
                              <ShieldAlert size={10} /> {edge}
                            </span>
                          ))}
                          {point.guardrail && (
                            <span className="zt-guard-tag">
                              <Scale size={10} /> {point.guardrail}
                            </span>
                          )}
                        </div>
                        <div className="zt-pain-card-footer">
                          <button
                            className="zt-pain-btn"
                            disabled={busy}
                            onClick={() => ask(point.prompt, botId === 'home' ? (point.id.includes('upi') || point.id.includes('sla') ? 'support' : point.id.includes('nodal') ? 'finance' : point.id.includes('licens') ? 'it' : 'hr') : botId)}
                          >
                            <Zap size={12} fill="currentColor" /> Solve with AI Bot
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Conversation Stream */}
            {messages.length > 0 && (
              <section className="zt-conversation">
                <div className="zt-section-heading">
                  <div>
                    <MessageSquareText size={15} />
                    <h2>Teammate Conversation</h2>
                  </div>
                  <button onClick={() => setMessages([])}><X size={13} /> Clear</button>
                </div>
                {messages.slice(-6).map((message, index) => (
                  <div className={`zt-message ${message.role}`} key={`${index}-${message.text.slice(0, 20)}`}>
                    <span>{message.role === 'assistant' ? <Sparkles size={14} /> : name[0]}</span>
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                        <b>{message.role === 'assistant' ? bot.bot : 'You'}</b>
                        {message.provider && (
                          <span className={`zt-provider-badge ${message.provider.includes('Grok') ? 'grok' : 'fallback'}`} title={message.fallbackLabel || message.provider}>
                            {message.provider}
                          </span>
                        )}
                      </div>
                      <div style={{ whiteSpace: 'pre-line', fontSize: '13px', lineHeight: '1.5' }}>
                        {message.text}
                      </div>

                      {/* Edge cases tags */}
                      {message.edgeCases?.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' }}>
                          {message.edgeCases.map((ec, i) => (
                            <span key={i} className="zt-edge-tag"><ShieldAlert size={11} /> Edge Case: {ec}</span>
                          ))}
                        </div>
                      )}

                      {/* Guardrails verified */}
                      {message.guardrails?.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                          {message.guardrails.map((gr, i) => (
                            <span key={i} className="zt-guard-tag"><Scale size={11} /> Invariant: {gr}</span>
                          ))}
                        </div>
                      )}

                      {/* Plan Steps */}
                      {message.planSteps?.length > 0 && (
                        <div className="zt-plan" style={{ marginTop: '12px' }}>
                          <small style={{ fontWeight: 600, color: '#475569', display: 'block', marginBottom: '6px' }}>ORCHESTRATED PLAN TRACE:</small>
                          {message.planSteps.map(step => (
                            <div key={step.step_id || Math.random()}>
                              <CheckCircle2 size={13} style={{ color: '#16a34a', flexShrink: 0 }} />
                              <span><b>{step.agent || 'Agent'}:</b> {step.action} — <small style={{ color: '#64748b' }}>{step.detail}</small></span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* RAG Knowledge Base Retrieval Grounding */}
                      {message.ragContext && (
                        <div style={{ marginTop: '10px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '8px 10px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', fontWeight: 700, color: '#0369a1', marginBottom: '4px' }}>
                            <BookOpen size={12} /> RAG Policy Knowledge Base Grounding:
                          </div>
                          <div style={{ fontSize: '11px', color: '#475569', whiteSpace: 'pre-line', maxHeight: '110px', overflowY: 'auto', lineHeight: '1.4' }}>
                            {message.ragContext}
                          </div>
                        </div>
                      )}

                      {/* Associated Case Selector */}
                      {message.caseId && (
                        <div style={{ marginTop: '10px' }}>
                          <button
                            onClick={() => setSelectedId(message.caseId)}
                            style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '5px 10px', fontSize: '11px', fontWeight: 600, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                          >
                            <ExternalLink size={12} /> Inspect Case {message.caseId} in Task Context
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {busy && (
                  <div className="zt-working">
                    <span>•••</span> {bot.bot} is inspecting evidence and running permissioned tools…
                  </div>
                )}
              </section>
            )}

            {/* Task Inbox Queue */}
            <section className="zt-tasks">
              <div className="zt-section-heading">
                <div>
                  <Activity size={15} />
                  <h2>{botId === 'home' ? 'All Pre-Worked Tasks' : `${bot.label} Tasks`}</h2>
                  <small>{visibleTasks.length}</small>
                </div>
                <button onClick={refresh}>Refresh <Activity size={12} /></button>
              </div>
              {visibleTasks.length ? (
                <div className="zt-task-list">
                  {visibleTasks.slice(0, 8).map(item => (
                    <button
                      key={item.case_id}
                      onClick={() => setSelectedId(item.case_id)}
                      className={`zt-task-row ${task?.case_id === item.case_id ? 'selected' : ''}`}
                    >
                      <span className={`zt-task-icon ${item.domain || 'support'}`}>
                        {item.domain === 'finance' ? <WalletCards size={16} /> : item.domain === 'hr' ? <Users size={16} /> : item.domain === 'it' ? <Wrench size={16} /> : item.domain === 'academy' ? <GraduationCap size={16} /> : <Headphones size={16} />}
                      </span>
                      <span className="zt-task-copy">
                        <b>{item.title || 'Work item'}</b>
                        <small>{item.case_id} · {item.domain || 'support'} · {time(item.created_at)}</small>
                      </span>
                      <span className={`zt-status ${statusClass(item)}`}>
                        {(item.status || 'PREPARED').replace(/_/g, ' ')}
                      </span>
                      <ChevronRight size={15} className="zt-task-chevron" />
                    </button>
                  ))}
                </div>
              ) : (
                <div className="zt-empty">
                  <Check size={17} />
                  <div>
                    <b>You’re all caught up</b>
                    <span>New work will appear here when an incoming event triggers a workflow.</span>
                  </div>
                </div>
              )}
            </section>
          </div>

          {/* Footer */}
          <footer className="zt-main-footer">
            <span>© 2026 ZeroTouch AI</span>
            <span><i /> Connected to xAI Grok & least-privilege connectors</span>
            <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setShowDocModal(true)}>
              Domain Documentation & Edge Cases
            </span>
          </footer>
        </main>

        {/* Right Task Context Sidebar */}
        <aside className="zt-context">
          <div className="zt-context-heading">
            <div>
              <small>WORKSPACE</small>
              <h2>Task context</h2>
            </div>
            <button
              onClick={() => setShowDocModal(true)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}
              title="Open documentation"
            >
              <BookOpen size={16} />
            </button>
          </div>

          {notice && (
            <div className="zt-notice">
              <CheckCircle2 size={14} />
              {notice}
              <button onClick={() => setNotice('')}><X size={12} /></button>
            </div>
          )}

          {task ? (
            <>
              <section className="zt-current">
                <div className="zt-current-top">
                  <small>CURRENT TASK</small>
                  <span className={`zt-status ${statusClass(task)}`}>
                    {(task.status || 'PREPARED').replace(/_/g, ' ')}
                  </span>
                </div>
                <h3>{task.title || 'Work item'}</h3>
                <p>{task.case_id} · {task.domain || 'support'} workflow</p>
                <div className="zt-progress-title">
                  <span>Progress</span>
                  <b>{done(task) ? 'Complete' : task.status === 'PENDING_REVIEW' ? 'Needs your review' : 'Ready for review'}</b>
                </div>
                <div className="zt-progress">
                  <i style={{ width: done(task) ? '100%' : '66%' }} />
                </div>
                <div className="zt-stages">
                  <span>✓ Gathered</span>
                  <span>✓ Prepared</span>
                  <span>{done(task) ? '✓' : '○'} Approved</span>
                </div>
              </section>

              {task.bot_assignment && (
                <section className="zt-assigned">
                  <span><Bot size={16} /></span>
                  <div>
                    <small>ASSIGNED BOT</small>
                    <b>{task.bot_assignment.name}</b>
                  </div>
                  <i>● Live</i>
                  <p>{(task.bot_assignment.tools || []).slice(0, 3).map(tool => tool.replace(/_/g, ' ')).join(' · ')}</p>
                </section>
              )}

              <section className="zt-actions">
                <small>ACTIONS</small>
                <button className="zt-run" disabled={Boolean(action)} onClick={() => act('bot')}>
                  {action === 'bot' ? <LoaderCircle size={15} className="zt-spin" /> : <Sparkles size={15} />} Run workflow bot <ArrowUp size={13} />
                </button>
                {!done(task) && task.status !== 'REJECTED' && (
                  <>
                    <button className="zt-approve" disabled={Boolean(action)} onClick={() => act('approve')}>
                      {action === 'approve' ? <LoaderCircle size={15} className="zt-spin" /> : <Check size={15} />} Approve task
                    </button>
                    <button className="zt-reject" disabled={Boolean(action)} onClick={() => act('reject')}>
                      Send to human review
                    </button>
                  </>
                )}
              </section>

              {task.external_agent_result?.draft && (
                <section style={{ margin: '12px 0', padding: '10px 12px', background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '10px', fontWeight: 700, color: '#0369a1', marginBottom: '4px' }}>
                    <Sparkles size={12} /> BOT INVESTIGATION RECOMMENDATION
                  </div>
                  <p style={{ fontSize: '11px', lineHeight: '1.45', color: '#334155', margin: 0, whiteSpace: 'pre-line' }}>
                    {task.external_agent_result.draft}
                  </p>
                </section>
              )}

              <section className="zt-activity">
                <div className="zt-activity-head">
                  <small>AUDIT TRAIL TIMELINE</small>
                  <MoreHorizontal size={15} />
                </div>
                {(task.audit_log || []).slice(-6).reverse().map((entry, index) => (
                  <div className="zt-activity-row" key={`${entry.timestamp}-${index}`}>
                    <i className={index === 0 ? 'latest' : ''} />
                    <div style={{ width: '100%' }}>
                      <b>{(entry.action || 'Updated').replace(/_/g, ' ')}</b>
                      <span>{entry.actor || 'ZeroTouch'} · {time(entry.timestamp)}</span>
                      {entry.provider && (
                        <span style={{ display: 'block', fontSize: '10px', color: '#64748b', marginTop: '1px' }}>
                          Provider: {entry.provider}
                        </span>
                      )}
                      {entry.tools_called?.length > 0 && (
                        <span style={{ display: 'block', fontSize: '10px', color: '#0284c7', marginTop: '1px' }}>
                          Tools: {entry.tools_called.join(', ')}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
                {!task.audit_log?.length && (
                  <div className="zt-no-activity">
                    <Clock3 size={14} /> Task activity will appear here
                  </div>
                )}
              </section>
            </>
          ) : (
            <div className="zt-no-task">
              <span><Sparkles size={19} /></span>
              <b>No task selected</b>
              <p>Choose a task from the inbox to see its evidence, bot assignment, and actions.</p>
            </div>
          )}

          <div className="zt-context-note">
            <ShieldCheck size={14} />
            <span><b>Human in control</b>Sensitive mutations wait for supervisory approval.</span>
          </div>
        </aside>
      </div>

      {/* In-App Documentation Modal */}
      {showDocModal && (
        <div className="zt-modal-backdrop" onClick={() => setShowDocModal(false)}>
          <div className="zt-modal-container" onClick={e => e.stopPropagation()}>
            <header className="zt-modal-header">
              <h2><BookOpen size={18} /> Domain Bots, Pain Points & Edge Cases Reference</h2>
              <button onClick={() => setShowDocModal(false)} aria-label="Close modal"><X size={18} /></button>
            </header>
            <div className="zt-modal-body">
              <p style={{ color: '#64748b', marginBottom: '14px' }}>
                Complete architecture reference for the 5 domain bots, their 2–3 critical pain points, handled edge cases, and regulatory invariants. Full Markdown document available at <code>docs/DOMAIN_BOTS_AND_EDGE_CASES.md</code>.
              </p>

              <h3>1. Customer Support & Payments Bot (<code>support_bot</code>)</h3>
              <ul>
                <li><b>Pain Point 1: Stuck UPI Debited Without Credit:</b> Core Bank=DEBITED, NPCI=SUCCESS, Merchant=NOT_CREDITED. Handled via <code>RULE_PAYMENT_REVERSAL_01</code> for Prime tier (CIBIL ≥ 750). Subprime tier held for manual review. SHA-256 idempotency prevents duplicate refunds.</li>
                <li><b>Pain Point 2: RBI T+1 SLA Breach with Compensation:</b> Detects delayed refunds exceeding T+1 turnaround. Auto-calculates statutory ₹100/day penalty, dispatches NPCI bank chase API, and guarantees customer compensation.</li>
                <li><b>Pain Point 3: Bounced Bank Refund due to Frozen Account:</b> Detects bank return code <code>ACCOUNT_FROZEN</code>. Automatically credits linked digital wallet with cryptographic hash fallback.</li>
              </ul>

              <h3>2. Finance Reconciliation Bot (<code>finance_bot</code>)</h3>
              <ul>
                <li><b>Pain Point 1: 3-Way Nodal Statement Reconciliation Variance:</b> Isolates MDR fee (₹847.46) + 18% GST (₹152.54) on ₹1,000 variance in statement STMT-902 / S302. Unexplained discrepancies &gt;₹5,000 routed to Controller under SOX Section 404.</li>
                <li><b>Pain Point 2: Duplicate Payout Detection & Prevention:</b> Detects duplicate debit line collision on Vendor Invoice #4491 within 14s. Enforces <code>RULE_DUPLICATE_PAYOUT_HALT</code> and drafts clawback notice.</li>
                <li><b>Pain Point 3: Expired KYC Merchant Settlement Hold:</b> Holds batch S306 (₹145,000) because merchant PAN/GSTIN expired yesterday. Enforces RBI Payout Direction §4.2 approval gate.</li>
              </ul>

              <h3>3. IT Access & Service Desk Bot (<code>it_access_bot</code>)</h3>
              <ul>
                <li><b>Pain Point 1: Repetitive Standard Software Licensing (Okta):</b> Checks employee role in Okta and auto-provisions pre-approved standard tools (Figma Pro for Designers, GitHub Enterprise for Engineers).</li>
                <li><b>Pain Point 2: High-Risk Privileged Access Attempt:</b> Hard guardrail <code>RULE_NEVER_AUTOMATE_PRIVILEGED_ACCESS</code> unconditionally blocks autonomous granting of AWS Root or Production DB credentials. Enforces dual CISO signature.</li>
                <li><b>Pain Point 3: Zero-Touch Deprovisioning on Role Change:</b> Identifies department transfers (Marketing to Product), deprovisions obsolete SaaS seats to eliminate license waste, and protects asset ownership.</li>
              </ul>

              <h3>4. Talent & HR Operations Bot (<code>hiring_bot</code>)</h3>
              <ul>
                <li><b>Pain Point 1: Unconscious Bias & PII in Candidate Screening:</b> Fairness filter strips gender, age, photo, and address before rubric scoring. AI strictly forbidden from auto-rejecting candidates (<code>RULE_NEVER_AUTO_REJECT_CANDIDATE</code>).</li>
                <li><b>Pain Point 2: Interview Panel Scheduling Overhead:</b> Dispatches calendar invites for candidates scoring ≥80% on rubric. Auto-substitutes backup interviewers if primary declines.</li>
                <li><b>Pain Point 3: Automated Onboarding Roadmap:</b> Synthesizes 30-60-90 day onboarding checklist, pairs onboarding buddy, and tracks IT laptop delivery.</li>
              </ul>

              <h3>5. New Joiner Academy Coach (<code>academy_bot</code>)</h3>
              <ul>
                <li><b>Pain Point 1: Slow Operator Ramp-Up:</b> Provides air-gapped simulation on historical dispute cases (REPLAY-UPI-404) with zero financial risk to real customer funds.</li>
                <li><b>Pain Point 2: Inconsistent Decision-Making:</b> Tests operators on boundary conditions (CIBIL 650 threshold, ₹5,000 limit) and generates live competency radar scores.</li>
                <li><b>Pain Point 3: Standardizing Expert Workflows into L1 Skills:</b> Synthesizes typed SkillSpec from recorded actions and executes 12-case historical backtest.</li>
              </ul>

              <div style={{ marginTop: '20px', padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', color: '#475569' }}>
                  Model: <b>xAI Grok (grok-4.7)</b> · Least-Privilege Tools · Deterministic Fallback Active
                </span>
                <button
                  onClick={() => setShowDocModal(false)}
                  style={{ background: '#0f172a', color: '#fff', border: 'none', borderRadius: '6px', padding: '6px 14px', fontSize: '11px', fontWeight: 600, cursor: 'pointer' }}
                >
                  Close Guide
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
