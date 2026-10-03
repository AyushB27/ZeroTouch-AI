import React, { useState } from 'react';
import {
  Terminal, ArrowRight, CheckCircle2, Clock3, AlertTriangle,
  ShieldAlert, Sparkles, X, CornerDownLeft, Bot, Layers
} from 'lucide-react';
import { executeWorkforceCommand } from '../api';

const QUICK_COMMANDS = [
  {
    icon: '⏱️',
    label: 'Chase all refunds past SLA',
    detail: 'Autonomous workflow: Scans overdue refunds, dispatches bank chase, tracks compensation clock',
  },
  {
    icon: '📊',
    label: "Clear yesterday's pending settlement holds",
    detail: 'Auto-reconciles fee shortfalls, stops at approval gate for compliance KYC hold',
  },
  {
    icon: '🏦',
    label: "Reconcile today's bank statement against general ledger",
    detail: 'Auto-matches feed lines, flags duplicate payment for human recovery',
  },
];

export default function CommandBarModal({ isOpen, onClose, currentRole, onRefreshTasks }) {
  const [command, setCommand] = useState('');
  const [loading, setLoading] = useState(false);
  const [planResult, setPlanResult] = useState(null);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  async function handleRun(cmdText = command) {
    const clean = cmdText.trim();
    if (!clean || loading) return;
    setLoading(true);
    setError('');
    setPlanResult(null);

    try {
      const res = await executeWorkforceCommand(clean, currentRole.role_id);
      setPlanResult(res);
      if (onRefreshTasks) await onRefreshTasks();
    } catch (err) {
      setError(err.message || 'Command planner failed to execute.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-start justify-center z-50 p-4 pt-16 sm:pt-24 animate-fade-in">
      <div className="bg-white rounded-3xl max-w-2xl w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[85vh]">
        {/* Command Input Bar */}
        <div className="p-4 border-b border-slate-100 flex items-center gap-3 bg-slate-50/60">
          <div className="w-8 h-8 rounded-xl bg-[#07356b] text-cyan-300 flex items-center justify-center shrink-0">
            <Terminal size={16} />
          </div>
          <form
            onSubmit={e => {
              e.preventDefault();
              handleRun();
            }}
            className="flex-1 flex items-center gap-2"
          >
            <input
              type="text"
              value={command}
              onChange={e => setCommand(e.target.value)}
              placeholder="Command AI teammate... (e.g. 'Chase all refunds past SLA')"
              className="flex-1 bg-transparent text-sm font-semibold text-slate-800 placeholder-slate-400 outline-none"
              autoFocus
            />
            <button
              type="submit"
              disabled={loading || !command.trim()}
              className="px-3 py-1.5 rounded-xl bg-[#07356b] text-white text-xs font-bold hover:bg-[#05284f] transition disabled:opacity-40 flex items-center gap-1.5"
            >
              <span>Run</span>
              <CornerDownLeft size={12} />
            </button>
          </form>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition"
          >
            <X size={16} />
          </button>
        </div>

        {/* Quick Suggested Commands */}
        <div className="p-3 bg-slate-100/50 border-b border-slate-100 flex items-center gap-2 overflow-x-auto text-xs">
          <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 shrink-0">
            Demo Presets:
          </span>
          {QUICK_COMMANDS.map((qc, i) => (
            <button
              key={i}
              onClick={() => {
                setCommand(qc.label);
                handleRun(qc.label);
              }}
              className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 hover:border-cyan-500 hover:bg-cyan-50/50 text-[11px] font-semibold text-slate-700 shrink-0 flex items-center gap-1.5 transition shadow-2xs"
            >
              <span>{qc.icon}</span>
              <span>{qc.label}</span>
            </button>
          ))}
        </div>

        {/* Body Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-700">
              {error}
            </div>
          )}

          {loading && (
            <div className="py-12 text-center space-y-3">
              <div className="w-10 h-10 rounded-2xl bg-[#07356b] text-cyan-300 flex items-center justify-center mx-auto animate-bounce">
                <Sparkles size={20} />
              </div>
              <p className="text-xs font-bold text-slate-700">
                Multi-Agent Planner decomposing task & coordinating tool connectors...
              </p>
              <p className="text-[11px] text-slate-400">
                Planner Agent ➔ Domain Executor ➔ Autonomy Governor ➔ Action Gateway
              </p>
            </div>
          )}

          {planResult && (
            <div className="space-y-4 animate-fade-in">
              {/* Summary Pill */}
              <div className={`p-4 rounded-2xl border text-xs leading-relaxed ${
                planResult.approval_required
                  ? 'bg-amber-50 text-amber-900 border-amber-300'
                  : 'bg-emerald-50 text-emerald-900 border-emerald-300'
              }`}>
                <div className="font-extrabold flex items-center gap-1.5 mb-1">
                  {planResult.approval_required ? (
                    <>
                      <AlertTriangle size={15} className="text-amber-600" />
                      <span>Approval Checkpoint Triggered</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 size={15} className="text-emerald-600" />
                      <span>Autonomous Execution Complete</span>
                    </>
                  )}
                </div>
                <p>{planResult.summary}</p>
              </div>

              {/* Step Trace */}
              <div>
                <h4 className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 mb-2">
                  Planner Multi-Agent Decomposition ({planResult.plan_steps.length} Steps)
                </h4>
                <div className="space-y-2 border-l-2 border-[#07356b]/20 pl-3">
                  {planResult.plan_steps.map((st, i) => (
                    <div key={i} className="text-xs space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold ${
                          st.status === 'STOPPED_AT_APPROVAL_GATE'
                            ? 'bg-amber-500 text-white'
                            : 'bg-emerald-500 text-white'
                        }`}>
                          {st.step_id}
                        </span>
                        <span className="font-bold text-slate-800">{st.action}</span>
                        <span className="text-[10px] text-slate-400 font-mono">({st.agent})</span>
                      </div>
                      <p className="text-[11px] text-slate-600 pl-6">
                        {st.detail}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* If Stopped at Approval Gate */}
              {planResult.approval_case && (
                <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-xs space-y-2">
                  <div className="font-bold text-amber-900 flex items-center gap-1.5">
                    <ShieldAlert size={14} className="text-amber-700" />
                    <span>Never-Automate Guardrail Active: Manual Human Review Enforced</span>
                  </div>
                  <p className="text-amber-800 text-[11px]">
                    {planResult.approval_case.reason}
                  </p>
                  <div className="pt-2 flex justify-end">
                    <button
                      onClick={onClose}
                      className="px-4 py-1.5 rounded-xl bg-[#07356b] text-white text-xs font-bold hover:bg-[#05284f]"
                    >
                      View in Task Inbox
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {!loading && !planResult && (
            <div className="py-8 text-center text-xs text-slate-400 space-y-1">
              <p>Type a high-level command or click one of the presets above.</p>
              <p className="text-[10px]">The planner shows its multi-agent plan as it runs and asks for approval at the right points.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
