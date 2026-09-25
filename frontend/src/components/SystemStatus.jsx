import React from 'react';
import { Building2, Radio, Store, Banknote } from 'lucide-react';

const STATUS_COLORS = {
  DEBITED: 'bg-slate-100 text-slate-800 border-slate-300',
  SUCCESS: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  CREDITED: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  SETTLED: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  NOT_CREDITED: 'bg-red-100 text-red-800 border-red-300',
  NOT_FOUND: 'bg-red-100 text-red-800 border-red-300',
  UNKNOWN: 'bg-amber-100 text-amber-800 border-amber-300',
  FAILED: 'bg-red-100 text-red-800 border-red-300',
  REVERSED: 'bg-teal-100 text-teal-800 border-teal-300',
};

const STATUS_LABELS = {
  NOT_CREDITED: 'NOT CREDITED',
  NOT_FOUND: 'NOT FOUND',
};

function StatusBadge({ value }) {
  const colorClass = STATUS_COLORS[value] || 'bg-slate-100 text-slate-700 border-slate-300';
  const label = STATUS_LABELS[value] || value;
  return (
    <span className={`px-2 py-1 text-xs font-bold tracking-wider rounded border ${colorClass}`}>
      {label}
    </span>
  );
}

const CARDS = [
  { key: 'bank_status', label: 'BANK', icon: Building2 },
  { key: 'network_status', label: 'NETWORK', icon: Radio },
  { key: 'merchant_status', label: 'MERCHANT', icon: Store },
  { key: 'settlement_status', label: 'SETTLEMENT', icon: Banknote },
];

export default function SystemStatus({ transaction }) {
  if (!transaction) return null;
  return (
    <div className="grid grid-cols-4 gap-3">
      {CARDS.map(({ key, label, icon: Icon }) => (
        <div key={key} className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Icon size={14} className="text-slate-400" />
            <div className="text-[10px] font-bold tracking-widest text-slate-400">{label}</div>
          </div>
          <StatusBadge value={transaction[key]} />
        </div>
      ))}
    </div>
  );
}
