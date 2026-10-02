import React, { useState, useEffect, useCallback, useRef } from 'react';
import { RefreshCw, Play, CheckCircle2, Loader2, WifiOff, Shield, Smartphone } from 'lucide-react';
import AgentTimeline from './components/AgentTimeline';
import PhoneMockup from './components/PhoneMockup';
import SupportConsole from './components/SupportConsole';
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
    <div className="min-h-screen bg-paytm-light text-slate-900 font-sans flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <header className="bg-paytm-dark border-b border-paytm-dark shadow-sm z-10 shrink-0">
        <div className="max-w-[1400px] mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-white flex items-center justify-center">
              <Shield size={18} className="text-paytm-primary" />
            </div>
            <div>
              <span className="font-bold text-white text-lg tracking-tight">ZeroTouch</span>
              <span className="text-paytm-primary text-xs ml-2 font-medium">Autonomous Agent</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 bg-white/10 px-3 py-1 rounded-full">
              <div className="w-2 h-2 rounded-full bg-paytm-green animate-pulse" />
              <span className="text-xs font-semibold text-white tracking-wide">AUTONOMOUS MODE</span>
            </div>
            <button 
              onClick={handleReset}
              disabled={isResetting || isRunning}
              className="flex items-center gap-1.5 text-xs text-white hover:text-white border border-white/20 rounded hover:bg-white/10 px-3 py-1.5 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={12} className={isResetting ? 'animate-spin' : ''} />
              RESET
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col max-w-[1400px] mx-auto w-full px-6 py-4 gap-4 overflow-hidden">
        
        {/* Scenario Selector & Demo Control Panel */}
        <div className="shrink-0 bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
          <div className="flex gap-2 flex-1">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center mr-2">Demo Injector</div>
            {['TX9281', 'TX9342', 'TX9410'].map(tx => (
              <button
                key={tx}
                onClick={() => handleSelectScenario(tx)}
                className={`px-4 py-2 text-sm font-semibold rounded transition-colors ${
                  selectedTx === tx 
                  ? 'bg-paytm-primary text-white shadow-sm' 
                  : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                Fire {tx}
              </button>
            ))}
          </div>

          <button
            onClick={handleRun}
            disabled={!canRun}
            className={`flex items-center gap-2 px-6 py-2 rounded text-sm font-bold tracking-wide transition-all ${
              isRunning 
                ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
                : 'bg-paytm-dark hover:bg-paytm-dark/90 text-white shadow-md active:scale-95'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isRunning ? (
              <><Loader2 size={16} className="animate-spin" /> EXECUTING...</>
            ) : isAlreadyResolved ? (
              <><CheckCircle2 size={16} /> COMPLETED</>
            ) : (
              <><Play size={16} /> TRIGGER EVENT</>
            )}
          </button>
        </div>

        {error && (
          <div className="shrink-0 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Three Column Layout */}
        <div className="flex-1 flex gap-4 min-h-0">
          
          {/* Left: Phone Mockup (35%) */}
          <div className="w-[35%] flex flex-col items-center justify-center bg-white rounded-xl border border-slate-200 p-4 overflow-y-auto">
             <div className="w-full mb-4 flex items-center gap-2">
               <Smartphone size={16} className="text-paytm-primary" />
               <span className="text-sm font-bold text-slate-700">Customer App View</span>
             </div>
             {/* PhoneMockup Component */}
             <PhoneMockup transaction={transaction} result={result} />
          </div>

          {/* Center: Agent Trace (30%) */}
          <div className="w-[30%] flex flex-col min-h-0">
            <AgentTimeline events={events} isRunning={isRunning} />
          </div>

          {/* Right: Support Console (35%) */}
          <div className="w-[35%] flex flex-col min-h-0">
            <SupportConsole result={result} isRunning={isRunning} />
          </div>
          
        </div>
      </main>
    </div>
  );
}
