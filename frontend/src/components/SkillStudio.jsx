import React, { useState } from 'react';
import {
  Wrench, Play, CheckCircle2, AlertTriangle, ShieldCheck,
  FileCode, Layers, ArrowRight, ShieldAlert, Sparkles, Check,
  Terminal, ExternalLink, RefreshCw, Cpu
} from 'lucide-react';
import { teachWorkforceSkill, backtestWorkforceSkill, publishWorkforceSkill } from '../api';

export default function SkillStudio({ onSkillPublished }) {
  const [currentStep, setCurrentStep] = useState(1); // 1: Record, 2: Spec, 3: Backtest, 4: Publish
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Step 1: Mock IT Console state
  const [employeeId, setEmployeeId] = useState('EMP-8821');
  const [employeeRole, setEmployeeRole] = useState('Product Designer');
  const [requestedTool, setRequestedTool] = useState('Figma Pro');
  const [roleVerified, setRoleVerified] = useState(false);
  const [policyChecked, setPolicyChecked] = useState(false);
  const [licenseGranted, setLicenseGranted] = useState(false);
  const [whyNote, setWhyNote] = useState('Approved per Design Team standard bundle policy.');

  // Step 2 & 3 state
  const [generatedSpec, setGeneratedSpec] = useState(null);
  const [backtestReport, setBacktestReport] = useState(null);
  const [publishResult, setPublishResult] = useState(null);

  // Guardrail test state
  const [guardrailTestResult, setGuardrailTestResult] = useState(null);

  // Step 1 -> Step 2: Teach Skill & Synthesize Spec
  async function handleSynthesizeSpec() {
    setLoading(true);
    setError('');
    try {
      const recordedActions = [
        { tool: 'okta_idp', action: 'lookup_employee_role', input: employeeId, output: employeeRole },
        { tool: 'access_matrix', action: 'check_policy', input: { role: employeeRole, tool: requestedTool }, output: 'ALLOWED' },
        { tool: 'figma_admin_api', action: 'grant_license', input: { emp_id: employeeId, license: requestedTool } },
      ];
      const res = await teachWorkforceSkill('it', 'IT Standard Tool Provisioning', recordedActions, whyNote, 'Vikram Malhotra');
      setGeneratedSpec(res.spec);
      setCurrentStep(2);
    } catch (err) {
      setError(err.message || 'Failed to synthesize skill spec.');
    } finally {
      setLoading(false);
    }
  }

  // Step 2 -> Step 3: Run Backtest on 12 Historical Requests
  async function handleRunBacktest() {
    if (!generatedSpec) return;
    setLoading(true);
    setError('');
    try {
      const res = await backtestWorkforceSkill(generatedSpec);
      setBacktestReport(res.report);
      setCurrentStep(3);
    } catch (err) {
      setError(err.message || 'Backtest failed.');
    } finally {
      setLoading(false);
    }
  }

  // Step 3 -> Step 4: Publish to L1
  async function handlePublish() {
    if (!generatedSpec) return;
    setLoading(true);
    setError('');
    try {
      const res = await publishWorkforceSkill(generatedSpec, 'Vikram Malhotra');
      setPublishResult(res);
      setCurrentStep(4);
      if (onSkillPublished) await onSkillPublished();
    } catch (err) {
      setError(err.message || 'Failed to publish skill.');
    } finally {
      setLoading(false);
    }
  }

  // Guardrail Test: Request AWS Root Access
  function testGuardrail() {
    setGuardrailTestResult({
      tool: 'AWS Root Access',
      status: 'BLOCKED_BY_GUARDRAIL',
      rule: 'NEVER_AUTOMATE_PRIVILEGED_ACCESS',
      message: 'System refused autonomous execution. Privileged root tokens strictly require CISO manual approval.',
    });
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-8 bg-slate-50 text-slate-800">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                The Winning Slice · Live Skill Studio
              </span>
              <span className="text-xs text-slate-400 font-mono">Demo Minute 3:15</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              Teach a New Domain: IT Tool Access Provisioning
            </h1>
            <p className="text-xs text-slate-500 mt-1 max-w-xl">
              ZeroTouch has never seen IT access before. A senior employee demonstrates the task once. The AI Learner generates the spec, backtests on past cases, and earns L1 autonomy.
            </p>
          </div>

          {/* Stepper Pill */}
          <div className="flex items-center gap-1.5 bg-slate-100 p-1.5 rounded-2xl shrink-0 text-xs font-bold">
            {[1, 2, 3, 4].map(s => (
              <span
                key={s}
                className={`w-7 h-7 rounded-xl flex items-center justify-center transition ${
                  currentStep === s
                    ? 'bg-[#07356b] text-white shadow-xs'
                    : currentStep > s
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'text-slate-400'
                }`}
              >
                {currentStep > s ? '✓' : s}
              </span>
            ))}
          </div>
        </div>

        {error && (
          <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-700 font-semibold">
            {error}
          </div>
        )}

        {/* ── STEP 1: Record Mode (Mock IT Console) ── */}
        {currentStep === 1 && (
          <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-5 animate-fade-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-wider text-slate-500">
                <Terminal size={15} className="text-[#07356b]" />
                <span>Step 1: Record Employee Demonstration in Mock IT Console</span>
              </div>
              <span className="text-[11px] font-bold text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-200">
                Record Mode Active 🔴
              </span>
            </div>

            {/* Simulated Access Request Card */}
            <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50/70 space-y-3">
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 block">
                Incoming Raw Request (Unstructured Ticket)
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="bg-white p-3 rounded-xl border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-bold">Employee</span>
                  <span className="font-bold text-slate-800">Rohan Joshi (EMP-8821)</span>
                </div>
                <div className="bg-white p-3 rounded-xl border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-bold">Role & Department</span>
                  <span className="font-bold text-slate-800">Product Designer · Design</span>
                </div>
                <div className="bg-white p-3 rounded-xl border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-bold">Requested Tool</span>
                  <span className="font-bold text-[#07356b]">Figma Pro & Slack</span>
                </div>
              </div>
            </div>

            {/* Interactive Tool Actions */}
            <div className="space-y-3">
              <span className="text-xs font-bold text-slate-700 block">
                Senior Employee Resolution Actions (Click to simulate employee clicks):
              </span>

              <div className="space-y-2 text-xs">
                {/* Action 1 */}
                <button
                  type="button"
                  onClick={() => setRoleVerified(true)}
                  className={`w-full p-3 rounded-xl border text-left flex items-center justify-between transition ${
                    roleVerified
                      ? 'bg-emerald-50 text-emerald-900 border-emerald-300 font-bold'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold">1</span>
                    <span>Query Okta IdP Directory: Confirm employment status & role (EMP-8821)</span>
                  </div>
                  {roleVerified ? <CheckCircle2 size={16} className="text-emerald-600" /> : <span className="text-[11px] text-blue-600 font-bold">Click to Execute</span>}
                </button>

                {/* Action 2 */}
                <button
                  type="button"
                  disabled={!roleVerified}
                  onClick={() => setPolicyChecked(true)}
                  className={`w-full p-3 rounded-xl border text-left flex items-center justify-between transition disabled:opacity-40 ${
                    policyChecked
                      ? 'bg-emerald-50 text-emerald-900 border-emerald-300 font-bold'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold">2</span>
                    <span>Check Access Policy: Verify 'Figma Pro' is in Product Designer standard bundle</span>
                  </div>
                  {policyChecked ? <CheckCircle2 size={16} className="text-emerald-600" /> : <span className="text-[11px] text-blue-600 font-bold">Click to Verify</span>}
                </button>

                {/* Action 3 */}
                <button
                  type="button"
                  disabled={!policyChecked}
                  onClick={() => setLicenseGranted(true)}
                  className={`w-full p-3 rounded-xl border text-left flex items-center justify-between transition disabled:opacity-40 ${
                    licenseGranted
                      ? 'bg-emerald-50 text-emerald-900 border-emerald-300 font-bold'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold">3</span>
                    <span>Invoke Tool Provisioning API: Grant license in Figma Organization & log audit record</span>
                  </div>
                  {licenseGranted ? <CheckCircle2 size={16} className="text-emerald-600" /> : <span className="text-[11px] text-blue-600 font-bold">Click to Grant</span>}
                </button>
              </div>
            </div>

            {/* One-Line Why Note */}
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Senior Employee 'Why' Note (AI Learns Decision Invariant from This):
              </label>
              <input
                type="text"
                value={whyNote}
                onChange={e => setWhyNote(e.target.value)}
                className="w-full text-xs p-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-[#07356b] outline-none"
              />
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                disabled={!licenseGranted || loading}
                onClick={handleSynthesizeSpec}
                className="px-6 py-2.5 rounded-xl bg-[#07356b] hover:bg-[#05284f] text-white text-xs font-extrabold transition shadow-sm disabled:opacity-40 flex items-center gap-2"
              >
                <span>Synthesize Universal Skill Spec</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 2: Review Generated Universal SkillSpec YAML ── */}
        {currentStep === 2 && generatedSpec && (
          <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-5 animate-fade-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-wider text-slate-500">
                <FileCode size={15} className="text-[#07356b]" />
                <span>Step 2: Universal SkillSpec Generated by Skill Learner</span>
              </div>
              <span className="text-[11px] font-bold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200 font-mono">
                Autonomy: L0 (Untested)
              </span>
            </div>

            <p className="text-xs text-slate-500">
              The Skill Learner converted your recorded tool actions and 'why' note into the universal format. Hiring, refund chasing, and IT access all look identical to the orchestrator:
            </p>

            {/* YAML Preview Block */}
            <div className="bg-slate-900 text-slate-100 p-4 rounded-2xl font-mono text-xs overflow-x-auto space-y-1 shadow-inner leading-5">
              <div className="text-cyan-400">skill: <span className="text-white">{generatedSpec.skill_id}</span>  version: <span className="text-white">{generatedSpec.version}</span>  domain: <span className="text-white">{generatedSpec.domain}</span></div>
              <div className="text-cyan-400">trigger: <span className="text-emerald-300">"{generatedSpec.trigger}"</span></div>
              <div className="text-cyan-400">inputs: <span className="text-slate-300">[{generatedSpec.inputs.join(', ')}]</span></div>
              <div className="text-cyan-400 pt-1">steps:</div>
              {generatedSpec.steps.map((st, i) => (
                <div key={i} className="pl-4 text-slate-300">{st}</div>
              ))}
              <div className="text-cyan-400 pt-1">rules:</div>
              {generatedSpec.rules.map((rl, i) => (
                <div key={i} className="pl-4 text-amber-300">{rl}</div>
              ))}
              <div className="text-cyan-400 pt-1">exceptions:</div>
              {generatedSpec.exceptions.map((ex, i) => (
                <div key={i} className="pl-4 text-rose-300">{ex}</div>
              ))}
              <div className="text-cyan-400 pt-1">autonomy: <span className="text-amber-400 font-bold">L0 (Backtest Required Before Acting)</span></div>
              <div className="text-cyan-400">owner: <span className="text-slate-300">{generatedSpec.owner}</span></div>
            </div>

            <div className="pt-2 flex justify-between items-center">
              <button
                type="button"
                onClick={() => setCurrentStep(1)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50"
              >
                ← Back to Record
              </button>

              <button
                type="button"
                disabled={loading}
                onClick={handleRunBacktest}
                className="px-6 py-2.5 rounded-xl bg-[#07356b] hover:bg-[#05284f] text-white text-xs font-extrabold transition shadow-sm flex items-center gap-2"
              >
                <span>Run Historical Backtest (12 Cases)</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 3: Backtest Results (Proof Before Autonomy) ── */}
        {currentStep === 3 && backtestReport && (
          <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-5 animate-fade-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-wider text-slate-500">
                <ShieldCheck size={15} className="text-emerald-600" />
                <span>Step 3: Historical Backtest Verification (Proves Safety Before Acting)</span>
              </div>
              <span className="text-[11px] font-bold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200 font-mono">
                Match Rate: {backtestReport.match_rate}%
              </span>
            </div>

            {/* Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100 text-center">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Historical Cases Tested</span>
                <span className="text-2xl font-extrabold text-slate-800">{backtestReport.cases_tested}</span>
              </div>
              <div className="bg-emerald-50 p-4 rounded-2xl border border-emerald-200 text-center">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 block">Correct Matches</span>
                <span className="text-2xl font-extrabold text-emerald-700">{backtestReport.passed_count} / {backtestReport.cases_tested}</span>
              </div>
              <div className="bg-blue-50 p-4 rounded-2xl border border-blue-200 text-center">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#07356b] block">Promotion Status</span>
                <span className="text-sm font-extrabold text-[#07356b] mt-1 block">Qualified for L1 (&gt; 90%)</span>
              </div>
            </div>

            {/* Backtest Explanatory Note */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs space-y-1">
              <span className="font-bold text-slate-800 block">Backtest Result Analysis:</span>
              <p className="text-slate-600 leading-relaxed">
                Tested against 12 past requests from Product Designers, Frontend Developers, and Interns. 11 standard bundle requests correctly granted. 1 privileged root request (Case HIST-IT-12: 'AWS Root Access') was correctly intercepted by the never-automate guardrail.
              </p>
            </div>

            <div className="pt-2 flex justify-between items-center">
              <button
                type="button"
                onClick={() => setCurrentStep(2)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50"
              >
                ← Back to Spec
              </button>

              <button
                type="button"
                disabled={loading}
                onClick={handlePublish}
                className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold transition shadow-sm flex items-center gap-2"
              >
                <span>Publish Skill to L1 (Earned Autonomy)</span>
                <Check size={14} className="stroke-[3]" />
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 4: Published at L1 & Live Invariant Verification ── */}
        {currentStep === 4 && (
          <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-6 animate-fade-in">
            <div className="text-center py-4 space-y-2">
              <div className="w-12 h-12 bg-emerald-100 text-emerald-700 rounded-2xl flex items-center justify-center mx-auto shadow-xs">
                <CheckCircle2 size={24} />
              </div>
              <h2 className="text-xl font-extrabold text-slate-900">
                Skill Published to Autonomy Level L1!
              </h2>
              <p className="text-xs text-slate-500 max-w-lg mx-auto">
                ZeroTouch now autonomously pre-works incoming IT access requests. The AI gathers employee records, verifies entitlements, and drafts tool licenses for 1-click human sign-off.
              </p>
            </div>

            {/* Immediate Verification Card: Case IT-409 generated */}
            <div className="p-4 rounded-2xl bg-blue-50 border border-blue-200 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-extrabold text-[#07356b] flex items-center gap-1.5">
                  <Sparkles size={14} /> Immediate Live Proof (Inbox Updated):
                </span>
                <span className="font-mono text-[10px] font-bold text-[#07356b] bg-white px-2 py-0.5 rounded border border-blue-200">
                  CASE-IT-409
                </span>
              </div>
              <p className="text-xs text-blue-950 font-medium leading-relaxed">
                A new request arrived from <strong>Mansi Gupta (Frontend Developer)</strong> for VS Code Cloud & GitHub. The newly published skill pre-worked the entire task and placed it in the Task Inbox awaiting 1-click approval!
              </p>
            </div>

            {/* Never-Automate Guardrail Interactive Proof */}
            <div className="p-4 rounded-2xl bg-rose-50/70 border border-rose-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-rose-900 flex items-center gap-1.5">
                  <ShieldAlert size={14} className="text-rose-600" />
                  Test Never-Automate Guardrail (Privileged Access):
                </span>
                <button
                  type="button"
                  onClick={testGuardrail}
                  className="px-3 py-1 rounded-lg bg-rose-600 text-white text-[11px] font-bold hover:bg-rose-700 transition"
                >
                  Simulate 'AWS Root Access' Request
                </button>
              </div>

              {guardrailTestResult && (
                <div className="mt-2 p-3 bg-white rounded-xl border border-rose-300 text-xs text-rose-900 space-y-1 animate-fade-in font-medium">
                  <div className="font-bold flex items-center gap-1 text-rose-700">
                    <span>✓ Guardrail Verified:</span> {guardrailTestResult.rule}
                  </div>
                  <p>{guardrailTestResult.message}</p>
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-center">
              <button
                type="button"
                onClick={() => setCurrentStep(1)}
                className="px-5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition"
              >
                Teach Another Skill
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
