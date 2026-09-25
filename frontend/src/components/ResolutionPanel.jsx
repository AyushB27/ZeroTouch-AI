import React from 'react';
import { CheckCircle2, XCircle, Shield, Zap, Bell, TicketX } from 'lucide-react';

export default function ResolutionPanel({ result }) {
  if (!result) return null;

  const isResolved = result.resolution_status === 'RESOLVED';
  const isEscalated = result.resolution_status === 'ESCALATED';
  const isNoAction = result.resolution_status === 'NO_ACTION';

  if (isNoAction) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h3 className="text-xs font-bold tracking-widest text-slate-400 uppercase mb-4">Resolution</h3>
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <CheckCircle2 size={32} className="text-emerald-500 mb-3" />
          <div className="font-semibold text-slate-800">No Action Required</div>
          <div className="text-xs text-slate-500 mt-1">Transaction is consistent across all systems</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <h3 className="text-xs font-bold tracking-widest text-slate-400 uppercase mb-4">Resolution</h3>
      <div className="space-y-3">
        <Row icon={<Shield size={14} className="text-violet-500" />} label="Decision" value={result.decision.replace('_', ' ')} highlight={isResolved ? 'success' : isEscalated ? 'danger' : 'neutral'} />
        <Row icon={<Zap size={14} className="text-teal-500" />} label="Policy" value={result.authorized ? 'AUTHORIZED' : isNoAction ? 'N/A' : 'DENIED'} highlight={result.authorized ? 'success' : 'neutral'} />
        {result.action_id && (
          <Row icon={<Zap size={14} className="text-blue-500" />} label="Action" value={result.action_id} highlight="success" mono />
        )}
        {result.verification_status && (
          <Row icon={<CheckCircle2 size={14} className="text-emerald-500" />} label="Verification" value={result.verification_status} highlight="success" />
        )}
        <Row
          icon={<Bell size={14} className="text-sky-500" />}
          label="Customer"
          value={result.notification_sent ? 'NOTIFIED' : 'NOT NOTIFIED'}
          highlight={result.notification_sent ? 'success' : 'neutral'}
        />
        <Row
          icon={<TicketX size={14} className="text-slate-400" />}
          label="Support Ticket"
          value={result.support_case ? result.support_case : 'NOT REQUIRED'}
          highlight={result.support_case ? 'danger' : 'success'}
        />
      </div>
    </div>
  );
}

function Row({ icon, label, value, highlight, mono }) {
  const colorMap = {
    success: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    danger: 'text-rose-700 bg-rose-50 border-rose-200',
    neutral: 'text-slate-600 bg-slate-50 border-slate-200',
  };
  const cls = colorMap[highlight] || colorMap.neutral;
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2 text-slate-500">
        {icon}
        <span className="text-xs font-medium">{label}</span>
      </div>
      <span className={`text-xs font-bold px-2 py-0.5 rounded border ${cls} ${mono ? 'font-mono' : ''}`}>
        {value}
      </span>
    </div>
  );
}
