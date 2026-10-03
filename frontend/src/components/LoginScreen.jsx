import React, { useState } from 'react';
import { ArrowRight, ShieldCheck, Zap, User, Users, Sparkles } from 'lucide-react';
import { login } from '../api';

export default function LoginScreen({ onLogin }) {
  const [account, setAccount] = useState('customer');
  const [email, setEmail] = useState('ayush@zerotouch.demo');
  const [password, setPassword] = useState('demo123');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    if (event) event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const user = await login(email, password);
      onLogin(user);
    } catch (err) {
      setError(err.message || 'Could not sign in.');
    } finally {
      setBusy(false);
    }
  }

  function select(next) {
    setAccount(next);
    setEmail(next === 'customer' ? 'ayush@zerotouch.demo' : next === 'employee' ? 'employee@zerotouch.demo' : 'admin@zerotouch.demo');
    setError('');
  }

  async function quickLogin(targetEmail, targetRole) {
    setBusy(true);
    setError('');
    setEmail(targetEmail);
    setAccount(targetRole.toLowerCase());
    try {
      const user = await login(targetEmail, 'demo123');
      onLogin(user);
    } catch (err) {
      setError(err.message || 'Could not sign in.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen grid lg:grid-cols-[1.05fr_.95fr] bg-white text-slate-900">
      <section className="relative overflow-hidden bg-[#072b56] px-7 py-9 text-white sm:px-12 lg:px-16 lg:py-14 flex flex-col justify-between min-h-[390px]">
        <div className="absolute -right-28 -top-20 h-96 w-96 rounded-full border border-white/10" />
        <div className="absolute -right-12 -top-4 h-64 w-64 rounded-full border border-white/10" />
        <div className="relative flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-400 text-[#072b56]">
            <Zap size={20} fill="currentColor" />
          </div>
          <div>
            <div className="text-lg font-extrabold tracking-tight">ZeroTouch</div>
            <div className="text-[11px] text-blue-200">AUTONOMOUS PAYMENT SUPPORT</div>
          </div>
        </div>
        <div className="relative max-w-xl py-12 lg:py-0">
          <p className="mb-4 text-xs font-bold uppercase tracking-[.22em] text-cyan-300">
            Your autonomous payment teammate
          </p>
          <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
            From issue to resolution — without the ticket.
          </h1>
          <p className="mt-5 max-w-lg text-sm leading-6 text-blue-100">
            ZeroTouch checks the payment trail across 4 independent ledgers, evaluates policy, executes simulated reversal or wallet credit, and verifies the outcome. A person steps in when human judgment is needed.
          </p>
          <div className="mt-8 flex flex-wrap gap-2 text-xs font-medium text-blue-50">
            {['Multi-Agent Segregation', 'CIBIL Profiling', 'Dynamic Communication', 'HITL Review Queue'].map(label => (
              <span key={label} className="rounded-full border border-white/15 bg-white/5 px-3 py-1.5">
                {label}
              </span>
            ))}
          </div>
        </div>
        <div className="relative flex items-center gap-2 text-xs text-blue-200">
          <ShieldCheck size={15} className="text-emerald-300" />
          Financial actions are strictly governed by deterministic policy rules.
        </div>
      </section>

      <section className="flex items-center justify-center px-6 py-12 sm:px-10">
        <div className="w-full max-w-md">
          <p className="text-sm font-semibold text-cyan-700">Welcome to ZeroTouch</p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight">Sign in to continue</h2>
          <p className="mt-2 text-sm text-slate-500">Choose a demo workspace or use one-click quick login.</p>

          {/* Quick 1-Click Login Chips */}
          <div className="mt-6 space-y-2">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">1-Click Quick Demo Sign In</div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              <button
                type="button"
                disabled={busy}
                onClick={() => quickLogin('ayush@zerotouch.demo', 'CUSTOMER')}
                className="flex items-center justify-center gap-2 p-3 bg-blue-50 hover:bg-blue-100 text-[#07356b] border border-blue-200 rounded-xl text-xs font-bold transition disabled:opacity-50"
              >
                <User size={14} className="text-blue-600" />
                Customer (Ayush)
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => quickLogin('support@zerotouch.demo', 'ADMIN')}
                className="flex items-center justify-center gap-2 p-3 bg-purple-50 hover:bg-purple-100 text-purple-900 border border-purple-200 rounded-xl text-xs font-bold transition disabled:opacity-50"
              >
                <Users size={14} className="text-purple-600" />
                Support Ops Portal
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => quickLogin('employee@zerotouch.demo', 'EMPLOYEE')}
                className="flex items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-bold text-emerald-900 transition hover:bg-emerald-100 disabled:opacity-50"
              >
                <Users size={14} className="text-emerald-700" />
                Employee Workspace
              </button>
            </div>
          </div>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200" /></div>
            <div className="relative flex justify-center text-xs uppercase"><span className="bg-white px-2 text-slate-400 font-semibold">Or Sign In with Form</span></div>
          </div>

          <div className="grid grid-cols-3 rounded-xl bg-slate-100 p-1">
            {[['customer', 'Customer'], ['employee', 'Employee'], ['admin', 'Admin']].map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => select(key)}
                className={`rounded-lg px-3 py-2.5 text-xs font-bold transition ${
                  account === key ? 'bg-white text-[#07356b] shadow-sm' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="mt-5 space-y-4">
            <label className="block text-xs font-bold text-slate-700">
              Email
              <input
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="mt-1.5 block w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none transition focus:border-cyan-500 focus:ring-4 focus:ring-cyan-500/10"
              />
            </label>
            <label className="block text-xs font-bold text-slate-700">
              Password
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="mt-1.5 block w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none transition focus:border-cyan-500 focus:ring-4 focus:ring-cyan-500/10"
              />
            </label>
            {error && (
              <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">
                {error}
              </p>
            )}
            <button
              disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#07356b] px-4 py-3 text-sm font-bold text-white transition hover:bg-[#05284f] disabled:opacity-60 shadow-sm"
            >
              {busy ? 'Signing in…' : 'Continue'} {!busy && <ArrowRight size={16} />}
            </button>
          </form>

          <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
            <div className="font-bold text-slate-800 text-[11px] uppercase tracking-wider">Demo Credentials</div>
            <div className="mt-1 text-[11px]">
              Customer: <code className="font-mono font-semibold text-blue-700">ayush@zerotouch.demo</code> (or <code className="font-mono font-semibold text-blue-700">vansh@zerotouch.demo</code>)
            </div>
            <div className="text-[11px]">
              Support: <code className="font-mono font-semibold text-purple-700">support@zerotouch.demo</code>
            </div>
            <div className="text-[11px]">
              Employee: <code className="font-mono font-semibold text-emerald-700">employee@zerotouch.demo</code> · Admin: <code className="font-mono font-semibold text-purple-700">admin@zerotouch.demo</code>
            </div>
            <div className="text-[10px] text-slate-400 mt-1">Demo password: <code className="font-mono">demo123</code></div>
          </div>
        </div>
      </section>
    </main>
  );
}
