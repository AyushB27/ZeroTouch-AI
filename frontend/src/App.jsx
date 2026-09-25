import React, { useState, useEffect, useCallback, useRef } from 'react';
import { RefreshCw, Play, CheckCircle2, Loader2, WifiOff, Shield } from 'lucide-react';
import ScenarioSelector from './components/ScenarioSelector';
import TransactionHeader from './components/TransactionHeader';
import SystemStatus from './components/SystemStatus';
import AgentTimeline from './components/AgentTimeline';
import ResolutionPanel from './components/ResolutionPanel';
import EvidencePanel from './components/EvidencePanel';
import EscalationPanel from './components/EscalationPanel';
import InvestigationNarrative from './components/InvestigationNarrative';
import { getTransaction, runResolution, getEvents, resetDemo } from './api';

const TX_IDS = ['TX9281', 'TX9342', 'TX9410'];

export default function App() {
  const [selectedTx, setSelectedTx] = useState('TX9281');
  const [transaction, setTransaction] = useState(null);
  const [result, setResult] = useState(null);
  const [events, setEvents] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [error, setError] = useState(null);
  const [backendDown, setBackendDown] = useState(false);

  const loadTransaction = useCallback(async (txId) => {
    try {
      setError(null);
      setBackendDown(false);
      setTransaction(null);
      setResult(null);
      setEvents([]);
      const tx = await getTransaction(txId);
      setTransaction(tx);
      
      const evs = await getEvents(txId);
      setEvents(evs);

      if (tx.resolution_status !== 'PENDING') {
        const fakeResult = {
          resolution_status: tx.resolution_status,
          decision: tx.resolution_status === 'RESOLVED' ? 'AUTO_REVERSAL' : 'HUMAN_ESCALATION',
          action_id: tx.action_id,
          support_case: tx.resolution_status === 'ESCALATED' ? `CASE-ZT${txId.slice(2)}` : null,
          evidence: {
            bank: tx.bank_status,
            network: tx.network_status,
            merchant: tx.merchant_status,
            settlement: tx.settlement_status,
            amount: tx.amount,
            risk: tx.risk_score
          }
        };
        setResult(fakeResult);
      }
    } catch (err) {
      console.error(err);
      if (err.message === 'Failed to fetch') {
        setBackendDown(true);
      } else {
        setError(err.message);
      }
    }
  }, []);

  useEffect(() => {
    loadTransaction(selectedTx);
  }, [selectedTx, loadTransaction]);

  const handleRun = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setError(null);
    setResult(null);
    setEvents([]);

    try {
      // Poll events while running
      const pollInterval = setInterval(async () => {
        try {
          const evs = await getEvents(selectedTx);
          setEvents(evs);
        } catch (e) { }
      }, 500);

      const res = await runResolution(selectedTx);
      clearInterval(pollInterval);
      
      const finalEvs = await getEvents(selectedTx);
      setEvents(finalEvs);
      
      setResult(res);
      await loadTransaction(selectedTx); // refresh state
    } catch (err) {
      setError(err.message);
    } finally {
      setIsRunning(false);
    }
  };

  const handleReset = async () => {
    setIsResetting(true);
    try {
      await resetDemo();
      await loadTransaction(selectedTx);
    } catch (err) {
      setError('Failed to reset demo');
    } finally {
      setIsResetting(false);
    }
  };

  const handleSelectScenario = (txId) => {
    if (isRunning) return;
    setSelectedTx(txId);
  };

  const isAlreadyResolved = transaction && transaction.resolution_status !== 'PENDING';
  const canRun = transaction && !isAlreadyResolved && !isRunning;

  if (backendDown) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
        <WifiOff size={48} className="text-slate-300 mb-4" />
        <h1 className="text-xl font-bold text-slate-800 mb-2">Backend Disconnected</h1>
        <p className="text-slate-500 mb-6 text-center max-w-md">
          Make sure the FastAPI backend is running on port 8000. <br/>
          <code className="bg-slate-100 px-2 py-1 rounded text-sm mt-2 block">python -m uvicorn backend.main:app --port 8000</code>
        </p>
        <button onClick={() => loadTransaction(selectedTx)} className="px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700">
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans pb-20">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
              <Shield size={14} className="text-white" />
            </div>
            <div>
              <span className="font-bold text-slate-900 text-sm tracking-tight">ZERO TOUCH</span>
              <span className="text-slate-400 text-xs ml-2">Payment Resolution Teammate</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-emerald-400 pulse-dot" />
              <span className="text-xs font-semibold text-slate-600">AUTONOMOUS MODE</span>
            </div>
            <button 
              onClick={handleReset}
              disabled={isResetting || isRunning}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 border border-slate-200 rounded-lg px-3 py-1.5 hover:bg-slate-50 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={12} className={isResetting ? 'animate-spin' : ''} />
              RESET DEMO
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6 space-y-5">
        {/* Scenario Selector */}
        <ScenarioSelector selected={selectedTx} onSelect={handleSelectScenario} />

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Transaction Header */}
        <TransactionHeader transaction={transaction} />

        {/* System Status */}
        <SystemStatus transaction={transaction} />

        {/* Layer 3 — Agent Investigation Narrative */}
        {result?.investigation_narrative && (
          <InvestigationNarrative 
            narrative={result.investigation_narrative} 
            agentPowered={result.agent_powered}
          />
        )}

        {/* Main Grid */}
        <div className="grid grid-cols-3 gap-5">
          {/* Left: Agent Timeline */}
          <div className="col-span-2">
            <AgentTimeline events={events} isRunning={isRunning} />
          </div>
          {/* Right: Resolution */}
          <div className="space-y-5">
            <ResolutionPanel result={result} />
          </div>
        </div>

        {/* Evidence */}
        {(result?.evidence) && (
          <EvidencePanel evidence={result.evidence} />
        )}

        {/* Escalation */}
        {result && result.resolution_status === 'ESCALATED' && (
          <EscalationPanel result={result} />
        )}

        {/* CTA */}
        <div className="flex justify-center pb-4">
          {isAlreadyResolved ? (
            <div className="flex items-center gap-2 px-6 py-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-sm font-semibold">
              <CheckCircle2 size={16} />
              {transaction.resolution_status === 'RESOLVED' ? 'RESOLUTION COMPLETE' : 
               transaction.resolution_status === 'NO_ACTION' ? 'NO ACTION REQUIRED' : 
               'ESCALATED TO HUMAN'}
            </div>
          ) : (
            <button
              onClick={handleRun}
              disabled={!canRun}
              className={`flex items-center gap-2.5 px-8 py-3.5 rounded-xl text-sm font-bold tracking-wide transition-all ${
                isRunning 
                  ? 'bg-blue-100 text-blue-600 border border-blue-200 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-md active:scale-95'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {isRunning ? (
                <><Loader2 size={16} className="animate-spin" /> RESOLUTION IN PROGRESS</>
              ) : (
                <><Play size={16} /> RUN RESOLUTION</>
              )}
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
