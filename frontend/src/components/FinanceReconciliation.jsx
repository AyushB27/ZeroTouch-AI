import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet, CheckCircle2, Clock3, AlertTriangle,
  ArrowRight, ShieldCheck, RefreshCw, Layers, DollarSign
} from 'lucide-react';
import { getFinanceReconciliation } from '../api';

const money = val => (val ? `₹${Number(val).toLocaleString('en-IN')}` : '₹0');

export default function FinanceReconciliation() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  async function loadData() {
    try {
      const res = await getFinanceReconciliation();
      setData(res);
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-8 bg-slate-50 text-slate-800 space-y-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="bg-purple-100 text-purple-900 text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                Finance Operations · Ledger Reconciliation
              </span>
              <span className="text-xs text-slate-400 font-mono">Nodal & Banking Feeds</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              Bank Statement & General Ledger Reconciliation
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              The same domain-neutral engine processes bank statement feeds: auto-matching exact lines, explaining fee/tax variances, and flagging duplicate payouts.
            </p>
          </div>

          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-bold text-slate-700 shadow-2xs self-start"
          >
            <RefreshCw size={13} />
            <span>Ingest Feed</span>
          </button>
        </div>

        {/* 3 Summary Metric Pills */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Auto-Matched (L2)</span>
              <span className="text-2xl font-extrabold text-emerald-700">{data?.auto_matched_count || 1} Lines</span>
            </div>
            <span className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
              ✓
            </span>
          </div>

          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Variance Explained</span>
              <span className="text-2xl font-extrabold text-cyan-800">{data?.variance_explained_count || 1} Lines</span>
            </div>
            <span className="w-10 h-10 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center font-bold">
              📊
            </span>
          </div>

          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Human Action Flags</span>
              <span className="text-2xl font-extrabold text-amber-700">{data?.flagged_for_human_count || 2} Items</span>
            </div>
            <span className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
              ⚠️
            </span>
          </div>
        </div>

        {/* Statement Lines Table */}
        <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <span className="text-xs font-extrabold uppercase tracking-wider text-slate-500">
              Live Bank Statement Feed & Matching Engine
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Connector: HDFC / ICICI / SBI Nodal Gateways
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-slate-200 text-[10px] font-extrabold uppercase tracking-wider text-slate-400 bg-slate-50/50">
                  <th className="py-2.5 px-3">Line ID & Date</th>
                  <th className="py-2.5 px-3">Description</th>
                  <th className="py-2.5 px-3">Bank Amount</th>
                  <th className="py-2.5 px-3">Ledger Amount</th>
                  <th className="py-2.5 px-3">Match Type</th>
                  <th className="py-2.5 px-3">Decision & Action Taken</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(data?.statement_lines || []).map((line, i) => {
                  const isAuto = line.status === 'MATCHED';
                  const isNote = line.status === 'MATCHED_WITH_VARIANCE_NOTE';
                  const isFlag = line.status.includes('FLAGGED') || line.status.includes('DRAFT');

                  return (
                    <tr key={i} className="hover:bg-slate-50/50 transition">
                      <td className="py-3.5 px-3">
                        <span className="font-mono font-bold text-slate-800 block">{line.line_id}</span>
                        <span className="text-[10px] text-slate-400">{line.value_date}</span>
                      </td>
                      <td className="py-3.5 px-3 font-semibold text-slate-700 max-w-xs">
                        {line.description}
                        <span className="block font-mono text-[10px] text-slate-400">{line.bank_ref}</span>
                      </td>
                      <td className="py-3.5 px-3 font-bold text-slate-800">
                        {money(line.bank_amount)}
                      </td>
                      <td className="py-3.5 px-3 font-semibold text-slate-600">
                        {line.ledger_amount > 0 ? money(line.ledger_amount) : 'Unmatched'}
                      </td>
                      <td className="py-3.5 px-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
                          isAuto
                            ? 'bg-emerald-100 text-emerald-800'
                            : isNote
                            ? 'bg-cyan-100 text-cyan-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}>
                          {line.match_type.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-3.5 px-3">
                        <div className="font-bold text-slate-800 text-[11px]">{line.rule_applied}</div>
                        <span className="text-[10px] text-slate-400 block font-mono mt-0.5">
                          Status: {line.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
