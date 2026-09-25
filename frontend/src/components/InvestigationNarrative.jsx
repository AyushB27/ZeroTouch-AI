import React from 'react';
import { Brain, Cpu } from 'lucide-react';

export default function InvestigationNarrative({ narrative, agentPowered }) {
  if (!narrative) return null;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-violet-500" />
          <h3 className="text-xs font-bold tracking-widest text-slate-400 uppercase">
            Layer 3 · Agent Investigation
          </h3>
        </div>
        <span
          className={`flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border ${
            agentPowered
              ? 'bg-violet-50 text-violet-700 border-violet-200'
              : 'bg-slate-50 text-slate-500 border-slate-200'
          }`}
        >
          <Cpu size={9} />
          {agentPowered ? 'GEMINI' : 'DETERMINISTIC FALLBACK'}
        </span>
      </div>
      <p className="text-sm text-slate-700 leading-relaxed border-l-2 border-violet-300 pl-3">
        {narrative}
      </p>
    </div>
  );
}
