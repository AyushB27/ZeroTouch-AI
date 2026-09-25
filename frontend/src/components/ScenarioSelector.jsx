import React from 'react';
import { AlertTriangle, HelpCircle, CheckCircle2 } from 'lucide-react';

const SCENARIOS = [
  {
    id: 'TX9281',
    label: 'TX9281',
    sublabel: 'Auto Resolution',
    desc: '₹2,500 · Low Risk',
    icon: AlertTriangle,
    iconColor: 'text-amber-500',
    badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
    outcome: 'AUTO REVERSAL',
  },
  {
    id: 'TX9342',
    label: 'TX9342',
    sublabel: 'Human Escalation',
    desc: '₹18,000 · High Risk',
    icon: HelpCircle,
    iconColor: 'text-rose-500',
    badgeColor: 'bg-rose-50 text-rose-700 border-rose-200',
    outcome: 'ESCALATED',
  },
  {
    id: 'TX9410',
    label: 'TX9410',
    sublabel: 'No Action',
    desc: '₹850 · Consistent',
    icon: CheckCircle2,
    iconColor: 'text-emerald-500',
    badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    outcome: 'NO ACTION',
  },
];

export default function ScenarioSelector({ selected, onSelect }) {
  return (
    <div className="flex gap-3">
      {SCENARIOS.map((s) => {
        const Icon = s.icon;
        const isSelected = selected === s.id;
        return (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`flex-1 p-4 rounded-xl border-2 text-left transition-all ${
              isSelected
                ? 'border-blue-600 bg-blue-50 shadow-sm'
                : 'border-slate-200 bg-white hover:border-blue-300 hover:shadow-sm'
            }`}
          >
            <div className="flex items-start gap-3">
              <Icon size={18} className={`mt-0.5 ${s.iconColor}`} />
              <div>
                <div className="font-semibold text-slate-800 text-sm">{s.label}</div>
                <div className="text-xs text-slate-500 mt-0.5">{s.sublabel}</div>
                <div className="text-xs text-slate-400 mt-1">{s.desc}</div>
                <span className={`inline-block mt-2 text-[10px] font-semibold px-2 py-0.5 rounded border ${s.badgeColor}`}>
                  {s.outcome}
                </span>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
