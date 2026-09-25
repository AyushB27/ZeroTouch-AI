import React from 'react';
import { FileText } from 'lucide-react';

function generateNarrative(evidence) {
  if (!evidence) return [];
  const lines = [];
  if (evidence.bank === 'DEBITED') lines.push(`Customer was debited ₹${evidence.amount.toLocaleString('en-IN')} from their account.`);
  if (evidence.network === 'SUCCESS') lines.push('Payment network confirmed the transaction as successful.');
  if (evidence.network === 'UNKNOWN') lines.push('Payment network status is UNKNOWN — transaction trace required.');
  if (evidence.network === 'FAILED') lines.push('Payment network reports the transaction FAILED.');
  if (evidence.merchant === 'NOT_CREDITED') lines.push('Merchant ledger shows no corresponding credit received.');
  if (evidence.merchant === 'CREDITED') lines.push('Merchant ledger confirms credit received.');
  if (evidence.settlement === 'NOT_FOUND') lines.push('No settlement record found in the settlement system.');
  if (evidence.settlement === 'UNKNOWN') lines.push('Settlement status is UNKNOWN — manual verification required.');
  if (evidence.settlement === 'SETTLED') lines.push('Settlement system confirms the transaction is settled.');
  if (evidence.settlement === 'REVERSED') lines.push('Settlement has been reversed.');
  lines.push(`Risk score: ${(evidence.risk * 100).toFixed(0)}% | Prior refund: ${evidence.previous_refund ? 'Yes' : 'No'}.`);
  return lines;
}

export default function EvidencePanel({ evidence }) {
  if (!evidence) return null;
  const lines = generateNarrative(evidence);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <FileText size={14} className="text-slate-400" />
        <h3 className="text-xs font-bold tracking-widest text-slate-400 uppercase">Evidence</h3>
      </div>
      <ul className="space-y-2">
        {lines.map((line, i) => (
          <li key={i} className="flex items-start gap-2 text-xs text-slate-600">
            <span className="w-1 h-1 rounded-full bg-slate-400 flex-shrink-0 mt-1.5" />
            {line}
          </li>
        ))}
      </ul>
    </div>
  );
}
