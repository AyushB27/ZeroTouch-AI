import React from 'react';
import { AlertTriangle, User, FileText, Check, X, ArrowRight } from 'lucide-react';

export default function SupportConsole({ result, isRunning }) {
  if (isRunning) {
    return (
      <div className="h-full bg-white rounded-xl border border-slate-200 flex flex-col items-center justify-center p-6 text-slate-400">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-paytm-primary rounded-full animate-spin mb-4"></div>
        <div className="text-sm font-medium">Processing...</div>
      </div>
    );
  }

  if (!result || result.resolution_status !== 'ESCALATED') {
    return (
      <div className="h-full bg-white rounded-xl border border-slate-200 flex flex-col items-center justify-center p-6 text-center text-slate-400">
        <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mb-3">
          <Check size={20} className="text-slate-300" />
        </div>
        <div className="text-sm font-medium text-slate-600">Zero Tickets in Queue</div>
        <div className="text-xs mt-1">Autonomous resolution successful or no action required.</div>
      </div>
    );
  }

  return (
    <div className="h-full bg-white rounded-xl border border-rose-200 shadow-sm flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-rose-50 border-b border-rose-100 p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-rose-600" />
          <span className="text-sm font-bold text-rose-900">Human Approval Required</span>
        </div>
        <span className="px-2 py-1 bg-white rounded text-xs font-mono font-bold text-rose-600 border border-rose-200">
          {result.support_case}
        </span>
      </div>

      <div className="p-4 flex-1 overflow-y-auto space-y-5">
        
        {/* Pre-investigated bundle */}
        <div>
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Agent Investigation Summary</div>
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm text-slate-700 leading-relaxed">
            {result.investigation_narrative}
          </div>
        </div>

        {/* Action Recommendation */}
        <div>
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Suggested Resolution</div>
          <div className="flex items-start gap-3 bg-blue-50 text-paytm-dark rounded-lg p-3 border border-blue-100">
            <User size={16} className="mt-0.5 text-paytm-primary" />
            <div className="text-sm font-medium">
              {result.suggested_resolution}
            </div>
          </div>
        </div>

        {/* Evidence Snapshot */}
        {result.evidence && (
          <div>
             <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Evidence Snapshot</div>
             <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-50 border border-slate-100 p-2 rounded">
                  <div className="text-slate-400 mb-1">Bank Status</div>
                  <div className="font-semibold text-slate-800">{result.evidence.bank}</div>
                </div>
                <div className="bg-slate-50 border border-slate-100 p-2 rounded">
                  <div className="text-slate-400 mb-1">Network Status</div>
                  <div className="font-semibold text-slate-800">{result.evidence.network}</div>
                </div>
                <div className="bg-slate-50 border border-slate-100 p-2 rounded">
                  <div className="text-slate-400 mb-1">Merchant Status</div>
                  <div className="font-semibold text-slate-800">{result.evidence.merchant}</div>
                </div>
                <div className="bg-slate-50 border border-slate-100 p-2 rounded">
                  <div className="text-slate-400 mb-1">Risk Score</div>
                  <div className="font-semibold text-rose-600">{(result.evidence.risk * 100).toFixed(0)}%</div>
                </div>
             </div>
          </div>
        )}

      </div>

      {/* Human Actions */}
      <div className="p-4 border-t border-slate-100 bg-slate-50 flex gap-2">
        <button className="flex-1 bg-paytm-dark hover:bg-paytm-dark/90 text-white text-sm font-bold py-2 rounded shadow-sm transition-colors flex items-center justify-center gap-1.5">
          <Check size={16} /> Approve
        </button>
        <button className="flex-1 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-sm font-bold py-2 rounded shadow-sm transition-colors flex items-center justify-center gap-1.5">
          <X size={16} /> Reject
        </button>
      </div>

    </div>
  );
}
