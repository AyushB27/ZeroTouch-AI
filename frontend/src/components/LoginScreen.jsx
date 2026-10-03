import React, { useState } from 'react';
import { ArrowRight, Check, CircleHelp, Command, ShieldCheck, Sparkles, UserRound, UsersRound, Zap } from 'lucide-react';
import { login } from '../api';

const roles = [
  { id: 'customer', label: 'Customer', email: 'ayush@zerotouch.demo', icon: UserRound, note: 'Get payment support' },
  { id: 'employee', label: 'Employee', email: 'employee@zerotouch.demo', icon: UsersRound, note: 'Get work done' },
  { id: 'admin', label: 'Admin', email: 'admin@zerotouch.demo', icon: ShieldCheck, note: 'Oversee operations' },
];

export default function LoginScreen({ onLogin }) {
  const [account, setAccount] = useState('customer');
  const [email, setEmail] = useState(roles[0].email);
  const [password, setPassword] = useState('demo123');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function signIn(event) {
    event?.preventDefault();
    setBusy(true); setError('');
    try { await login(email, password); await onLogin(); }
    catch (err) { setError(err.message || 'Could not sign in. Please try again.'); }
    finally { setBusy(false); }
  }

  function selectRole(role) {
    setAccount(role.id); setEmail(role.email); setError('');
  }

  return (
    <main className="zt-login min-h-screen bg-[#f5f8fc] text-slate-900">
      <section className="zt-login-brand relative flex min-h-[360px] flex-col overflow-hidden px-7 py-7 text-white sm:px-12 lg:min-h-screen lg:px-16 lg:py-10">
        <div className="zt-orbit zt-orbit-one"/><div className="zt-orbit zt-orbit-two"/>
        <div className="relative z-10 flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-300 text-[#06254a]"><Zap size={20} fill="currentColor"/></div>
          <div><div className="text-lg font-extrabold tracking-tight">ZeroTouch <span className="text-cyan-300">AI</span></div><div className="mt-0.5 text-[10px] font-semibold uppercase tracking-[.18em] text-blue-200">One AI teammate. Every department.</div></div>
        </div>
        <div className="relative z-10 my-auto max-w-2xl py-12 lg:py-0">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[.07] px-3 py-1.5 text-[11px] font-semibold text-cyan-100"><Sparkles size={13}/> CONTROLLED AI WORKSPACE</div>
          <h1 className="max-w-xl text-[2.65rem] font-semibold leading-[1.08] tracking-[-.045em] sm:text-6xl">From request<br/>to <span className="text-cyan-300">resolved.</span></h1>
          <p className="mt-5 max-w-lg text-sm leading-6 text-blue-100/85 sm:text-base">One place to solve customer payment issues and coordinate employee work—with clear approvals, verified actions, and an audit trail.</p>
          <div className="mt-10 max-w-xl rounded-2xl border border-white/10 bg-[#0d3762]/70 p-4 backdrop-blur-sm sm:p-5">
            <div className="mb-4 flex items-center justify-between"><span className="text-xs font-bold text-white">A request moves forward</span><span className="inline-flex items-center gap-1.5 text-[10px] font-medium text-emerald-200"><span className="h-1.5 w-1.5 rounded-full bg-emerald-300"/> Policy guided</span></div>
            <div className="grid grid-cols-4 gap-2">
              {['Understand','Check','Act','Verify'].map((label, index)=><div key={label} className="relative">
                <div className="flex items-center gap-2"><span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full ${index < 2 ? 'bg-cyan-300 text-[#06254a]' : 'border border-white/20 bg-white/5 text-blue-100'}`}>{index < 2 ? <Check size={14}/> : <span className="text-[10px] font-bold">0{index+1}</span>}</span><span className="text-[10px] font-semibold text-blue-100 sm:text-xs">{label}</span></div>
                {index < 3 && <span className="absolute left-8 top-3.5 hidden h-px w-[calc(100%-1.5rem)] bg-white/20 sm:block"/>}
              </div>)}
            </div>
          </div>
        </div>
        <div className="relative z-10 flex items-center gap-2 text-[11px] text-blue-200"><ShieldCheck size={14} className="text-emerald-300"/> Actions stay within defined policies and approval paths.</div>
      </section>

      <section className="flex min-h-[600px] items-center justify-center px-5 py-12 sm:px-10 lg:min-h-screen">
        <div className="w-full max-w-[440px]">
          <div className="mb-8"><div className="text-xs font-bold uppercase tracking-[.16em] text-blue-700">Welcome to ZeroTouch</div><h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Choose your workspace</h2><p className="mt-2 text-sm leading-6 text-slate-500">Sign in to continue. Your experience adapts to your role.</p></div>
          <div className="space-y-2.5" role="group" aria-label="Choose a role">
            {roles.map(({id,label,email:roleEmail,icon:Icon,note})=>{
              const active=account===id;
              return <button key={id} type="button" onClick={()=>selectRole({id,email:roleEmail})} className={`zt-role-option flex w-full items-center gap-3.5 rounded-xl border p-3.5 text-left transition ${active?'border-blue-700 bg-white shadow-[0_4px_18px_rgba(7,53,107,.09)] ring-1 ring-blue-700':'border-slate-200 bg-white/70 hover:border-slate-300 hover:bg-white'}`}>
                <span className={`grid h-10 w-10 place-items-center rounded-xl ${active?'bg-[#07356b] text-white':'bg-slate-100 text-slate-500'}`}><Icon size={18}/></span>
                <span className="min-w-0 flex-1"><span className="block text-sm font-bold text-slate-900">{label}</span><span className="mt-0.5 block text-xs text-slate-500">{note}</span></span>
                <span className={`grid h-5 w-5 place-items-center rounded-full border ${active?'border-blue-700 bg-blue-700 text-white':'border-slate-300 text-transparent'}`}><Check size={12}/></span>
              </button>;
            })}
          </div>
          <form onSubmit={signIn} className="mt-6 space-y-4">
            <label className="block text-xs font-semibold text-slate-700">Email address<input type="email" autoComplete="username" required value={email} onChange={event=>setEmail(event.target.value)} className="zt-input mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-slate-900 outline-none transition"/></label>
            <label className="block text-xs font-semibold text-slate-700">Password<input type="password" autoComplete="current-password" required value={password} onChange={event=>setPassword(event.target.value)} className="zt-input mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-slate-900 outline-none transition"/></label>
            {error&&<p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs font-semibold text-rose-700">{error}</p>}
            <button disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#07356b] px-4 py-3.5 text-sm font-bold text-white shadow-sm transition hover:bg-[#05284f] focus:outline-none focus:ring-4 focus:ring-blue-200 disabled:opacity-60">{busy?'Signing in…':'Continue to ZeroTouch'}{!busy&&<ArrowRight size={16}/>}</button>
          </form>
          <div className="mt-5 flex items-center justify-between rounded-xl border border-slate-200 bg-white/70 px-3.5 py-3 text-[11px] text-slate-500"><span className="flex items-center gap-2"><Command size={14} className="text-slate-400"/> Hackathon demo workspace</span><span className="font-mono text-slate-400">Password: demo123</span></div>
          <p className="mt-5 flex items-center justify-center gap-1.5 text-[11px] text-slate-400"><CircleHelp size={13}/> Demo accounts are prefilled for each role.</p>
        </div>
      </section>
    </main>
  );
}
