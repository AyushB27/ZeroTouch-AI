import React, { useState, useEffect } from 'react';
import {
  TrendingUp, Users, ShieldAlert, ShieldCheck, CheckCircle2,
  Clock3, AlertTriangle, Sliders, ArrowUpRight, DollarSign,
  Activity, Layers, RefreshCw
} from 'lucide-react';
import { getWorkforceDashboard, toggleWorkforceKillSwitch } from '../api';

const money = val => (val ? `₹${Number(val).toLocaleString('en-IN')}` : '₹0');

export default function ManagerDashboard({ currentRole, killSwitchActive, onToggleKillSwitch }) {
  const [teamSize, setTeamSize] = useState(10);
  const [repetitivePct, setRepetitivePct] = useState(0.40);
  const [skillCoveragePct, setSkillCoveragePct] = useState(0.60);
  const [timeSavedPct, setTimeSavedPct] = useState(0.80);

  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  async function loadData() {
    try {
      const data = await getWorkforceDashboard(teamSize, repetitivePct, skillCoveragePct, timeSavedPct);
      setDashboardData(data);
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [teamSize, repetitivePct, skillCoveragePct, timeSavedPct, killSwitchActive]);

  const cap = dashboardData?.capacity_model;

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-8 bg-slate-50 text-slate-800 space-y-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="bg-emerald-100 text-emerald-800 text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                Executive Operations & Governance
              </span>
              <span className="text-xs text-slate-400 font-mono">Operations Model</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              Manager Governance & Capacity Dashboard
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Live capacity model, per-skill autonomy ladder, immutable audit log, and emergency kill switch.
            </p>
          </div>

          {/* Quick Refresh */}
          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-bold text-slate-700 shadow-2xs self-start"
          >
            <RefreshCw size={13} />
            <span>Refresh Metrics</span>
          </button>
        </div>

        {/* ── Section 1: Live Interactive Capacity Model (Page 5) ── */}
        <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-wider text-slate-500">
              <TrendingUp size={15} className="text-[#07356b]" />
              <span>Capacity Model (Official Formula from Page 5)</span>
            </div>
            <span className="text-[11px] font-semibold text-slate-500 italic">
              Adjust sliders below to simulate team scaling
            </span>
          </div>

          {/* 4 Hero KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-left">
            {/* Card 1 */}
            <div className="bg-blue-50/70 p-4 rounded-2xl border border-blue-200">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                Rule-Bound Repetitive Work
              </span>
              <div className="text-2xl font-extrabold text-[#07356b] mt-1">
                {cap?.repetitive_fte || 4.0} <span className="text-sm font-semibold">FTEs</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                {(repetitivePct * 100).toFixed(0)}% of {teamSize} employees
              </p>
            </div>

            {/* Card 2 */}
            <div className="bg-cyan-50/70 p-4 rounded-2xl border border-cyan-200">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                Gross Capacity Freed
              </span>
              <div className="text-2xl font-extrabold text-cyan-900 mt-1">
                {cap?.gross_freed_fte || 1.92} <span className="text-sm font-semibold">FTEs</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                {cap?.hours_saved_per_month || 246} hours saved / month
              </p>
            </div>

            {/* Card 3 */}
            <div className="bg-emerald-50 p-4 rounded-2xl border border-emerald-300">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 block">
                Net Capacity Freed (Day 100)
              </span>
              <div className="text-2xl font-extrabold text-emerald-700 mt-1">
                {cap?.net_freed_fte || 1.54} <span className="text-sm font-semibold">FTEs</span>
              </div>
              <p className="text-[11px] text-emerald-800 mt-1 font-semibold">
                = Equivalent of +1.5 extra colleagues
              </p>
            </div>

            {/* Card 4 */}
            <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                Annual Redeployed Value
              </span>
              <div className="text-2xl font-extrabold text-slate-800 mt-1">
                {money(cap?.annual_value_inr || 1309000)}
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Redeployed to complex growth & escalations
              </p>
            </div>
          </div>

          {/* Formula Display Banner */}
          <div className="p-3.5 bg-slate-900 text-slate-100 rounded-2xl font-mono text-xs flex flex-col sm:flex-row items-center justify-between gap-2 shadow-inner">
            <span className="text-cyan-300 font-bold">Official Formula:</span>
            <span className="text-slate-200 text-center">{cap?.formula_display}</span>
            <span className="text-emerald-400 font-bold">✓ Net: {cap?.net_freed_fte} FTE</span>
          </div>

          {/* Dynamic Sliders */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2 text-xs">
            <div>
              <div className="flex justify-between font-bold mb-1">
                <span className="text-slate-600">Team Size:</span>
                <span className="text-[#07356b]">{teamSize} Employees</span>
              </div>
              <input
                type="range"
                min="5"
                max="50"
                value={teamSize}
                onChange={e => setTeamSize(Number(e.target.value))}
                className="w-full accent-[#07356b]"
              />
            </div>

            <div>
              <div className="flex justify-between font-bold mb-1">
                <span className="text-slate-600">Repetitive Work Share:</span>
                <span className="text-[#07356b]">{(repetitivePct * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.80"
                step="0.05"
                value={repetitivePct}
                onChange={e => setRepetitivePct(Number(e.target.value))}
                className="w-full accent-[#07356b]"
              />
            </div>

            <div>
              <div className="flex justify-between font-bold mb-1">
                <span className="text-slate-600">Skills Covered (Day 100):</span>
                <span className="text-[#07356b]">{(skillCoveragePct * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.20"
                max="0.90"
                step="0.05"
                value={skillCoveragePct}
                onChange={e => setSkillCoveragePct(Number(e.target.value))}
                className="w-full accent-[#07356b]"
              />
            </div>

            <div>
              <div className="flex justify-between font-bold mb-1">
                <span className="text-slate-600">Handling Time Saved:</span>
                <span className="text-[#07356b]">{(timeSavedPct * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.40"
                max="0.95"
                step="0.05"
                value={timeSavedPct}
                onChange={e => setTimeSavedPct(Number(e.target.value))}
                className="w-full accent-[#07356b]"
              />
            </div>
          </div>
        </div>

        {/* ── Section 2: Autonomy Ladder Matrix ── */}
        <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-wider text-slate-500">
              <Layers size={15} className="text-[#07356b]" />
              <span>Autonomy Ladder (Per-Skill Trust Levels & Measured Accuracy)</span>
            </div>
            <span className="text-xs text-slate-400">
              L0: Suggest ➔ L1: Draft & Human Approve ➔ L2: Sample Review ➔ L3: Acts Alone
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-slate-200 text-[10px] font-extrabold uppercase tracking-wider text-slate-400 bg-slate-50/50">
                  <th className="py-2.5 px-3">Skill Spec</th>
                  <th className="py-2.5 px-3">Domain</th>
                  <th className="py-2.5 px-3">Trust Level</th>
                  <th className="py-2.5 px-3">Cases Processed</th>
                  <th className="py-2.5 px-3">Measured Accuracy</th>
                  <th className="py-2.5 px-3">Edits / Rejects</th>
                  <th className="py-2.5 px-3">Governor Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(dashboardData?.skills_autonomy_ladder || []).map((sk, i) => (
                  <tr key={i} className="hover:bg-slate-50/60 transition">
                    <td className="py-3 px-3 font-bold text-slate-800">
                      {sk.name}
                      <span className="block font-mono text-[10px] text-slate-400">{sk.skill_id}</span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="capitalize px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">
                        {sk.domain}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`font-mono font-extrabold px-2 py-0.5 rounded ${
                        sk.level === 'L2'
                          ? 'bg-purple-100 text-purple-900 border border-purple-200'
                          : sk.level === 'L1'
                          ? 'bg-blue-100 text-blue-900 border border-blue-200'
                          : 'bg-amber-100 text-amber-900 border border-amber-200'
                      }`}>
                        Level {sk.level}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-semibold text-slate-700">
                      {sk.cases_processed}
                    </td>
                    <td className="py-3 px-3 font-extrabold text-emerald-700">
                      {sk.accuracy_rate}%
                    </td>
                    <td className="py-3 px-3 text-slate-500">
                      {sk.edited_count} edits / {sk.rejected_count} rejects
                    </td>
                    <td className="py-3 px-3">
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700">
                        <CheckCircle2 size={12} /> {sk.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Section 3: Kill Switch & Immutable Audit Trail ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Emergency Kill Switch Card */}
          <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold uppercase tracking-wider text-slate-500">
                Governor Safety Control
              </span>
              <ShieldAlert size={16} className={killSwitchActive ? 'text-rose-600 animate-pulse' : 'text-slate-400'} />
            </div>

            <div className={`p-4 rounded-2xl border text-xs space-y-2 ${
              killSwitchActive
                ? 'bg-rose-50 text-rose-900 border-rose-300'
                : 'bg-emerald-50 text-emerald-900 border-emerald-300'
            }`}>
              <div className="font-extrabold text-sm flex items-center gap-1.5">
                {killSwitchActive ? '🚨 KILL SWITCH ENGAGED' : '🛡️ SYSTEM RUNNING NORMALLY'}
              </div>
              <p className="text-[11px] leading-relaxed">
                {killSwitchActive
                  ? 'All autonomous execution is strictly suspended. Every case forces 100% human sign-off.'
                  : 'Autonomous safety boundaries active. L2/L3 skills act within approved thresholds.'}
              </p>
            </div>

            <button
              onClick={onToggleKillSwitch}
              className={`w-full py-3 rounded-2xl font-extrabold text-xs transition shadow-xs flex items-center justify-center gap-2 ${
                killSwitchActive
                  ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                  : 'bg-rose-600 hover:bg-rose-700 text-white'
              }`}
            >
              <span>{killSwitchActive ? 'Disengage Kill Switch' : 'Trigger Emergency Kill Switch'}</span>
            </button>
          </div>

          {/* Immutable Audit Log */}
          <div className="lg:col-span-2 bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <span className="text-xs font-extrabold uppercase tracking-wider text-slate-500">
                Immutable Trust & Action Audit Log
              </span>
              <span className="text-[10px] text-slate-400 font-mono">Tied to Agent, Skill Version & Human</span>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {(dashboardData?.recent_audit_trail || []).map((ev, i) => (
                <div key={i} className="p-2.5 rounded-xl border border-slate-100 bg-slate-50/60 text-xs flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 truncate">
                    <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                      ev.event_type === 'APPROVE'
                        ? 'bg-emerald-100 text-emerald-800'
                        : ev.event_type === 'EDIT'
                        ? 'bg-blue-100 text-blue-800'
                        : ev.event_type === 'KILL_SWITCH'
                        ? 'bg-rose-100 text-rose-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}>
                      {ev.event_type}
                    </span>
                    <span className="font-bold text-slate-800 truncate">{ev.notes || ev.skill_id}</span>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="font-semibold text-slate-500 text-[10px] block">{ev.approver}</span>
                    <span className="text-[9px] text-slate-400 font-mono">{ev.timestamp?.slice(11, 19)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
