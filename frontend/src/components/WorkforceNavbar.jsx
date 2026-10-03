import React from 'react';
import {
  ShieldAlert, ShieldCheck, Terminal, Layers, RefreshCw,
  Users, CheckCircle2, AlertTriangle, ChevronDown, Sparkles,
  Command, Eye, Zap, HelpCircle
} from 'lucide-react';

export default function WorkforceNavbar({
  currentRole,
  roles,
  onSelectRole,
  activeTab,
  onSelectTab,
  killSwitchActive,
  onToggleKillSwitch,
  onOpenCommandBar,
  showIntegrationPoints,
  onToggleIntegrationPoints,
  onResetPlatform,
  isResetting,
}) {
  return (
    <header className="bg-[#07356b] text-white border-b border-white/10 shrink-0 select-none shadow-md z-30">
      {/* Top Bar */}
      <div className="h-14 px-4 flex items-center justify-between">
        {/* Brand & Track */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-cyan-400 text-[#07356b] flex items-center justify-center font-extrabold shadow-sm">
            <Zap size={18} className="fill-[#07356b]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-base tracking-tight text-white">ZeroTouch Workforce</span>
              <span className="bg-cyan-500/20 text-cyan-300 border border-cyan-400/30 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
                Prototype
              </span>
            </div>
            <div className="text-[10px] text-blue-200/80 font-medium -mt-0.5">
              Team Trex · Paytm Hackathon: Autonomous AI Teammates
            </div>
          </div>
        </div>

        {/* Global Action Bar */}
        <div className="flex items-center gap-2.5">
          {/* Command Bar Button */}
          <button
            onClick={onOpenCommandBar}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/15 border border-white/20 text-xs font-semibold text-white transition shadow-xs group"
            title="Open Autonomous Command Bar (Ctrl+K or /)"
          >
            <Terminal size={14} className="text-cyan-300 group-hover:scale-110 transition-transform" />
            <span className="hidden sm:inline">Command Bar</span>
            <kbd className="hidden md:inline-block px-1.5 py-0.5 text-[9px] font-mono bg-white/20 rounded text-blue-100">
              /
            </kbd>
          </button>

          {/* Show Integration Points Toggle */}
          <button
            onClick={onToggleIntegrationPoints}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-semibold border transition ${
              showIntegrationPoints
                ? 'bg-amber-400/20 text-amber-300 border-amber-400/50 shadow-xs'
                : 'bg-white/5 text-blue-200 border-white/10 hover:bg-white/10 hover:text-white'
            }`}
            title="Toggle numbered integration point overlays (Page 6)"
          >
            <Eye size={13} />
            <span className="hidden lg:inline">Integration Points</span>
          </button>

          {/* Emergency Kill Switch */}
          <button
            onClick={onToggleKillSwitch}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-extrabold border transition shadow-xs ${
              killSwitchActive
                ? 'bg-rose-600 hover:bg-rose-700 text-white border-rose-400 animate-pulse'
                : 'bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 border-emerald-500/40'
            }`}
            title="Emergency Kill Switch: Forces all autonomous skills back to human review"
          >
            {killSwitchActive ? (
              <>
                <ShieldAlert size={14} className="text-white animate-bounce" />
                <span>KILL SWITCH ACTIVE (FORCED L1)</span>
              </>
            ) : (
              <>
                <ShieldCheck size={14} className="text-emerald-400" />
                <span className="hidden sm:inline">Kill Switch</span>
                <span className="text-[10px] opacity-75 font-mono">NORMAL</span>
              </>
            )}
          </button>

          {/* Role Switcher Dropdown */}
          <div className="relative">
            <select
              value={currentRole.role_id}
              onChange={e => {
                const found = roles.find(r => r.role_id === e.target.value);
                if (found) onSelectRole(found);
              }}
              aria-label="Select employee role"
              className="bg-white/15 hover:bg-white/20 text-white text-xs font-bold rounded-xl px-3 py-1.5 border border-white/20 outline-none cursor-pointer pr-7 appearance-none transition"
            >
              {roles.map(r => (
                <option key={r.role_id} value={r.role_id} className="text-slate-900 bg-white">
                  {r.avatar} {r.name} ({r.title})
                </option>
              ))}
            </select>
            <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-blue-200" />
          </div>

          {/* Reset Demo Platform */}
          <button
            onClick={onResetPlatform}
            disabled={isResetting}
            className="p-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-blue-200 hover:text-white border border-white/15 transition disabled:opacity-50"
            title="Reset platform data to clean state"
          >
            <RefreshCw size={14} className={isResetting ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Domain Navigation Tabs */}
      <div className="h-10 px-4 bg-[#05284f]/90 border-t border-white/5 flex items-center justify-between text-xs overflow-x-auto">
        <div className="flex items-center gap-1">
          <button
            onClick={() => onSelectTab('inbox')}
            className={`px-3 py-1 rounded-lg font-bold transition flex items-center gap-1.5 ${
              activeTab === 'inbox'
                ? 'bg-white text-[#07356b] shadow-xs'
                : 'text-blue-200 hover:bg-white/10 hover:text-white'
            }`}
          >
            <span>📥 Task Inbox</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-cyan-500 text-white font-mono">
              6 Pre-Worked
            </span>
          </button>

          <button
            onClick={() => onSelectTab('finance')}
            className={`px-3 py-1 rounded-lg font-bold transition flex items-center gap-1.5 ${
              activeTab === 'finance'
                ? 'bg-white text-[#07356b] shadow-xs'
                : 'text-blue-200 hover:bg-white/10 hover:text-white'
            }`}
          >
            <span>📊 Finance Reconciliation</span>
          </button>

          <button
            onClick={() => onSelectTab('studio')}
            className={`px-3 py-1 rounded-lg font-bold transition flex items-center gap-1.5 ${
              activeTab === 'studio'
                ? 'bg-white text-[#07356b] shadow-xs'
                : 'text-blue-200 hover:bg-white/10 hover:text-white'
            }`}
          >
            <span>🛠️ Skill Studio (Teach IT)</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-400 text-slate-900 font-bold">
              Winning Slice
            </span>
          </button>

          <button
            onClick={() => onSelectTab('academy')}
            className={`px-3 py-1 rounded-lg font-bold transition flex items-center gap-1.5 ${
              activeTab === 'academy'
                ? 'bg-white text-[#07356b] shadow-xs'
                : 'text-blue-200 hover:bg-white/10 hover:text-white'
            }`}
          >
            <span>🎓 Academy (Joiner Sandbox)</span>
          </button>

          <button
            onClick={() => onSelectTab('dashboard')}
            className={`px-3 py-1 rounded-lg font-bold transition flex items-center gap-1.5 ${
              activeTab === 'dashboard'
                ? 'bg-white text-[#07356b] shadow-xs'
                : 'text-blue-200 hover:bg-white/10 hover:text-white'
            }`}
          >
            <span>📈 Manager Dashboard</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-emerald-400 text-slate-900 font-bold">
              1.5 FTE Freed
            </span>
          </button>
        </div>

        {/* Current Role Banner */}
        <div className="hidden md:flex items-center gap-2 text-[11px] text-blue-200">
          <span className="opacity-70">Active Employee:</span>
          <span className="font-bold text-white flex items-center gap-1">
            {currentRole.avatar} {currentRole.name} · <span className="text-cyan-300 font-normal">{currentRole.title}</span>
          </span>
        </div>
      </div>
    </header>
  );
}
