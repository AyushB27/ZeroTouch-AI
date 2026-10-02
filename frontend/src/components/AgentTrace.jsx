import React, { useRef, useEffect } from 'react';
import {
  CheckCircle2, XCircle, Info, Loader2, Zap, Shield,
  Building2, Radio, Store, Banknote, Bell, AlertTriangle, FileText
} from 'lucide-react';

const TYPE_STYLE = {
  INVESTIGATION: { dot: 'bg-paytm-primary', label: 'text-blue-700',   bg: 'bg-blue-50'   },
  POLICY:        { dot: 'bg-violet-500',    label: 'text-violet-700',  bg: 'bg-violet-50' },
  ACTION:        { dot: 'bg-teal-500',      label: 'text-teal-700',    bg: 'bg-teal-50'   },
  VERIFICATION:  { dot: 'bg-emerald-500',   label: 'text-emerald-700', bg: 'bg-emerald-50'},
  NOTIFICATION:  { dot: 'bg-sky-500',       label: 'text-sky-700',     bg: 'bg-sky-50'    },
  ESCALATION:    { dot: 'bg-rose-500',      label: 'text-rose-700',    bg: 'bg-rose-50'   },
  ERROR:         { dot: 'bg-red-400',       label: 'text-red-600',     bg: 'bg-red-50'    },
};

const STEP_ICONS = {
  check_bank_status:    Building2,
  check_network_status: Radio,
  check_merchant_ledger:Store,
  check_settlement:     Banknote,
  evaluate_policy:      Shield,
  initiate_reversal:    Zap,
  chase_bank_sla:       Zap,
  offer_wallet_credit:  Zap,
  generate_itemized_explanation: FileText,
  flag_compliance_hold: AlertTriangle,
  send_notification:    Bell,
  create_support_case:  AlertTriangle,
  search_policy:        FileText,
  human_decision:       CheckCircle2,
};

function StatusIcon({ status }) {
  if (status === 'SUCCESS') return <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />;
  if (status === 'FAILED')  return <XCircle      size={13} className="text-red-400    shrink-0" />;
  return <Info size={13} className="text-slate-400 shrink-0" />;
}

function EventRow({ event, isLast }) {
  const style = TYPE_STYLE[event.type] || TYPE_STYLE.INVESTIGATION;
  const StepIcon = STEP_ICONS[event.step] || Info;
  return (
    <div className="flex gap-3 group">
      {/* Timeline spine */}
      <div className="flex flex-col items-center pt-1 shrink-0">
        <div className={`w-2 h-2 rounded-full ${style.dot} ring-2 ring-white`} />
        {!isLast && <div className="w-px flex-1 bg-slate-100 mt-1" />}
      </div>
      {/* Content */}
      <div className={`flex-1 mb-3 rounded-lg px-3 py-2.5 border border-transparent ${style.bg}`}>
        <div className="flex items-start gap-2">
          <StepIcon size={13} className={`mt-0.5 shrink-0 ${style.label}`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <StatusIcon status={event.status} />
              <span className={`text-[11px] font-bold uppercase tracking-wider ${style.label}`}>{event.type}</span>
              <span className="text-[10px] text-slate-400 font-mono">{event.step}</span>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">{event.message}</p>
            <div className="text-[10px] text-slate-400 mt-1 font-mono">
              {new Date(event.timestamp).toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ResultSummary({ result }) {
  if (!result) return null;
  const isResolved  = result.resolution_status === 'RESOLVED';
  const isEscalated = result.resolution_status === 'ESCALATED';
  const isNoAction  = result.resolution_status === 'NO_ACTION';

  const bg    = isResolved ? 'bg-emerald-50 border-emerald-200' : isEscalated ? 'bg-rose-50 border-rose-200' : 'bg-slate-50 border-slate-200';
  const color = isResolved ? 'text-emerald-800' : isEscalated ? 'text-rose-800' : 'text-slate-700';
  const Icon  = isResolved ? CheckCircle2 : isEscalated ? AlertTriangle : CheckCircle2;

  return (
    <div className={`mx-4 mb-4 rounded-xl border p-4 ${bg}`}>
      <div className={`flex items-center gap-2 font-bold text-sm mb-3 ${color}`}>
        <Icon size={16} />
        {result.decision?.replace(/_/g, ' ')}
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        {[
          { k: 'Decision',     v: result.decision?.replace(/_/g, ' ') },
          { k: 'Authorized',   v: result.authorized ? 'Yes' : 'No'    },
          { k: 'Action Ref',   v: result.action_id || '—'             },
          { k: 'Verified',     v: result.verification_status || '—'   },
          { k: 'Customer',     v: result.notification_sent ? 'Notified' : 'Not notified' },
          { k: 'Ticket',       v: result.support_case || 'Not required' },
        ].map(({ k, v }) => (
          <div key={k} className={`${bg} rounded p-2 border border-white/80`}>
            <div className="text-[10px] font-semibold text-slate-500 uppercase">{k}</div>
            <div className={`font-bold mt-0.5 truncate ${color}`}>{v}</div>
          </div>
        ))}
      </div>
      {result.escalation_reason && (
        <div className="mt-3 text-xs text-rose-700 bg-rose-100 rounded p-2 leading-relaxed">
          <span className="font-bold">Escalation reason: </span>{result.escalation_reason}
        </div>
      )}
      {result.suggested_resolution && (
        <div className="mt-2 text-xs text-amber-800 bg-amber-50 rounded p-2 leading-relaxed border border-amber-100">
          <span className="font-bold">Suggested: </span>{result.suggested_resolution}
        </div>
      )}
    </div>
  );
}

export default function AgentTrace({ events, result, isRunning }) {
  const bottomRef = useRef(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [events.length]);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between shrink-0">
        <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Live Agent Trace</div>
        {isRunning && (
          <div className="flex items-center gap-1.5 text-paytm-primary text-xs font-semibold">
            <Loader2 size={12} className="animate-spin" /> Processing...
          </div>
        )}
        {!isRunning && result && (
          <span className="text-xs font-bold text-emerald-600">{events.length} steps recorded</span>
        )}
      </div>

      {/* Empty state */}
      {events.length === 0 && !isRunning && (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-slate-300">
          <Zap size={40} className="opacity-40" />
          <p className="text-sm">Select a transaction and run ZeroTouch to see the agent trace</p>
        </div>
      )}

      {/* Events */}
      <div className="flex-1 overflow-y-auto px-5 pt-4">
        {events.map((ev, i) => (
          <EventRow key={i} event={ev} isLast={i === events.length - 1 && !isRunning} />
        ))}
        {isRunning && (
          <div className="flex gap-3 mb-3">
            <div className="flex flex-col items-center pt-1 shrink-0">
              <div className="w-2 h-2 rounded-full bg-paytm-primary animate-pulse ring-2 ring-white" />
            </div>
            <div className="flex-1 bg-blue-50 rounded-lg px-3 py-2.5 border border-blue-100">
              <div className="flex items-center gap-2 text-xs text-paytm-primary font-semibold">
                <Loader2 size={12} className="animate-spin" /> Agent is working...
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Result summary */}
      {result && !isRunning && <ResultSummary result={result} />}
    </div>
  );
}
