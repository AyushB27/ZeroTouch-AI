import React from 'react';
import { X, Users, Smartphone, Store, ShieldCheck, Zap, ArrowRight, Bot } from 'lucide-react';

export default function UserRolesModal({ open, onClose }) {
  if (!open) return null;

  const roles = [
    {
      title: 'Customer',
      icon: Smartphone,
      color: 'text-paytm-primary',
      bg: 'bg-paytm-primary/10',
      border: 'border-paytm-primary/20',
      badge: 'Customer Portal',
      badgeColor: 'bg-slate-100 text-slate-700',
      desc: 'Customers can sign in to ZeroTouch, review their transactions, and open a support conversation.',
      howItWorks: [
        'Signs in to the customer portal and describes a payment issue in their own words.',
        'Follows transaction checks and policy decisions in the investigation activity panel.',
        'Can track cases and review recorded actions and outcomes.',
        'Gets a clear handoff to support whenever policy blocks autonomous action.'
      ]
    },
    {
      title: 'Paytm Merchant (Business)',
      icon: Store,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
      border: 'border-purple-200',
      badge: 'Integrated via Webhooks',
      badgeColor: 'bg-purple-100 text-purple-700',
      desc: 'Shops and businesses using Paytm Soundbox, QR codes, and Payment Gateway.',
      howItWorks: [
        'Monitors payouts in the Paytm for Business app/web portal.',
        'Does not interact with ZeroTouch directly.',
        'Receives automated itemized reconciliation breakdowns (e.g. S-302 fee deduction explanations) or compliance notices (S-306 KYC hold) directly into their business feed.',
        'Prevents unnecessary merchant disputes and support calls.'
      ]
    },
    {
      title: 'Paytm Support & Ops Agents',
      icon: Users,
      color: 'text-paytm-dark',
      bg: 'bg-paytm-dark/10',
      border: 'border-paytm-dark/20',
      badge: 'Primary Portal Users',
      badgeColor: 'bg-paytm-dark text-white',
      desc: 'Internal Paytm operations and customer escalation team.',
      howItWorks: [
        'Uses this ZeroTouch Ops Portal dashboard daily.',
        'Monitors autonomous resolution rates and inspects live LangGraph execution traces.',
        'Reviews edge-case exceptions routed to the Human-in-the-Loop (HITL) Queue.',
        'Applies human approvals, rejects, or requests additional info with full pre-assembled evidence.'
      ]
    },
    {
      title: 'ZeroTouch Autonomous Agent',
      icon: Bot,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      badge: 'Core Intelligence Engine',
      badgeColor: 'bg-emerald-100 text-emerald-800',
      desc: 'LangGraph multi-step state machine with RAG-grounded policies.',
      howItWorks: [
        'Ingests real-time events via NPCI webhooks and core banking APIs.',
        'Autonomously investigates 4 independent ledgers (Bank, Network, Merchant, Settlement).',
        'Evaluates deterministic policy rules augmented by Paytm Refund Policy RAG retrieval.',
        'Executes autonomous reversal or routes to HITL before SLA breaches occur.'
      ]
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-slate-200">
        
        {/* Header */}
        <div className="px-6 py-5 bg-paytm-dark text-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-paytm-primary flex items-center justify-center">
              <ShieldCheck size={20} className="text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold">System Architecture: Who Interacts With What?</h2>
              <p className="text-xs text-blue-200">Clarifying User Roles, Client Portals, and Autonomous Backend Flow</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 text-white/80 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Architecture flow pill */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-3 text-center md:text-left">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-paytm-dark text-white text-xs font-bold flex items-center justify-center">1</span>
              <span className="text-xs font-bold text-slate-800">Consumer / Merchant Event</span>
            </div>
            <ArrowRight size={14} className="text-slate-400 hidden md:block" />
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-paytm-primary text-white text-xs font-bold flex items-center justify-center">2</span>
              <span className="text-xs font-bold text-paytm-dark">ZeroTouch LangGraph Engine</span>
            </div>
            <ArrowRight size={14} className="text-slate-400 hidden md:block" />
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-emerald-600 text-white text-xs font-bold flex items-center justify-center">3</span>
              <span className="text-xs font-bold text-emerald-800">Auto-Reversal / HITL</span>
            </div>
            <ArrowRight size={14} className="text-slate-400 hidden md:block" />
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-purple-600 text-white text-xs font-bold flex items-center justify-center">4</span>
              <span className="text-xs font-bold text-purple-800">Live Client UI Update</span>
            </div>
          </div>

          {/* Role Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {roles.map((r) => {
              const Icon = r.icon;
              return (
                <div key={r.title} className={`p-5 rounded-xl border ${r.border} bg-white shadow-sm flex flex-col justify-between`}>
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2.5">
                        <div className={`w-8 h-8 rounded-lg ${r.bg} flex items-center justify-center`}>
                          <Icon size={18} className={r.color} />
                        </div>
                        <h3 className="font-bold text-sm text-slate-800">{r.title}</h3>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${r.badgeColor}`}>
                        {r.badge}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mb-3">{r.desc}</p>
                    <ul className="space-y-1.5">
                      {r.howItWorks.map((item, idx) => (
                        <li key={idx} className="text-[11px] text-slate-600 flex items-start gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1 shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })}
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-between items-center shrink-0">
          <span className="text-xs text-slate-500">
            Tip: Use the <span className="font-bold text-paytm-dark">"Client Experience"</span> view mode in the top bar to simulate what the customer sees.
          </span>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-lg bg-paytm-dark text-white font-bold text-xs hover:bg-slate-800 transition-colors"
          >
            Got It
          </button>
        </div>

      </div>
    </div>
  );
}
