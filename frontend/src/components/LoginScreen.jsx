import React, { useState } from 'react';
import { ArrowRight, ShieldCheck, Zap, User, Users, Sparkles, Bot, CheckCircle2, Lock, Key } from 'lucide-react';
import { login } from '../api';

const STAKEHOLDERS = [
  {
    role_id: 'manager',
    email: 'manager@zerotouch.demo',
    name: 'Rajesh Mehra',
    title: 'VP of Operations (Admin)',
    avatar: '👔',
    badge: 'Executive Admin',
    badgeColor: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    workflow: 'Global Analytics Dashboard, All Agent Trace Logs, ROI Model (1.54 FTE), Emergency Kill Switch',
  },
  {
    role_id: 'support_agent',
    email: 'support@zerotouch.demo',
    name: 'Aarav Sharma',
    title: 'Senior Support Lead',
    avatar: '💳',
    badge: 'Payments & Support',
    badgeColor: 'bg-blue-100 text-blue-800 border-blue-300',
    workflow: 'Failed UPI debits (W1), Refund SLA breaches (W2), Bounced refunds (W2), Settlement shortfalls (W3)',
  },
  {
    role_id: 'finance_analyst',
    email: 'finance@zerotouch.demo',
    name: 'Neha Patel',
    title: 'Lead Reconciliation Analyst',
    avatar: '📊',
    badge: 'Finance Operations',
    badgeColor: 'bg-purple-100 text-purple-800 border-purple-300',
    workflow: 'Nodal statement feeds (HDFC/ICICI/SBI), MDR & GST variances, duplicate payout detection',
  },
  {
    role_id: 'skill_owner',
    email: 'it@zerotouch.demo',
    name: 'Vikram Malhotra',
    title: 'Staff Operations / IT Lead',
    avatar: '🛠️',
    badge: 'IT & Skill Authoring',
    badgeColor: 'bg-amber-100 text-amber-900 border-amber-300',
    workflow: 'IT tool provisioning (Okta/GitHub), Skill Studio (Teach AI new workflows by demonstration)',
  },
  {
    role_id: 'recruiter',
    email: 'hr@zerotouch.demo',
    name: 'Priya Nair',
    title: 'Technical Talent Partner',
    avatar: '🎯',
    badge: 'Talent & HR',
    badgeColor: 'bg-rose-100 text-rose-800 border-rose-300',
    workflow: 'Candidate evaluation, privacy filter (protected attributes stripped), panel interview dispatch',
  },
  {
    role_id: 'new_joiner',
    email: 'joiner@zerotouch.demo',
    name: 'Kavita Rao',
    title: 'Operations Trainee',
    avatar: '🎓',
    badge: 'Joiner Sandbox',
    badgeColor: 'bg-cyan-100 text-cyan-900 border-cyan-300',
    workflow: 'Onboarding case replay simulation, AI coach real-time grading & competency map',
  },
  {
    role_id: 'customer',
    email: 'ayush@zerotouch.demo',
    name: 'Ayush Bhardwaj',
    title: 'Paytm Customer',
    avatar: '📱',
    badge: 'Customer Portal',
    badgeColor: 'bg-sky-100 text-sky-800 border-sky-300',
    workflow: 'Customer self-service dispute chat, dynamic AI status notices & live TAT clock tracking',
  },
];

export default function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState('manager@zerotouch.demo');
  const [password, setPassword] = useState('demo123');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [activeTab, setActiveTab] = useState('1click'); // '1click' or 'form'

  async function handleQuickLogin(stakeholder) {
    setBusy(true);
    setError('');
    try {
      const res = await login(stakeholder.email, 'demo123');
      onLogin(res.user || res);
    } catch (err) {
      setError(err.message || 'Could not sign in as stakeholder.');
    } finally {
      setBusy(false);
    }
  }

  async function handleFormSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const res = await login(email, password);
      onLogin(res.user || res);
    } catch (err) {
      setError(err.message || 'Invalid credentials.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen grid lg:grid-cols-[1fr_1.15fr] bg-slate-50 text-slate-900 font-sans">
      {/* ── Left Hero Section ── */}
      <section className="relative overflow-hidden bg-[#07356b] px-6 py-8 text-white sm:px-10 lg:px-12 lg:py-12 flex flex-col justify-between">
        <div className="absolute -right-28 -top-20 h-96 w-96 rounded-full border border-white/10 pointer-events-none" />
        <div className="absolute -right-12 -top-4 h-64 w-64 rounded-full border border-white/10 pointer-events-none" />

        {/* Brand */}
        <div className="relative flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-cyan-400 text-[#07356b] flex items-center justify-center font-extrabold shadow-md">
            <Zap size={22} className="fill-[#07356b]" />
          </div>
          <div>
            <div className="text-xl font-extrabold tracking-tight">ZeroTouch Workforce</div>
            <div className="text-[11px] text-cyan-200 font-semibold tracking-wide">ENTERPRISE AUTONOMOUS OPERATIONS</div>
          </div>
        </div>

        {/* Hero Narrative */}
        <div className="relative max-w-xl py-8 lg:py-4">
          <span className="inline-block bg-cyan-400/20 text-cyan-300 border border-cyan-400/30 text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider mb-4">
            Multi-Agent AI Teammate
          </span>
          <h1 className="text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl text-white">
            Autonomous exception resolution with full stakeholder transparency.
          </h1>
          <p className="mt-4 text-xs sm:text-sm leading-relaxed text-blue-100/90">
            ZeroTouch orchestrates 5 segregated AI agents across Banking, NPCI, Credit Bureau, and Settlement ledgers. Every financial mutation is protected by SHA-256 idempotency, deterministic policy compliance, and independent verification.
          </p>

          {/* Pillars */}
          <div className="mt-6 grid grid-cols-2 gap-2 text-xs">
            <div className="p-3 rounded-2xl bg-white/10 border border-white/10">
              <div className="font-extrabold text-cyan-300">5 Segregated Agents</div>
              <div className="text-[11px] text-blue-100 mt-0.5">Investigator, Risk, Policy, Gateway, Communicator</div>
            </div>
            <div className="p-3 rounded-2xl bg-white/10 border border-white/10">
              <div className="font-extrabold text-emerald-300">1.54 FTE Capacity Freed</div>
              <div className="text-[11px] text-blue-100 mt-0.5">Measurable ROI formula live by Day 100</div>
            </div>
            <div className="p-3 rounded-2xl bg-white/10 border border-white/10">
              <div className="font-extrabold text-amber-300">Idempotent Action Gateway</div>
              <div className="text-[11px] text-blue-100 mt-0.5">Zero double-payouts, independent verification</div>
            </div>
            <div className="p-3 rounded-2xl bg-white/10 border border-white/10">
              <div className="font-extrabold text-purple-300">Continuous Skill Studio</div>
              <div className="text-[11px] text-blue-100 mt-0.5">Teach new workflows by 1 demonstration</div>
            </div>
          </div>
        </div>

        {/* Footer Note */}
        <div className="relative flex items-center gap-2 text-xs text-blue-200 border-t border-white/10 pt-4">
          <ShieldCheck size={16} className="text-emerald-400" />
          <span>Financial mutations strictly governed by deterministic policies and audit logging.</span>
        </div>
      </section>

      {/* ── Right Sign-In Section ── */}
      <section className="flex flex-col justify-center px-6 py-8 sm:px-10 overflow-y-auto">
        <div className="w-full max-w-xl mx-auto space-y-5">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-cyan-800 uppercase tracking-wider mb-1">
              <span>ZeroTouch Access Portal</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Select your workspace to sign in
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Choose any stakeholder role to test their tailored dashboard and automated workflow.
            </p>
          </div>

          {/* Toggle Tab */}
          <div className="flex items-center gap-1 p-1 bg-slate-200/70 rounded-2xl text-xs font-bold w-fit">
            <button
              onClick={() => setActiveTab('1click')}
              className={`px-3.5 py-1.5 rounded-xl transition ${
                activeTab === '1click' ? 'bg-white text-[#07356b] shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              ⚡ 1-Click Mock Logins
            </button>
            <button
              onClick={() => setActiveTab('form')}
              className={`px-3.5 py-1.5 rounded-xl transition ${
                activeTab === 'form' ? 'bg-white text-[#07356b] shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              🔑 Password Login
            </button>
          </div>

          {error && (
            <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200 text-xs font-bold text-rose-700">
              {error}
            </div>
          )}

          {/* 1-Click Mock Logins List */}
          {activeTab === '1click' ? (
            <div className="space-y-2.5 max-h-[62vh] overflow-y-auto pr-1">
              {STAKEHOLDERS.map(stakeholder => (
                <button
                  key={stakeholder.role_id}
                  disabled={busy}
                  onClick={() => handleQuickLogin(stakeholder)}
                  className="w-full text-left p-3.5 rounded-2xl border border-slate-200 bg-white hover:border-[#07356b] hover:bg-blue-50/40 hover:shadow-xs transition flex items-center justify-between gap-3 group disabled:opacity-50"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-slate-100 group-hover:bg-blue-100 flex items-center justify-center text-lg shrink-0 transition">
                      {stakeholder.avatar}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-extrabold text-xs text-slate-900 group-hover:text-[#07356b]">
                          {stakeholder.name}
                        </span>
                        <span className={`text-[10px] font-extrabold px-2 py-0.2 rounded-full border ${stakeholder.badgeColor}`}>
                          {stakeholder.badge}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 font-medium">
                        {stakeholder.title}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-1 line-clamp-1">
                        Workflow: {stakeholder.workflow}
                      </div>
                    </div>
                  </div>

                  <div className="w-8 h-8 rounded-xl bg-slate-100 group-hover:bg-[#07356b] group-hover:text-white flex items-center justify-center text-slate-400 shrink-0 transition">
                    <ArrowRight size={14} />
                  </div>
                </button>
              ))}
            </div>
          ) : (
            /* Custom Credentials Form */
            <form onSubmit={handleFormSubmit} className="space-y-4 bg-white p-5 rounded-3xl border border-slate-200 shadow-xs">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full text-xs p-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#07356b]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full text-xs p-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#07356b]"
                />
                <span className="text-[10px] text-slate-400 mt-1 block">Default demo password: demo123</span>
              </div>

              <button
                type="submit"
                disabled={busy}
                className="w-full py-3 rounded-xl bg-[#07356b] hover:bg-[#05284f] text-white text-xs font-extrabold transition shadow-xs disabled:opacity-50"
              >
                {busy ? 'Signing In...' : 'Sign In to Workspace'}
              </button>
            </form>
          )}

          <div className="p-3 rounded-2xl bg-slate-100/80 border border-slate-200 text-[11px] text-slate-600 flex items-center justify-between">
            <span>Need full admin control?</span>
            <button
              onClick={() => handleQuickLogin(STAKEHOLDERS[0])}
              className="font-bold text-[#07356b] hover:underline"
            >
              Sign In as VP of Operations (Admin) →
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
