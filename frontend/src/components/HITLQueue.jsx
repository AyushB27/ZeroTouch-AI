import React, { useState } from 'react';
import {
  AlertTriangle, CheckCircle2, XCircle, MessageSquare,
  User, Clock, Loader2, ShieldAlert, ChevronDown, ChevronUp,
  Building2, Radio, Store, Banknote
} from 'lucide-react';
import { submitHumanDecision, getEvents } from '../api';

const ACTIONS = [
  {
    id: 'APPROVE_REFUND',
    label: 'Approve Refund',
    icon: CheckCircle2,
    style: 'bg-emerald-600 hover:bg-emerald-700 text-white',
    desc: 'Issue a full refund to the customer',
  },
  {
    id: 'REJECT',
    label: 'Reject Case',
    icon: XCircle,
    style: 'bg-slate-200 hover:bg-slate-300 text-slate-800',
    desc: 'Close without action',
  },
  {
    id: 'REQUEST_MORE_INFO',
    label: 'Request Info',
    icon: MessageSquare,
    style: 'bg-amber-100 hover:bg-amber-200 text-amber-800',
    desc: 'Ask customer for more details',
  },
];

function EvidenceGrid({ tx }) {
  const fields = [
    { label: 'Bank',       icon: Building2, value: tx.bank_status       },
    { label: 'Network',    icon: Radio,     value: tx.network_status     },
    { label: 'Merchant',   icon: Store,     value: tx.merchant_status    },
    { label: 'Settlement', icon: Banknote,  value: tx.settlement_status  },
  ];
  return (
    <div className="grid grid-cols-2 gap-2 mb-3">
      {fields.map(f => (
        <div key={f.label} className="bg-white border border-slate-100 rounded-lg p-2.5">
          <div className="flex items-center gap-1 mb-1">
            <f.icon size={11} className="text-slate-400" />
            <span className="text-[10px] font-bold text-slate-400 uppercase">{f.label}</span>
          </div>
          <div className="text-xs font-bold text-slate-800 truncate">{f.value}</div>
        </div>
      ))}
    </div>
  );
}

function CaseCard({ tx, onDecisionMade }) {
  const [expanded,   setExpanded]   = useState(true);
  const [notes,      setNotes]      = useState('');
  const [agentName,  setAgentName]  = useState('Support Agent');
  const [submitting, setSubmitting] = useState(null);
  const [done,       setDone]       = useState(false);
  const [doneAction, setDoneAction] = useState(null);

  const handleAction = async (actionId) => {
    setSubmitting(actionId);
    try {
      await submitHumanDecision(tx.transaction_id, actionId, agentName, notes);
      setDone(true);
      setDoneAction(actionId);
      await onDecisionMade();
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className={`rounded-xl border shadow-sm overflow-hidden ${done ? 'opacity-60' : ''}`}>
      {/* Case header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-rose-50 border-b border-rose-100 cursor-pointer"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-2">
          <ShieldAlert size={14} className="text-rose-600" />
          <span className="font-bold text-sm text-rose-800">{tx.transaction_id}</span>
          <span className="font-mono text-xs text-rose-500">₹{tx.amount.toLocaleString('en-IN')}</span>
          <span className="text-[10px] bg-rose-200 text-rose-700 font-bold px-1.5 py-0.5 rounded uppercase">
            {tx.workflow_type}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-rose-500 flex items-center gap-1">
            <Clock size={10} /> AWAITING REVIEW
          </span>
          {expanded ? <ChevronUp size={14} className="text-rose-400" /> : <ChevronDown size={14} className="text-rose-400" />}
        </div>
      </div>

      {expanded && (
        <div className="p-4 bg-slate-50 space-y-3">
          {/* Evidence */}
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">System Evidence</div>
          <EvidenceGrid tx={tx} />

          {/* Customer Profile & CIBIL */}
          <div className="bg-white border border-slate-200/80 rounded-lg p-3">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Customer Profile</span>
              {tx.is_first_time_user && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                  ⭐ First-Time User
                </span>
              )}
            </div>
            <div className="flex items-center justify-between">
              <div className="font-bold text-xs text-slate-800">{tx.customer_name || 'Paytm Customer'}</div>
              <div className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
                (tx.cibil_score || 750) >= 750 ? 'bg-emerald-100 text-emerald-800' :
                (tx.cibil_score || 750) >= 650 ? 'bg-blue-100 text-blue-800' :
                'bg-rose-100 text-rose-800'
              }`}>
                CIBIL: {tx.cibil_score || 750} ({(tx.cibil_score || 750) >= 750 ? 'Prime' : (tx.cibil_score || 750) >= 650 ? 'Good' : 'Subprime'})
              </div>
            </div>
          </div>

          {/* Risk + amount */}
          <div className="flex gap-2 mb-2">
            <div className="flex-1 bg-white border border-slate-100 rounded-lg p-2.5">
              <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Fraud Risk</div>
              <div className={`text-base font-black ${tx.risk_score >= 0.5 ? 'text-rose-600' : 'text-amber-600'}`}>
                {(tx.risk_score * 100).toFixed(0)}%
              </div>
            </div>
            <div className="flex-1 bg-white border border-slate-100 rounded-lg p-2.5">
              <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Amount</div>
              <div className="text-base font-black text-slate-800">₹{tx.amount.toLocaleString('en-IN')}</div>
            </div>
            <div className="flex-1 bg-white border border-slate-100 rounded-lg p-2.5">
              <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Prior Refund</div>
              <div className={`text-base font-black ${tx.previous_refund ? 'text-rose-600' : 'text-emerald-600'}`}>
                {tx.previous_refund ? 'Yes' : 'No'}
              </div>
            </div>
          </div>

          {/* AI Synthesized Draft (No Pre-built messages) */}
          {tx.dynamic_message && (
            <div className="bg-amber-50/70 border border-amber-200/80 rounded-lg p-3 text-xs">
              <div className="text-[10px] font-bold text-amber-800 uppercase tracking-wider mb-1">
                Draft Customer Notice (Synthesized by Communication Agent)
              </div>
              <p className="text-slate-700 italic">"{tx.dynamic_message}"</p>
            </div>
          )}

          {done ? (
            <div className={`flex items-center gap-2 py-3 px-4 rounded-lg font-bold text-sm ${
              doneAction === 'APPROVE_REFUND' ? 'bg-emerald-100 text-emerald-800' :
              doneAction === 'REJECT'         ? 'bg-slate-200 text-slate-700'     :
              'bg-amber-100 text-amber-800'
            }`}>
              <CheckCircle2 size={16} />
              {doneAction === 'APPROVE_REFUND' ? 'Refund approved and processed'  :
               doneAction === 'REJECT'         ? 'Case rejected'                  :
               'More information requested from customer'}
            </div>
          ) : (
            <>
              {/* Agent name */}
              <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-2">
                <User size={13} className="text-slate-400" />
                <input
                  className="flex-1 text-xs outline-none placeholder-slate-300"
                  placeholder="Your name (optional)"
                  value={agentName}
                  onChange={e => setAgentName(e.target.value)}
                />
              </div>

              {/* Notes */}
              <textarea
                rows={2}
                className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 bg-white outline-none placeholder-slate-300 resize-none"
                placeholder="Add notes (optional)..."
                value={notes}
                onChange={e => setNotes(e.target.value)}
              />

              {/* Action buttons */}
              <div className="grid grid-cols-3 gap-2">
                {ACTIONS.map(a => {
                  const Icon = a.icon;
                  const isLoading = submitting === a.id;
                  return (
                    <button
                      key={a.id}
                      onClick={() => handleAction(a.id)}
                      disabled={!!submitting}
                      title={a.desc}
                      className={`flex flex-col items-center gap-1 py-2.5 px-2 rounded-lg font-bold text-[11px] transition-colors disabled:opacity-60 disabled:cursor-not-allowed ${a.style}`}
                    >
                      {isLoading
                        ? <Loader2 size={14} className="animate-spin" />
                        : <Icon size={14} />
                      }
                      {a.label}
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function HITLQueue({ escalated, onDecision }) {
  if (escalated.length === 0) return (
    <div className="h-full flex flex-col items-center justify-center gap-3 text-slate-300 px-6 text-center">
      <CheckCircle2 size={44} className="opacity-30" />
      <div className="text-sm font-medium">No cases awaiting human review</div>
      <div className="text-xs text-slate-400">When ZeroTouch escalates a case, it will appear here with full investigation context pre-loaded.</div>
    </div>
  );

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100 bg-rose-50 shrink-0 flex items-center justify-between">
        <div className="text-xs font-bold text-rose-700 uppercase tracking-wider flex items-center gap-1.5">
          <ShieldAlert size={13} /> Human Review Queue
        </div>
        <span className="text-xs font-bold text-rose-600 bg-rose-100 px-2 py-0.5 rounded-full">
          {escalated.length} case{escalated.length !== 1 ? 's' : ''} pending
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {escalated.map(tx => (
          <CaseCard key={tx.transaction_id} tx={tx} onDecisionMade={onDecision} />
        ))}
      </div>
    </div>
  );
}
