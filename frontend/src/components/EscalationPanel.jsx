import React from 'react';
import { AlertTriangle, User, Lightbulb } from 'lucide-react';

export default function EscalationPanel({ result }) {
  if (!result || result.resolution_status !== 'ESCALATED') return null;

  return (
    <div className="bg-rose-50 rounded-xl border border-rose-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle size={16} className="text-rose-500" />
        <h3 className="text-sm font-bold text-rose-800">Human Review Required</h3>
        {result.support_case && (
          <span className="ml-auto text-xs font-mono font-bold text-rose-700 bg-rose-100 border border-rose-300 px-2 py-0.5 rounded">
            {result.support_case}
          </span>
        )}
      </div>

      <div className="space-y-4">
        <div>
          <div className="text-[10px] font-bold tracking-widest text-rose-400 uppercase mb-1">Reason</div>
          <p className="text-xs text-rose-700 leading-relaxed">{result.escalation_reason}</p>
        </div>

        {result.evidence && (
          <div>
            <div className="text-[10px] font-bold tracking-widest text-rose-400 uppercase mb-2">Evidence Summary</div>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Bank', value: result.evidence.bank },
                { label: 'Network', value: result.evidence.network },
                { label: 'Merchant', value: result.evidence.merchant },
                { label: 'Settlement', value: result.evidence.settlement },
                { label: 'Amount', value: `₹${result.evidence.amount.toLocaleString('en-IN')}` },
                { label: 'Risk', value: `${(result.evidence.risk * 100).toFixed(0)}%` },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between bg-white border border-rose-100 rounded-lg px-3 py-2">
                  <span className="text-[10px] font-semibold text-rose-400 uppercase">{label}</span>
                  <span className="text-xs font-bold text-rose-800">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {result.suggested_resolution && (
          <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3">
            <Lightbulb size={14} className="text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <div className="text-[10px] font-bold tracking-widest text-amber-500 uppercase mb-1">Suggested Resolution</div>
              <p className="text-xs text-amber-800 leading-relaxed">{result.suggested_resolution}</p>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between border-t border-rose-200 pt-3">
          <div className="flex items-center gap-2">
            <User size={12} className="text-rose-400" />
            <span className="text-[10px] text-rose-500 font-medium uppercase tracking-wide">Priority: HIGH</span>
          </div>
          <span className="text-[10px] font-bold bg-rose-200 text-rose-800 px-2 py-0.5 rounded">AWAITING HUMAN REVIEW</span>
        </div>
      </div>
    </div>
  );
}
