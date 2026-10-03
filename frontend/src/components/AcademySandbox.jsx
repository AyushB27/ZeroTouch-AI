import React, { useState, useEffect } from 'react';
import {
  GraduationCap, CheckCircle2, AlertTriangle, ArrowRight,
  ShieldCheck, HelpCircle, BarChart3, Bot, Sparkles, RefreshCw
} from 'lucide-react';
import { getAcademyCase, submitAcademyCase } from '../api';

export default function AcademySandbox() {
  const [caseData, setCaseData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [evalResult, setEvalResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function loadCase() {
    try {
      const data = await getAcademyCase();
      setCaseData(data);
      setAnswers({});
      setEvalResult(null);
    } catch {
      // fallback
    }
  }

  useEffect(() => {
    loadCase();
  }, []);

  async function handleSubmit() {
    if (!caseData) return;
    const ansList = caseData.questions.map((_, i) => answers[i] ?? -1);
    setSubmitting(true);
    try {
      const res = await submitAcademyCase('Kavita Rao (New Joiner)', ansList);
      setEvalResult(res.run);
    } catch {
      // fallback
    } finally {
      setSubmitting(false);
    }
  }

  const allAnswered = caseData?.questions?.every((_, i) => answers[i] !== undefined);

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-8 bg-slate-50 text-slate-800 space-y-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="bg-blue-100 text-[#07356b] text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                New Joiner Academy Sandbox
              </span>
              <span className="text-xs text-slate-400 font-mono">Simulation Environment</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              Onboarding Sandbox & AI Coach
            </h1>
            <p className="text-xs text-slate-500 mt-1 max-w-xl">
              New joiners train by replaying real anonymized cases. The AI Coach grades your decisions per step, provides policy feedback, and updates your Competency Map before live work.
            </p>
          </div>

          <button
            onClick={loadCase}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-bold text-slate-700 shadow-2xs self-start"
          >
            <RefreshCw size={13} />
            <span>Reset Case</span>
          </button>
        </div>

        {caseData && (
          <div className="space-y-6">
            {/* Replayed Case Context Banner */}
            <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <span className="font-mono text-xs font-extrabold text-[#07356b] bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200">
                  {caseData.case_id}
                </span>
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
                  Anonymized Historical Case
                </span>
              </div>
              <h2 className="text-base font-extrabold text-slate-900">{caseData.title}</h2>
              <p className="text-xs text-slate-600 leading-relaxed">{caseData.context}</p>

              {/* Evidence Matrix */}
              <div className="mt-3 bg-slate-50 rounded-2xl p-3 border border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                {Object.entries(caseData.evidence).map(([k, v]) => (
                  <div key={k}>
                    <span className="text-[9px] font-bold text-slate-400 uppercase block">{k.replace(/_/g, ' ')}</span>
                    <span className="font-bold text-slate-800">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Questions Step List */}
            <div className="space-y-4">
              {caseData.questions.map((q, idx) => (
                <div key={idx} className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-extrabold text-[#07356b] uppercase tracking-wider">
                      {q.title}
                    </span>
                    <span className="text-[10px] font-bold text-slate-400 uppercase">
                      Tagged: {q.competency.replace(/_/g, ' ')}
                    </span>
                  </div>

                  <p className="text-xs font-bold text-slate-900 leading-relaxed">
                    {q.question}
                  </p>

                  <div className="space-y-2 pt-1">
                    {q.options.map((opt, optIdx) => {
                      const isSelected = answers[idx] === optIdx;
                      return (
                        <button
                          key={optIdx}
                          type="button"
                          onClick={() => setAnswers(prev => ({ ...prev, [idx]: optIdx }))}
                          className={`w-full text-left p-3 rounded-xl border text-xs transition flex items-center justify-between ${
                            isSelected
                              ? 'bg-blue-50/80 border-[#07356b] text-[#07356b] font-bold ring-2 ring-[#07356b]/10'
                              : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-700'
                          }`}
                        >
                          <span>{opt}</span>
                          {isSelected && <CheckCircle2 size={16} className="text-[#07356b] shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            {/* Submit Button */}
            {!evalResult && (
              <div className="flex justify-end">
                <button
                  type="button"
                  disabled={!allAnswered || submitting}
                  onClick={handleSubmit}
                  className="px-6 py-3 rounded-2xl bg-[#07356b] hover:bg-[#05284f] text-white text-xs font-extrabold transition shadow-sm disabled:opacity-40 flex items-center gap-2"
                >
                  <Sparkles size={15} />
                  <span>Submit Answers for AI Coach Evaluation</span>
                </button>
              </div>
            )}

            {/* AI Coach Feedback & Competency Map */}
            {evalResult && (
              <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-xs space-y-6 animate-fade-in">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-cyan-100 text-cyan-800 flex items-center justify-center font-bold">
                      <Bot size={16} />
                    </div>
                    <div>
                      <h3 className="text-sm font-extrabold text-slate-900">AI Coach Evaluation Report</h3>
                      <span className="text-[10px] text-slate-400">Evaluated against RBI master direction & policy playbooks</span>
                    </div>
                  </div>

                  <span className={`text-xs font-extrabold px-3 py-1 rounded-full ${
                    evalResult.passed ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                  }`}>
                    Score: {evalResult.score}% ({evalResult.passed ? 'PASSED' : 'RETRY'})
                  </span>
                </div>

                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-700 leading-relaxed font-medium">
                  {evalResult.coach_feedback}
                </div>

                {/* Competency Map */}
                <div className="space-y-3">
                  <span className="text-xs font-extrabold uppercase tracking-wider text-slate-500 block">
                    Updated Operator Competency Map
                  </span>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    {Object.entries(evalResult.competencies || {}).map(([comp, score]) => (
                      <div key={comp} className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1.5">
                        <div className="flex justify-between font-bold">
                          <span className="capitalize text-slate-700">{comp.replace(/_/g, ' ')}</span>
                          <span className="text-[#07356b]">{score}%</span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                          <div
                            className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                            style={{ width: `${score}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="text-center pt-2">
                  <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-800 bg-emerald-50 px-4 py-1.5 rounded-full border border-emerald-200">
                    <ShieldCheck size={14} /> Certified: Ready for Supervised Live Work
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
