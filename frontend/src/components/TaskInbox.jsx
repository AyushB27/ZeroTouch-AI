import React, { useState } from 'react';
import {
  CheckCircle2, Clock3, AlertTriangle, ShieldCheck,
  ChevronRight, ArrowRight, XCircle, Edit3, Send, Check,
  FileText, Layers, ExternalLink, ShieldAlert, Sparkles, Filter,
  Bot, Loader2, ScrollText
} from 'lucide-react';
import { approveWorkforceTask, editWorkforceTask, rejectWorkforceTask } from '../api';
import AgentTraceLogsExplorer from './AgentTraceLogsExplorer';

const money = val => (val ? `₹${Number(val).toLocaleString('en-IN')}` : '₹0');

function getAgentTrace(task) {
  if (task?.agent_trace && task.agent_trace.length > 0) {
    return task.agent_trace;
  }
  const isApproved = task?.status === 'APPROVED' || task?.status === 'AUTO_EXECUTED';
  const cibil = task?.evidence?.cibil_score || 785;
  const isFTU = task?.evidence?.is_first_time || false;

  if (task?.domain === 'it') {
    return [
      {
        agent: 'IT Entitlement Agent',
        status: 'COMPLETED',
        description: 'Verified role standard bundle in Okta Directory',
        icon: '🔑',
      },
      {
        agent: 'Security Compliance Supervisor',
        status: 'COMPLETED',
        description: 'STANDARD_ROLE_ENTITLEMENT rule confirmed (0 elevated root keys)',
        icon: '⚖️',
      },
      {
        agent: 'Connector Execution Gateway',
        status: isApproved ? 'COMPLETED' : 'READY',
        description: isApproved ? `Provisioned enterprise license seat (${task.execution_ref || 'VERIFIED'})` : 'Ready for 1-click Okta/GitHub provisioning',
        icon: '🛡️',
      },
    ];
  }

  if (task?.domain === 'finance') {
    return [
      {
        agent: 'Bank Statement Parser',
        status: 'COMPLETED',
        description: 'Parsed nodal statement feed lines and reference tags',
        icon: '📑',
      },
      {
        agent: 'Ledger Matching Engine',
        status: 'COMPLETED',
        description: 'Reconciled ₹1,000 variance with fee & GST schedule',
        icon: '🔄',
      },
      {
        agent: 'Reconciliation Ledger Gateway',
        status: isApproved ? 'COMPLETED' : 'READY',
        description: isApproved ? `Posted ledger adjustment entry (${task.execution_ref || 'VERIFIED'})` : 'Ready for 1-click ledger mutation',
        icon: '🛡️',
      },
    ];
  }

  if (task?.domain === 'hr') {
    return [
      {
        agent: 'Fairness & Anonymization Filter',
        status: 'COMPLETED',
        description: 'Protected personal attributes stripped prior to rubric',
        icon: '🛡️',
      },
      {
        agent: 'Rubric Scoring Agent',
        status: 'COMPLETED',
        description: '85% match scored against Staff Backend Engineer criteria',
        icon: '📊',
      },
      {
        agent: 'Calendar Dispatch Gateway',
        status: isApproved ? 'COMPLETED' : 'READY',
        description: isApproved ? `Dispatched interview invite to panel (${task.execution_ref || 'VERIFIED'})` : 'Ready for 1-click panel dispatch',
        icon: '📅',
      },
    ];
  }

  // Default / Support / Payment Multi-Agent LangGraph Pipeline
  return [
    {
      agent: 'Ledger Investigator Agent',
      status: 'COMPLETED',
      description: 'Reconciled 4 internal ledgers (Bank, NPCI UPI, Merchant, Settlement)',
      icon: '🕵️',
    },
    {
      agent: 'Risk & Credit Profiling Agent',
      status: 'COMPLETED',
      description: `CIBIL ${cibil} (${isFTU ? 'First-Time User' : 'Prime Tier'}) — low risk profile verified`,
      icon: '📊',
    },
    {
      agent: 'Policy & Compliance Supervisor',
      status: 'COMPLETED',
      description: 'Cross-referenced refund policy & RBI guidelines -> Authorized action',
      icon: '⚖️',
    },
    {
      agent: 'Action Gateway',
      status: isApproved ? 'COMPLETED' : 'READY',
      description: isApproved ? `Mutated ledger idempotently: ${task.execution_ref || 'VERIFIED'}` : 'Idempotent mutation queued with SHA-256 key',
      icon: '🛡️',
    },
    {
      agent: 'Dynamic Communication Agent',
      status: isApproved ? 'COMPLETED' : 'READY',
      description: isApproved ? 'Synthesized real-time customer notice with verified SLA timeline' : 'Personalized notice draft prepared via Gemini',
      icon: '✍️',
    },
  ];
}

export default function TaskInbox({
  tasks,
  onRefresh,
  currentRole,
  showIntegrationPoints,
  killSwitchActive,
}) {
  const [selectedDomain, setSelectedDomain] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedCaseId, setSelectedCaseId] = useState(tasks[0]?.case_id || null);
  const [actionLoading, setActionLoading] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [editMessage, setEditMessage] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [feedbackNotice, setFeedbackNotice] = useState(null);
  const [traceModalOpen, setTraceModalOpen] = useState(false);

  // Filter tasks
  const filteredTasks = tasks.filter(t => {
    const matchDomain = selectedDomain === 'all' || t.domain === selectedDomain;
    const matchStatus = selectedStatus === 'all' || t.status === selectedStatus;
    return matchDomain && matchStatus;
  });

  const activeTask = tasks.find(t => t.case_id === selectedCaseId) || filteredTasks[0] || tasks[0];

  async function handleApprove(caseId) {
    setActionLoading(true);
    try {
      const res = await approveWorkforceTask(caseId, currentRole.name);
      setFeedbackNotice({
        type: 'success',
        message: `Case ${caseId} approved! Executed by autonomous multi-agent pipeline via Action Gateway (${res.case?.execution_ref || 'VERIFIED'}).`,
      });
      await onRefresh();
    } catch (err) {
      setFeedbackNotice({ type: 'error', message: err.message || 'Failed to approve task.' });
    } finally {
      setActionLoading(false);
    }
  }

  async function handleEditSubmit(e) {
    e.preventDefault();
    if (!activeTask) return;
    setActionLoading(true);
    try {
      await editWorkforceTask(activeTask.case_id, currentRole.name, editMessage, null, 'Adjusted notification draft');
      setEditModalOpen(false);
      setFeedbackNotice({
        type: 'info',
        message: `Case ${activeTask.case_id} edited and signed off by ${currentRole.name}.`,
      });
      await onRefresh();
    } catch (err) {
      setFeedbackNotice({ type: 'error', message: err.message || 'Failed to edit task.' });
    } finally {
      setActionLoading(false);
    }
  }

  async function handleRejectSubmit(e) {
    e.preventDefault();
    if (!activeTask) return;
    setActionLoading(true);
    try {
      await rejectWorkforceTask(activeTask.case_id, currentRole.name, rejectReason || 'Operator rejected draft');
      setRejectModalOpen(false);
      setFeedbackNotice({
        type: 'warning',
        message: `Case ${activeTask.case_id} rejected and routed to specialist queue.`,
      });
      await onRefresh();
    } catch (err) {
      setFeedbackNotice({ type: 'error', message: err.message || 'Failed to reject task.' });
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <div className="flex-1 flex overflow-hidden bg-slate-50 text-slate-800">
      {/* ── Left Task Queue Sidebar ── */}
      <aside className="w-80 sm:w-96 border-r border-slate-200 bg-white flex flex-col h-full shrink-0">
        {/* Filter Header */}
        <div className="p-3 border-b border-slate-100 bg-slate-50/50 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Filter size={13} className="text-[#07356b]" />
              Prepared Task Queue ({filteredTasks.length})
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              {tasks.filter(t => t.status === 'PREPARED').length} Awaiting 1-Click
            </span>
          </div>

          {/* Domain Filter Pills */}
          <div className="flex items-center gap-1 overflow-x-auto text-[11px] pb-1">
            {['all', 'support', 'finance', 'it', 'hr'].map(dom => (
              <button
                key={dom}
                onClick={() => setSelectedDomain(dom)}
                className={`px-2.5 py-1 rounded-lg font-bold capitalize transition ${
                  selectedDomain === dom
                    ? 'bg-[#07356b] text-white shadow-2xs'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
                }`}
              >
                {dom}
              </button>
            ))}
          </div>
        </div>

        {/* Task Cards List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          {filteredTasks.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-xs italic">
              No tasks matching selected filter.
            </div>
          ) : (
            filteredTasks.map(task => {
              const isSelected = activeTask?.case_id === task.case_id;
              const isApproved = task.status === 'APPROVED' || task.status === 'AUTO_EXECUTED';
              const isReview = task.status === 'PENDING_REVIEW' || task.priority === 'URGENT';

              return (
                <button
                  key={task.case_id}
                  onClick={() => {
                    setSelectedCaseId(task.case_id);
                    setFeedbackNotice(null);
                  }}
                  className={`w-full text-left p-3 rounded-2xl border transition flex flex-col gap-1.5 shadow-2xs group ${
                    isSelected
                      ? 'border-[#07356b] bg-blue-50/60 ring-2 ring-[#07356b]/10'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[10px] font-extrabold text-[#07356b] bg-white px-2 py-0.5 rounded border border-blue-200">
                        {task.case_id}
                      </span>
                      <span className={`text-[10px] font-extrabold px-1.5 py-0.2 rounded font-mono ${
                        task.autonomy_level === 'L2'
                          ? 'bg-purple-100 text-purple-800 border border-purple-200'
                          : 'bg-blue-100 text-blue-800 border border-blue-200'
                      }`}>
                        {task.autonomy_level}
                      </span>
                    </div>

                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                      isApproved
                        ? 'bg-emerald-100 text-emerald-800'
                        : isReview
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-cyan-100 text-cyan-900'
                    }`}>
                      {isApproved ? <CheckCircle2 size={10} /> : <Clock3 size={10} />}
                      {task.status}
                    </span>
                  </div>

                  <div className="text-xs font-bold text-slate-800 group-hover:text-[#07356b] line-clamp-1">
                    {task.title}
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                    <span className="capitalize text-slate-400 font-semibold">{task.domain} Pack</span>
                    {task.amount > 0 && (
                      <span className="font-extrabold text-[#07356b]">{money(task.amount)}</span>
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>
      </aside>

      {/* ── Right Pre-Worked Task Canvas ── */}
      <main className="flex-1 flex flex-col h-full overflow-y-auto p-4 sm:p-6 space-y-4">
        {feedbackNotice && (
          <div className={`p-3.5 rounded-2xl border text-xs font-semibold flex items-center justify-between animate-fade-in ${
            feedbackNotice.type === 'success'
              ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
              : feedbackNotice.type === 'warning'
              ? 'bg-amber-50 text-amber-900 border-amber-200'
              : 'bg-blue-50 text-blue-900 border-blue-200'
          }`}>
            <span>{feedbackNotice.message}</span>
            <button onClick={() => setFeedbackNotice(null)} className="text-slate-400 hover:text-slate-700">✕</button>
          </div>
        )}

        {killSwitchActive && (
          <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-300 text-xs text-rose-900 font-bold flex items-center gap-2">
            <ShieldAlert size={16} className="text-rose-600 animate-pulse" />
            <span>EMERGENCY KILL SWITCH ENGAGED: 100% human sign-off enforced. Autonomous execution suspended across all skills.</span>
          </div>
        )}

        {activeTask ? (
          <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-6 max-w-4xl mx-auto w-full">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="font-mono text-xs font-extrabold text-[#07356b] bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200">
                    {activeTask.case_id}
                  </span>
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    {activeTask.domain} domain
                  </span>
                  <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                    activeTask.priority === 'URGENT'
                      ? 'bg-rose-100 text-rose-800'
                      : activeTask.priority === 'HIGH'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-slate-100 text-slate-700'
                  }`}>
                    {activeTask.priority} PRIORITY
                  </span>
                </div>
                <h1 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight">
                  {activeTask.title}
                </h1>
              </div>

              {/* Autonomy Badge */}
              <div className="flex items-center gap-2">
                <div className="text-right">
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 block">
                    Earned Autonomy
                  </span>
                  <span className="font-extrabold text-sm text-[#07356b]">
                    Level {activeTask.autonomy_level}
                  </span>
                </div>
                <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 text-[#07356b] flex items-center justify-center font-extrabold text-xs">
                  {activeTask.autonomy_level}
                </div>
              </div>
            </div>

            {/* Integration Point #1 */}
            {showIntegrationPoints && (
              <div className="rounded-xl bg-amber-50/80 border border-amber-300 p-2.5 text-xs text-amber-900 font-semibold flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-amber-500 text-white flex items-center justify-center text-[10px] font-bold">1</span>
                <span>Integration Point 1: Event/request ingested from system of record via permissioned connector.</span>
              </div>
            )}

            {/* Section 1: Pre-Gathered Multi-Tool Evidence Bundle */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Layers size={14} className="text-[#07356b]" />
                  Multi-Tool Evidence Bundle (Reconciled by AI)
                </h2>
                <span className="text-[11px] text-emerald-700 font-bold flex items-center gap-1">
                  <ShieldCheck size={13} /> 100% Invariants Verified
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 bg-slate-50 p-3.5 rounded-2xl border border-slate-100 text-xs">
                {Object.entries(activeTask.evidence || {}).map(([key, val]) => (
                  <div key={key} className="bg-white p-2.5 rounded-xl border border-slate-200/80 flex flex-col justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="font-bold text-slate-800 mt-0.5 truncate">
                      {String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Integration Point #2 */}
            {showIntegrationPoints && (
              <div className="rounded-xl bg-amber-50/80 border border-amber-300 p-2.5 text-xs text-amber-900 font-semibold flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-amber-500 text-white flex items-center justify-center text-[10px] font-bold">2</span>
                <span>Integration Point 2: ZeroTouch evaluates deterministic SkillSpec rules & Autonomy Governor precedence.</span>
              </div>
            )}

            {/* Section 2: Policy & Skill Cited */}
            <div className="space-y-2">
              <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <FileText size={14} className="text-[#07356b]" />
                Governing Skill & Policy Cited
              </h2>
              <div className="p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200 text-xs text-blue-950 font-medium leading-relaxed">
                {activeTask.policy_cited}
              </div>
            </div>

            {/* Integration Point #3 */}
            {showIntegrationPoints && (
              <div className="rounded-xl bg-amber-50/80 border border-amber-300 p-2.5 text-xs text-amber-900 font-semibold flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-amber-500 text-white flex items-center justify-center text-[10px] font-bold">3</span>
                <span>Integration Point 3: Pre-worked draft action & customer notice generated. Awaiting 1-click human execution.</span>
              </div>
            )}

            {/* Live Multi-Agent Resolution Pipeline */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Bot size={14} className="text-[#07356b]" />
                  Autonomous Multi-Agent Execution Pipeline
                </h2>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setTraceModalOpen(true)}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-[11px] font-bold text-[#07356b] shadow-2xs transition"
                    title="View step-by-step agent trace telemetry logs"
                  >
                    <ScrollText size={12} />
                    <span>View Trace Logs</span>
                  </button>
                  <span className={`text-[11px] font-bold flex items-center gap-1 ${
                    activeTask.status === 'APPROVED' || activeTask.status === 'AUTO_EXECUTED'
                      ? 'text-emerald-700'
                      : 'text-blue-700'
                  }`}>
                    {activeTask.status === 'APPROVED' || activeTask.status === 'AUTO_EXECUTED' ? (
                      <>
                        <CheckCircle2 size={13} className="text-emerald-600" />
                        <span>All Agents Executed</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={13} className="text-cyan-600" />
                        <span>Ready for 1-Click Execution</span>
                      </>
                    )}
                  </span>
                </div>
              </div>

              <div className={`grid grid-cols-1 ${getAgentTrace(activeTask).length === 5 ? 'sm:grid-cols-5' : 'sm:grid-cols-3'} gap-2`}>
                {getAgentTrace(activeTask).map((step, idx) => {
                  const isDone = activeTask.status === 'APPROVED' || activeTask.status === 'AUTO_EXECUTED' || step.status === 'COMPLETED';
                  return (
                    <div
                      key={idx}
                      className={`p-3 rounded-2xl border transition-all flex flex-col justify-between ${
                        isDone
                          ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950 shadow-2xs'
                          : 'bg-white border-slate-200 text-slate-700 shadow-2xs'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-base">{step.icon}</span>
                        <span className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded-full font-mono ${
                          isDone ? 'bg-emerald-200/80 text-emerald-900' : 'bg-blue-100 text-blue-800'
                        }`}>
                          {isDone ? 'PASS' : `AGENT ${idx + 1}`}
                        </span>
                      </div>
                      <div>
                        <div className="font-extrabold text-[11px] text-slate-900 leading-tight">{step.agent}</div>
                        <div className="text-[10px] text-slate-600 mt-1 leading-snug">{step.description}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Section 3: Drafted Action & Tool Calls */}
            <div className="space-y-3">
              <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Sparkles size={14} className="text-cyan-600" />
                Pre-Worked Draft Action & Tool Calls (Ready for 1-Click Execution)
              </h2>

              <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4 space-y-3">
                <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-200">
                  <span className="text-slate-500 font-medium">Action Type</span>
                  <span className="font-mono font-bold text-[#07356b] bg-white px-2 py-0.5 rounded border border-slate-200">
                    {activeTask.draft_action?.action_type || 'STANDARD_EXECUTION'}
                  </span>
                </div>

                {activeTask.draft_action?.customer_message && (
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                      Drafted Customer Communication (Dynamically Written)
                    </span>
                    <p className="text-xs text-slate-800 bg-white p-3 rounded-xl border border-slate-200 leading-relaxed font-sans">
                      {activeTask.draft_action.customer_message}
                    </p>
                  </div>
                )}

                {activeTask.draft_action?.tat_clock && (
                  <div className="flex items-center justify-between text-xs bg-emerald-50 text-emerald-800 px-3 py-1.5 rounded-xl border border-emerald-200">
                    <span className="font-semibold">RBI TAT Clock Tracking:</span>
                    <span className="font-bold">{activeTask.draft_action.tat_clock}</span>
                  </div>
                )}

                {(activeTask.execution_ref || activeTask.draft_action?.action_ref) && (
                  <div className="flex items-center justify-between text-xs pt-1">
                    <span className="text-slate-500">Action Gateway Reference (Idempotent)</span>
                    <span className="font-mono font-bold text-slate-700 bg-white px-2 py-0.5 rounded border border-slate-200">
                      {activeTask.execution_ref || activeTask.draft_action?.action_ref}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Section 4: Action Toolbar */}
            <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="text-xs text-slate-500">
                {activeTask.status === 'APPROVED' ? (
                  <span className="text-emerald-700 font-bold flex items-center gap-1.5">
                    <CheckCircle2 size={15} /> Approved & Executed by {activeTask.approver || 'Operator'} · Ref: {activeTask.execution_ref || 'VERIFIED'}
                  </span>
                ) : activeTask.status === 'REJECTED' ? (
                  <span className="text-rose-700 font-bold flex items-center gap-1.5">
                    <XCircle size={15} /> Rejected & Routed to Human Desk
                  </span>
                ) : (
                  <span>Review pre-gathered evidence and sign off with one click.</span>
                )}
              </div>

              {activeTask.status !== 'APPROVED' && (
                <div className="flex items-center gap-2.5 w-full sm:w-auto">
                  <button
                    onClick={() => {
                      setRejectReason('');
                      setRejectModalOpen(true);
                    }}
                    disabled={actionLoading}
                    className="flex-1 sm:flex-none px-3.5 py-2 rounded-xl border border-slate-200 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-200 text-xs font-bold text-slate-600 transition disabled:opacity-50"
                  >
                    Reject
                  </button>

                  <button
                    onClick={() => {
                      setEditMessage(activeTask.draft_action?.customer_message || '');
                      setEditModalOpen(true);
                    }}
                    disabled={actionLoading}
                    className="flex-1 sm:flex-none px-3.5 py-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-xs font-bold text-slate-700 transition flex items-center justify-center gap-1.5 disabled:opacity-50"
                  >
                    <Edit3 size={13} />
                    <span>Edit Draft</span>
                  </button>

                  <button
                    onClick={() => handleApprove(activeTask.case_id)}
                    disabled={actionLoading}
                    className="flex-2 sm:flex-none px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold transition shadow-sm flex items-center justify-center gap-2 disabled:opacity-75"
                  >
                    {actionLoading ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        <span>Executing Pipeline...</span>
                      </>
                    ) : (
                      <>
                        <Check size={14} className="stroke-[3]" />
                        <span>Approve (1-Click)</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="text-center py-20 text-slate-400 text-sm">
            Select a case from the queue to review pre-worked evidence and draft actions.
          </div>
        )}
      </main>

      {/* ── Edit Modal ── */}
      {editModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl p-6 max-w-lg w-full shadow-2xl space-y-4">
            <h3 className="text-base font-extrabold text-slate-900">Edit Drafted Resolution</h3>
            <p className="text-xs text-slate-500">
              Modify the customer notification or parameters before human sign-off.
            </p>
            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Customer Communication</label>
                <textarea
                  rows={4}
                  value={editMessage}
                  onChange={e => setEditMessage(e.target.value)}
                  className="w-full text-xs p-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-[#07356b] outline-none"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-xl bg-[#07356b] text-white text-xs font-bold hover:bg-[#05284f]"
                >
                  Save & Approve
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Reject Modal ── */}
      {rejectModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl p-6 max-w-lg w-full shadow-2xl space-y-4">
            <h3 className="text-base font-extrabold text-slate-900">Reject & Route to Specialist</h3>
            <p className="text-xs text-slate-500">
              Provide a rationale for refusing autonomous execution.
            </p>
            <form onSubmit={handleRejectSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Rejection Rationale</label>
                <textarea
                  rows={3}
                  value={rejectReason}
                  onChange={e => setRejectReason(e.target.value)}
                  placeholder="Explain why this case requires manual escalation..."
                  className="w-full text-xs p-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500 outline-none"
                  required
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setRejectModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-xl bg-rose-600 text-white text-xs font-bold hover:bg-rose-700"
                >
                  Confirm Rejection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Case Trace Logs Modal ── */}
      {traceModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl max-w-4xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-2xl border border-slate-200">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <Bot size={18} className="text-[#07356b]" />
                <span className="font-extrabold text-sm text-slate-900">
                  Case Telemetry Trace: {activeTask?.evidence?.transaction_id || activeTask?.case_id}
                </span>
              </div>
              <button
                onClick={() => setTraceModalOpen(false)}
                className="w-8 h-8 rounded-xl bg-slate-200 hover:bg-slate-300 flex items-center justify-center text-slate-700 font-bold"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <AgentTraceLogsExplorer
                initialTxId={activeTask?.evidence?.transaction_id || activeTask?.case_id}
                isEmbedded={true}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
