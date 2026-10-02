import React, { useState, useEffect } from 'react';
import {
  Smartphone, Store, Bell, CheckCircle2, Clock, XCircle,
  Zap, ChevronLeft, ArrowRight, ShieldAlert, FileText,
  Building2, Radio, Banknote, HelpCircle, User, Info, ArrowUpRight
} from 'lucide-react';
import { getTransactions } from '../api';

function Callout({ num, text, show, positionClass }) {
  if (!show) return null;
  return (
    <div className={`absolute z-50 flex items-center gap-1.5 ${positionClass} animate-in fade-in zoom-in duration-300 pointer-events-none`}>
      <div className="w-5 h-5 rounded-full bg-fuchsia-600 text-white text-[11px] font-black flex items-center justify-center shadow-lg ring-2 ring-white shrink-0">
        {num}
      </div>
      <div className="bg-slate-900/90 backdrop-blur-sm text-white text-[10px] px-2 py-1 rounded shadow-lg whitespace-nowrap font-medium border border-white/20">
        {text}
      </div>
    </div>
  );
}

export default function ClientExperienceView({ selectedTxId, result, onSelectTx }) {
  const [viewType, setViewType] = useState('consumer'); // 'consumer' | 'merchant'
  const [consumerTab, setConsumerTab] = useState('detail'); // 'home' | 'history' | 'detail' | 'inbox'
  const [showCallouts, setShowCallouts] = useState(true);
  const [txList, setTxList] = useState([]);
  const [activeTxId, setActiveTxId] = useState(selectedTxId || 'TX9281');

  useEffect(() => {
    getTransactions().then(list => {
      setTxList(list);
      if (selectedTxId) {
        setActiveTxId(selectedTxId);
      } else if (list.length > 0 && !activeTxId) {
        setActiveTxId(list[0].transaction_id);
      }
    }).catch(console.error);
  }, [selectedTxId, result]);

  useEffect(() => {
    if (selectedTxId) {
      setActiveTxId(selectedTxId);
      setConsumerTab('detail');
      // If it's W3, automatically switch to merchant view!
      if (selectedTxId.startsWith('S')) {
        setViewType('merchant');
      } else {
        setViewType('consumer');
      }
    }
  }, [selectedTxId]);

  const currentTx = txList.find(t => t.transaction_id === activeTxId) || txList[0] || null;

  const handleTxChange = (id) => {
    setActiveTxId(id);
    if (onSelectTx) onSelectTx(id);
    if (id.startsWith('S')) {
      setViewType('merchant');
    } else {
      setViewType('consumer');
    }
  };

  const getStatusChip = (tx) => {
    if (!tx) return { label: 'Pending', color: 'text-amber-700 bg-amber-50 border-amber-200', icon: Clock };
    if (tx.resolution_status === 'RESOLVED') return { label: 'Refund Credited', color: 'text-emerald-700 bg-emerald-50 border-emerald-200', icon: CheckCircle2 };
    if (tx.resolution_status === 'ESCALATED') return { label: 'Under Review', color: 'text-rose-700 bg-rose-50 border-rose-200', icon: ShieldAlert };
    if (tx.resolution_status === 'NO_ACTION') return { label: 'Successful', color: 'text-emerald-700 bg-emerald-50 border-emerald-200', icon: CheckCircle2 };
    return { label: 'Processing', color: 'text-amber-700 bg-amber-50 border-amber-200', icon: Clock };
  };

  return (
    <div className="h-full flex flex-col bg-slate-100 overflow-hidden">
      
      {/* Top Controller Bar */}
      <div className="px-6 py-3.5 bg-white border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Client Surface:</span>
          <div className="flex bg-slate-100 p-1 rounded-xl">
            <button
              onClick={() => setViewType('consumer')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                viewType === 'consumer'
                  ? 'bg-paytm-dark text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Smartphone size={14} /> Paytm Consumer App
            </button>
            <button
              onClick={() => setViewType('merchant')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                viewType === 'merchant'
                  ? 'bg-paytm-dark text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Store size={14} /> Paytm for Business Portal
            </button>
          </div>
        </div>

        {/* Transaction Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-semibold">Simulated Tx:</span>
          <select
            value={activeTxId}
            onChange={(e) => handleTxChange(e.target.value)}
            className="text-xs font-mono font-bold bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800 outline-none cursor-pointer"
          >
            {txList.map(t => (
              <option key={t.transaction_id} value={t.transaction_id}>
                {t.transaction_id} (₹{t.amount}) - {t.resolution_status}
              </option>
            ))}
          </select>

          {/* Integration Callouts Toggle */}
          <label className="flex items-center gap-2 ml-2 cursor-pointer bg-fuchsia-50 hover:bg-fuchsia-100 border border-fuchsia-200 px-2.5 py-1.5 rounded-lg transition-colors">
            <input
              type="checkbox"
              checked={showCallouts}
              onChange={() => setShowCallouts(!showCallouts)}
              className="accent-fuchsia-600 w-3.5 h-3.5 cursor-pointer"
            />
            <span className="text-[11px] font-bold text-fuchsia-900">Show Integration Callouts</span>
          </label>
        </div>
      </div>

      {/* Explanatory Banner */}
      <div className="bg-blue-50 border-b border-blue-100 px-6 py-2.5 flex items-center justify-between text-xs text-blue-900 shrink-0">
        <div className="flex items-center gap-2">
          <Info size={14} className="text-paytm-primary shrink-0" />
          <span>
            {viewType === 'consumer' ? (
              <>
                <strong className="font-bold">Customer Perspective:</strong> The end user pays via Paytm. When an exception occurs, ZeroTouch acts in the background. The user receives a proactive refund notification & updated status without raising a ticket.
              </>
            ) : (
              <>
                <strong className="font-bold">Merchant Perspective:</strong> Merchants check daily settlements. ZeroTouch auto-reconciles fee shortfalls (S302) or flags KYC holds (S306) with instant itemized explanations.
              </>
            )}
          </span>
        </div>
      </div>

      {/* Main Body */}
      <div className="flex-1 overflow-y-auto p-6 flex items-center justify-center">
        {viewType === 'consumer' ? (
          /* ═══════════ PHONE MOCKUP (CONSUMER APP) ═══════════ */
          <div className="w-[360px] h-[640px] bg-slate-900 rounded-[44px] p-3 shadow-2xl border-4 border-slate-700 flex flex-col relative select-none">
            {/* Notch / Speaker */}
            <div className="absolute top-4 left-1/2 -translate-x-1/2 w-28 h-4 bg-slate-800 rounded-full z-50 flex items-center justify-center">
              <div className="w-8 h-1 bg-slate-600 rounded-full" />
            </div>

            {/* Inner Phone Screen */}
            <div className="w-full h-full bg-slate-50 rounded-[34px] overflow-hidden flex flex-col relative">
              
              {/* Phone Status Bar */}
              <div className="bg-paytm-dark text-white pt-6 pb-2 px-5 flex justify-between items-center text-[10px] font-semibold tracking-wider shrink-0 z-10">
                <span>9:41</span>
                <span className="flex items-center gap-1">5G 📶 100%</span>
              </div>

              {/* Phone Content */}
              <div className="flex-1 overflow-y-auto flex flex-col relative">
                {consumerTab === 'detail' && currentTx ? (
                  /* ── Consumer Transaction Detail Screen ── */
                  <div className="flex-1 flex flex-col bg-slate-50 relative pb-6">
                    <div className="bg-paytm-dark text-white px-4 py-3 flex items-center gap-3 shrink-0">
                      <button onClick={() => setConsumerTab('home')} className="p-1 hover:bg-white/10 rounded">
                        <ChevronLeft size={20} />
                      </button>
                      <span className="font-bold text-sm">Payment Details</span>
                    </div>

                    <Callout num="1" text="Paytm payment event emitted" show={showCallouts} positionClass="top-14 right-4" />

                    {/* Paid to Card */}
                    <div className="bg-white p-5 flex flex-col items-center border-b border-slate-100">
                      <div className="w-14 h-14 bg-paytm-dark/5 rounded-full flex items-center justify-center text-xl mb-2 font-bold text-paytm-dark">
                        🏪
                      </div>
                      <div className="font-bold text-slate-800 text-sm">Swiggy / Retail Merchant</div>
                      <div className="text-2xl font-black text-slate-900 mt-1">
                        ₹{currentTx.amount.toLocaleString('en-IN')}
                      </div>
                      <div className="mt-2">
                        {(() => {
                          const s = getStatusChip(currentTx);
                          const SIcon = s.icon;
                          return (
                            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold ${s.color}`}>
                              <SIcon size={13} /> {s.label}
                            </span>
                          );
                        })()}
                      </div>
                    </div>

                    {/* Details Table */}
                    <div className="bg-white mt-2 px-4 py-3 space-y-3 text-xs border-y border-slate-100 relative">
                      <Callout num="4" text="Paytm UI updated live" show={showCallouts} positionClass="top-2 left-2" />
                      <div className="flex justify-between">
                        <span className="text-slate-400">Customer</span>
                        <div className="text-right">
                          <span className="font-bold text-slate-800">{currentTx.customer_name || 'Paytm Customer'}</span>
                          <div className="flex items-center gap-1.5 justify-end mt-0.5">
                            {currentTx.is_first_time_user && (
                              <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 border border-amber-200">
                                ⭐ First-Time User
                              </span>
                            )}
                            <span className="text-[10px] font-mono font-bold text-emerald-700">
                              CIBIL: {currentTx.cibil_score || 750}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">UPI Ref ID</span>
                        <span className="font-mono font-bold text-slate-700">{currentTx.transaction_id}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Debit Account</span>
                        <span className="font-medium text-slate-700">HDFC Bank ··· 4821</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Time</span>
                        <span className="text-slate-700">Today, 02:45 PM</span>
                      </div>
                    </div>

                    {/* ZeroTouch Resolution Banner (Simulated In-App) */}
                    {currentTx.resolution_status === 'RESOLVED' && (
                      <div className="mx-3 mt-3 bg-emerald-50 border border-emerald-200 rounded-xl p-3 relative shadow-sm">
                        <Callout num="3" text="ZeroTouch Action: Auto-reversal executed" show={showCallouts} positionClass="-top-3 right-2" />
                        <div className="flex items-start gap-2">
                          <CheckCircle2 size={16} className="text-emerald-600 mt-0.5 shrink-0" />
                          <div>
                            <div className="text-xs font-bold text-emerald-800">
                              Auto-Refund Initiated
                            </div>
                            <div className="text-[11px] text-emerald-800 mt-0.5 leading-snug">
                              {currentTx.dynamic_message ? (
                                <span className="italic font-medium">"{currentTx.dynamic_message}"</span>
                              ) : (
                                `ZeroTouch AI identified that ₹${currentTx.amount} was debited but not received by merchant. Full refund sent back to your account.`
                              )}
                            </div>
                            <div className="text-[10px] font-mono text-emerald-700 mt-1 font-bold">
                              Ref: {currentTx.action_id || `REV-${currentTx.transaction_id}`}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {currentTx.resolution_status === 'ESCALATED' && (
                      <div className="mx-3 mt-3 bg-rose-50 border border-rose-200 rounded-xl p-3 relative shadow-sm">
                        <Callout num="2" text="ZeroTouch decides: High risk → Human Queue" show={showCallouts} positionClass="-top-3 right-2" />
                        <div className="flex items-start gap-2">
                          <ShieldAlert size={16} className="text-rose-600 mt-0.5 shrink-0" />
                          <div>
                            <div className="text-xs font-bold text-rose-800">Under Review by Paytm Desk</div>
                            <div className="text-[11px] text-rose-700 mt-0.5 leading-snug">
                              Transaction is under expedited review. A specialized support officer is verifying the bank trace.
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Need Help? button */}
                    <div className="mt-4 px-4">
                      <div className="w-full py-2.5 rounded-lg border border-slate-200 bg-white text-center text-xs font-bold text-slate-600">
                        Need Help with this Payment?
                      </div>
                    </div>
                  </div>
                ) : (
                  /* ── Consumer Home / Passbook Screen ── */
                  <div className="flex-1 flex flex-col bg-slate-50">
                    {/* Header */}
                    <div className="bg-paytm-dark text-white p-4 pt-3 rounded-b-2xl shadow-sm">
                      <div className="flex justify-between items-center mb-4">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-xs font-bold">
                            AB
                          </div>
                          <span className="font-extrabold text-sm tracking-tight">Paytm</span>
                        </div>
                        <div className="relative">
                          <Bell size={18} />
                          {txList.some(t => t.resolution_status === 'RESOLVED') && (
                            <span className="absolute -top-1 -right-1 w-2 h-2 bg-paytm-primary rounded-full animate-ping" />
                          )}
                        </div>
                      </div>

                      <div className="text-[11px] text-blue-200">Total Balance</div>
                      <div className="text-2xl font-black text-white mt-0.5">₹42,850.00</div>
                    </div>

                    {/* In-app Push Notification Banner if any resolved */}
                    {txList.some(t => t.resolution_status === 'RESOLVED') && (
                      <div className="m-3 p-3 bg-white rounded-xl shadow-md border-l-4 border-emerald-500 flex items-start gap-2 animate-in slide-in-from-top duration-300">
                        <Zap size={16} className="text-paytm-primary mt-0.5 shrink-0" />
                        <div>
                          <div className="text-xs font-bold text-slate-800">Refund Credited</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">
                            ₹2,500 has been credited back to your account automatically.
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Recent Transactions List */}
                    <div className="flex-1 px-3 py-2">
                      <div className="text-xs font-bold text-slate-500 mb-2 px-1">Passbook & Transactions</div>
                      <div className="space-y-1.5">
                        {txList.slice(0, 5).map(tx => {
                          const s = getStatusChip(tx);
                          return (
                            <div
                              key={tx.transaction_id}
                              onClick={() => { setActiveTxId(tx.transaction_id); setConsumerTab('detail'); }}
                              className="bg-white p-3 rounded-xl border border-slate-100 flex items-center justify-between cursor-pointer hover:border-paytm-primary/40 transition-colors shadow-2xs"
                            >
                              <div>
                                <div className="font-bold text-xs text-slate-800">{tx.transaction_id}</div>
                                <div className="text-[10px] text-slate-400 mt-0.5">{s.label}</div>
                              </div>
                              <div className="text-right">
                                <div className="font-bold text-xs text-slate-900">₹{tx.amount}</div>
                                <span className={`inline-block text-[9px] font-bold px-1.5 py-0.5 rounded ${s.color}`}>
                                  {tx.resolution_status}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Phone Bottom Tab Bar */}
              <div className="h-12 bg-white border-t border-slate-200 flex justify-around items-center px-2 shrink-0">
                <button
                  onClick={() => setConsumerTab('home')}
                  className={`flex flex-col items-center text-[9px] font-bold ${consumerTab === 'home' ? 'text-paytm-primary' : 'text-slate-400'}`}
                >
                  <Smartphone size={16} /> Home
                </button>
                <button
                  onClick={() => setConsumerTab('detail')}
                  className={`flex flex-col items-center text-[9px] font-bold ${consumerTab === 'detail' ? 'text-paytm-primary' : 'text-slate-400'}`}
                >
                  <FileText size={16} /> Transaction
                </button>
              </div>

            </div>
          </div>
        ) : (
          /* ═══════════ MERCHANT DASHBOARD (PAYTM FOR BUSINESS) ═══════════ */
          <div className="w-full max-w-4xl bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col">
            
            {/* Merchant Portal Top Bar */}
            <div className="bg-paytm-dark text-white px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-purple-600 flex items-center justify-center text-white font-bold">
                  🏪
                </div>
                <div>
                  <div className="font-extrabold text-sm tracking-tight flex items-center gap-2">
                    Paytm for Business <span className="text-[10px] bg-white/20 px-2 py-0.5 rounded font-mono">MERCHANT PORTAL</span>
                  </div>
                  <div className="text-xs text-blue-200">Merchant: Sharma Electronics & Supermarket</div>
                </div>
              </div>
              <div className="text-right text-xs">
                <div className="text-blue-200">Next Settlement Cycle:</div>
                <div className="font-bold text-white">Tomorrow, 07:00 AM</div>
              </div>
            </div>

            {/* Merchant Settlement Content */}
            <div className="p-6 space-y-6">
              
              {/* Batch S302 / S306 Explanations */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* S-302 Card */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 relative">
                  <Callout num="3" text="ZeroTouch: Auto-generated fee reconciliation" show={showCallouts} positionClass="-top-3 right-4" />
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-xs text-slate-800">Batch S-302: ₹50,000 Payout</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                      Reconciled Automatically
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mb-3">
                    Merchant received ₹49,000 (₹1,000 platform fee deduction). ZeroTouch detected the perceived shortfall and sent an itemized explanation before any ticket was raised.
                  </p>
                  <div className="bg-white border border-slate-200 rounded-lg p-3 text-xs space-y-1.5 font-mono">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Gross Sales</span>
                      <span className="font-bold text-slate-800">₹50,000.00</span>
                    </div>
                    <div className="flex justify-between text-rose-600">
                      <span>MDR & Platform Fee (2%)</span>
                      <span>-₹1,000.00</span>
                    </div>
                    <div className="flex justify-between border-t border-slate-100 pt-1 text-emerald-700 font-bold">
                      <span>Net Settlement</span>
                      <span>₹49,000.00</span>
                    </div>
                  </div>
                  <div className="mt-2 text-[10px] text-slate-400 font-medium">
                    ✓ Explanation PDF auto-dispatched to merchant email. Zero support ticket needed.
                  </div>
                </div>

                {/* S-306 Card */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 relative">
                  <Callout num="2" text="ZeroTouch: Policy blocks payout on expired KYC" show={showCallouts} positionClass="-top-3 right-4" />
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-xs text-slate-800">Batch S-306: ₹45,000 Payout</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800">
                      Compliance Hold
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mb-3">
                    Settlement held by ZeroTouch policy because merchant KYC documents expired. Automated compliance flow notified merchant to upload Aadhaar/PAN.
                  </p>
                  <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-xs space-y-1 text-rose-800">
                    <div className="font-bold flex items-center gap-1.5">
                      <ShieldAlert size={14} className="text-rose-600" /> Action Required: Update KYC
                    </div>
                    <div className="text-[11px] text-rose-700">
                      Please upload your renewed GSTIN certificate and PAN to release ₹45,000 escrow funds.
                    </div>
                  </div>
                  <div className="mt-3 flex justify-end">
                    <button className="px-3 py-1.5 rounded-lg bg-paytm-dark text-white text-xs font-bold hover:bg-slate-800">
                      Upload Documents
                    </button>
                  </div>
                </div>

              </div>

              {/* Settlement History Table */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase tracking-wider">
                  Recent Merchant Payout Batches
                </div>
                <table className="w-full text-xs">
                  <thead className="border-b border-slate-100 text-slate-400 font-medium bg-white">
                    <tr>
                      <th className="text-left p-3">Batch ID</th>
                      <th className="text-left p-3">Gross Amount</th>
                      <th className="text-left p-3">Deductions</th>
                      <th className="text-left p-3">Net Deposited</th>
                      <th className="text-left p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr>
                      <td className="p-3 font-mono font-bold text-slate-800">S-302</td>
                      <td className="p-3 font-semibold">₹50,000.00</td>
                      <td className="p-3 text-rose-600 font-mono">-₹1,000.00</td>
                      <td className="p-3 font-bold text-emerald-700">₹49,000.00</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold border border-emerald-200">
                          Reconciled (ZeroTouch)
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td className="p-3 font-mono font-bold text-slate-800">S-306</td>
                      <td className="p-3 font-semibold">₹45,000.00</td>
                      <td className="p-3 text-slate-400 font-mono">₹0.00</td>
                      <td className="p-3 font-bold text-rose-600">Held in Escrow</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 font-bold border border-rose-200">
                          KYC Hold (ZeroTouch)
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

            </div>
          </div>
        )}
      </div>

    </div>
  );
}
