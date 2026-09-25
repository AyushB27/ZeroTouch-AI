import React from 'react';
import { Zap } from 'lucide-react';

const STATUS_MAP = {
  PENDING: { label: 'EXCEPTION', color: 'bg-amber-100 text-amber-800 border-amber-300' },
  RESOLVED: { label: 'RESOLVED', color: 'bg-emerald-100 text-emerald-800 border-emerald-300' },
  ESCALATED: { label: 'ESCALATED', color: 'bg-rose-100 text-rose-800 border-rose-300' },
  NO_ACTION: { label: 'CONSISTENT', color: 'bg-slate-100 text-slate-700 border-slate-300' },
};

export default function TransactionHeader({ transaction }) {
  if (!transaction) return null;
  const statusInfo = STATUS_MAP[transaction.resolution_status] || STATUS_MAP.PENDING;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center">
            <Zap size={18} className="text-white" />
          </div>
          <div>
            <div className="text-xl font-bold text-slate-900 tracking-tight">
              {transaction.transaction_id}
            </div>
            <div className="text-3xl font-bold text-slate-800 mt-0.5">
              ₹{transaction.amount.toLocaleString('en-IN')}
            </div>
          </div>
        </div>
        <div className="text-right">
          <span className={`inline-block px-3 py-1.5 rounded-lg border text-xs font-bold tracking-wider ${statusInfo.color}`}>
            {statusInfo.label}
          </span>
          <div className="text-xs text-slate-400 mt-2 font-mono">
            Risk: {(transaction.risk_score * 100).toFixed(0)}%
          </div>
        </div>
      </div>
    </div>
  );
}
