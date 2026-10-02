import React, { useState, useEffect } from 'react';
import { ChevronLeft, Bell, Home as HomeIcon, List, HelpCircle, Store, Banknote, CheckCircle2, Clock, ShieldAlert, Zap, Search, User, XCircle } from 'lucide-react';
import { getTransactions } from '../api';

function Callout({ num, text, show, positionClass }) {
  if (!show) return null;
  return (
    <div className={`absolute z-50 flex items-center gap-1.5 ${positionClass} animate-in fade-in zoom-in duration-300`}>
      <div className="w-5 h-5 rounded-full bg-fuchsia-600 text-white text-[11px] font-bold flex items-center justify-center shadow-lg ring-2 ring-white">
        {num}
      </div>
      <div className="bg-slate-800 text-white text-[10px] px-2 py-1.5 rounded shadow-lg whitespace-nowrap font-medium">
        {text}
      </div>
    </div>
  );
}

export default function PhoneMockup({ transaction, result }) {
  const [viewMode, setViewMode] = useState('consumer');
  const [activeTab, setActiveTab] = useState('home');
  const [selectedTxId, setSelectedTxId] = useState(null);
  const [showIntegration, setShowIntegration] = useState(false);
  const [txList, setTxList] = useState([]);

  useEffect(() => {
    // Poll for the latest transactions when result or transaction prop changes
    getTransactions().then(setTxList).catch(console.error);
  }, [transaction, result]);

  const openDetail = (tx) => {
     setSelectedTxId(tx.transaction_id);
  };
  
  const getStatusInfo = (tx) => {
      if (tx.resolution_status === 'RESOLVED') return { label: 'Refunded', color: 'text-emerald-600', bg: 'bg-emerald-50', icon: CheckCircle2 };
      if (tx.resolution_status === 'ESCALATED') return { label: 'Under review', color: 'text-amber-600', bg: 'bg-amber-50', icon: Clock };
      if (tx.resolution_status === 'NO_ACTION') return { label: 'Success', color: 'text-emerald-600', bg: 'bg-emerald-50', icon: CheckCircle2 };
      if (tx.resolution_status === 'PENDING') {
          if (tx.bank_status === 'DEBITED') return { label: 'Processing', color: 'text-amber-600', bg: 'bg-amber-50', icon: Clock };
          return { label: 'Failed', color: 'text-rose-600', bg: 'bg-rose-50', icon: XCircle };
      }
      return { label: 'Unknown', color: 'text-slate-600', bg: 'bg-slate-50', icon: Clock };
  };

  const renderConsumerContent = () => {
     if (selectedTxId) {
         const tx = txList.find(t => t.transaction_id === selectedTxId) || transaction;
         if (!tx) return null;
         const status = getStatusInfo(tx);
         const StatusIcon = status.icon;
         
         return (
             <div className="flex-1 bg-slate-50 flex flex-col relative">
                <div className="bg-paytm-dark text-white pt-10 pb-4 px-4 flex items-center gap-3 shrink-0">
                  <button onClick={() => setSelectedTxId(null)}><ChevronLeft size={24}/></button>
                  <span className="font-semibold">Transaction Details</span>
                </div>
                <div className="flex-1 overflow-y-auto pb-4 relative">
                    <Callout num="1" text="Paytm event emitted" show={showIntegration} positionClass="top-2 right-4" />
                    <div className="bg-white p-6 flex flex-col items-center border-b border-slate-100">
                      <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-3 text-2xl">🏪</div>
                      <h2 className="text-lg font-bold text-slate-800">Merchant Payment</h2>
                      <div className="text-3xl font-bold mt-2 text-slate-800">₹{tx.amount.toLocaleString('en-IN')}</div>
                      <div className={`flex items-center gap-1.5 mt-3 px-3 py-1 rounded-full text-xs font-bold ${status.bg} ${status.color}`}>
                        <StatusIcon size={14} /> {status.label}
                      </div>
                    </div>

                    <div className="bg-white mt-2 px-4 py-3 space-y-4 text-sm border-y border-slate-100 relative">
                        <Callout num="4" text="Paytm UI updated" show={showIntegration} positionClass="top-2 left-2" />
                        <div className="flex justify-between">
                            <span className="text-slate-500">To</span>
                            <span className="font-semibold text-slate-800">Mock Merchant</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-slate-500">From</span>
                            <span className="font-semibold text-slate-800">Bank Account **** 1234</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-slate-500">UPI Ref</span>
                            <span className="font-mono text-slate-800">{tx.transaction_id}</span>
                        </div>
                    </div>

                    {tx.resolution_status === 'RESOLVED' && (
                       <div className="mx-4 mt-4 bg-emerald-50 border border-emerald-200 rounded-lg p-3 relative shadow-sm">
                         <Callout num="3" text="Action API called" show={showIntegration} positionClass="-top-3 -right-2" />
                         <div className="flex items-start gap-2">
                           <Zap size={16} className="text-emerald-600 mt-0.5" />
                           <div>
                             <div className="text-xs font-bold text-emerald-800">Resolved Automatically</div>
                             <div className="text-[10px] text-emerald-600 mt-0.5">ZeroTouch detected the failure and refunded ₹{tx.amount} to your account. No ticket needed.</div>
                           </div>
                         </div>
                       </div>
                    )}
                    {tx.resolution_status === 'ESCALATED' && (
                       <div className="mx-4 mt-4 bg-amber-50 border border-amber-200 rounded-lg p-3 relative shadow-sm">
                         <Callout num="2" text="ZeroTouch decides" show={showIntegration} positionClass="-top-3 -right-2" />
                         <div className="flex items-start gap-2">
                           <Clock size={16} className="text-amber-600 mt-0.5" />
                           <div>
                             <div className="text-xs font-bold text-amber-800">Under Review</div>
                             <div className="text-[10px] text-amber-600 mt-0.5">Our team is manually reviewing this transaction. Ticket created.</div>
                           </div>
                         </div>
                       </div>
                    )}
                </div>
             </div>
         );
     }

     switch(activeTab) {
         case 'home':
             return (
                 <div className="flex-1 bg-slate-50 overflow-y-auto">
                    <div className="bg-paytm-dark text-white pt-10 pb-6 px-4 rounded-b-2xl shadow-sm relative">
                       <Callout num="4" text="Paytm UI updated" show={showIntegration} positionClass="bottom-2 right-4" />
                       <div className="flex justify-between items-center mb-6">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center"><User size={16}/></div>
                            <span className="font-bold text-sm tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-blue-200">Paytm <span className="text-[10px] ml-1 bg-white/20 px-1.5 py-0.5 rounded text-white font-mono">PROTOTYPE</span></span>
                          </div>
                          <div className="relative cursor-pointer" onClick={() => setActiveTab('inbox')}>
                            <Bell size={20} />
                            {txList.some(t => t.resolution_status === 'RESOLVED') && (
                              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-rose-500 rounded-full border-2 border-paytm-dark"></span>
                            )}
                          </div>
                       </div>
                       <div className="text-sm text-blue-100">UPI Balance</div>
                       <div className="text-3xl font-bold mt-1">₹45,210</div>
                    </div>

                    <div className="grid grid-cols-4 gap-4 px-4 py-6 bg-white border-b border-slate-100">
                       {[{icon: Search, label: 'Scan'}, {icon: User, label: 'To Mobile'}, {icon: Store, label: 'To Self'}, {icon: Banknote, label: 'To Bank'}].map(s => (
                         <div key={s.label} className="flex flex-col items-center gap-2">
                           <div className="w-12 h-12 rounded-full bg-paytm-primary/10 flex items-center justify-center text-paytm-dark"><s.icon size={20}/></div>
                           <div className="text-[10px] font-semibold text-slate-700">{s.label}</div>
                         </div>
                       ))}
                    </div>

                    <div className="px-4 py-4">
                       <div className="text-xs font-bold text-slate-800 mb-3">Recent Transactions</div>
                       <div className="space-y-3">
                          {txList.slice(0, 4).map(tx => {
                              const status = getStatusInfo(tx);
                              return (
                                <div key={tx.transaction_id} onClick={() => openDetail(tx)} className="flex items-center justify-between bg-white p-3 rounded-xl border border-slate-100 shadow-sm cursor-pointer active:scale-95 transition-transform">
                                   <div className="flex items-center gap-3">
                                      <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-lg">🏪</div>
                                      <div>
                                         <div className="text-sm font-bold text-slate-800">{tx.transaction_id}</div>
                                         <div className={`text-[10px] font-bold ${status.color}`}>{status.label}</div>
                                      </div>
                                   </div>
                                   <div className="font-bold text-slate-800 text-sm">₹{tx.amount}</div>
                                </div>
                              )
                          })}
                       </div>
                    </div>
                 </div>
             );
         case 'history':
             return (
                 <div className="flex-1 bg-slate-50 flex flex-col">
                    <div className="bg-paytm-dark text-white pt-10 pb-4 px-4 shrink-0 font-bold text-lg relative">
                        Payment History
                    </div>
                    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 relative">
                       <Callout num="1" text="Paytm event emitted" show={showIntegration} positionClass="top-6 right-8" />
                       {txList.map(tx => {
                           const status = getStatusInfo(tx);
                           return (
                            <div key={tx.transaction_id} onClick={() => openDetail(tx)} className="flex items-center justify-between bg-white p-3 rounded-xl border border-slate-100 shadow-sm cursor-pointer active:scale-95 transition-transform">
                               <div className="flex items-center gap-3">
                                  <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-lg">🏪</div>
                                  <div>
                                     <div className="text-sm font-bold text-slate-800">{tx.transaction_id}</div>
                                     <div className="text-[10px] text-slate-500 mt-0.5">{tx.bank_status}</div>
                                  </div>
                               </div>
                               <div className="text-right">
                                  <div className="font-bold text-slate-800 text-sm">₹{tx.amount}</div>
                                  <div className={`text-[10px] font-bold mt-0.5 ${status.color}`}>{status.label}</div>
                               </div>
                            </div>
                           )
                       })}
                    </div>
                 </div>
             );
         case 'inbox':
             return (
                 <div className="flex-1 bg-slate-50 flex flex-col">
                    <div className="bg-paytm-dark text-white pt-10 pb-4 px-4 shrink-0 font-bold text-lg">Inbox</div>
                    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 relative">
                       <Callout num="4" text="Paytm UI updated" show={showIntegration} positionClass="top-6 left-6" />
                       {txList.filter(t => t.resolution_status === 'RESOLVED').map(tx => (
                           <div key={`notif-${tx.transaction_id}`} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex gap-3 cursor-pointer" onClick={() => openDetail(tx)}>
                              <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center shrink-0 mt-1">
                                 <Zap size={14} className="text-emerald-600"/>
                              </div>
                              <div>
                                 <div className="text-sm font-bold text-slate-800">Refund Processed Automatically</div>
                                 <div className="text-xs text-slate-600 mt-1 leading-snug">Good news! We detected a failure with {tx.transaction_id} and have automatically reversed ₹{tx.amount} to your account.</div>
                              </div>
                           </div>
                       ))}
                       <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex gap-3 opacity-50">
                           <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0 mt-1">
                              <Bell size={14} className="text-blue-600"/>
                           </div>
                           <div>
                              <div className="text-sm font-bold text-slate-800">Welcome to Paytm</div>
                              <div className="text-xs text-slate-600 mt-1 leading-snug">Experience lightning fast UPI payments safely and securely.</div>
                           </div>
                       </div>
                    </div>
                 </div>
             );
         case 'help':
             return (
                 <div className="flex-1 bg-slate-50 flex flex-col">
                    <div className="bg-paytm-dark text-white pt-10 pb-4 px-4 shrink-0 font-bold text-lg">24x7 Help</div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-6">
                        {txList.some(t => t.resolution_status === 'RESOLVED') && (
                          <div>
                              <div className="text-xs font-bold text-emerald-700 uppercase tracking-wider mb-3 flex items-center gap-1.5"><CheckCircle2 size={14}/> Resolved Automatically</div>
                              <div className="space-y-3 relative">
                                <Callout num="2" text="ZeroTouch decides" show={showIntegration} positionClass="-top-2 -right-2" />
                                {txList.filter(t => t.resolution_status === 'RESOLVED').map(tx => (
                                    <div key={`help-${tx.transaction_id}`} onClick={() => openDetail(tx)} className="bg-white p-3 rounded-xl border border-emerald-200 shadow-sm flex items-center justify-between cursor-pointer">
                                       <div>
                                          <div className="text-sm font-bold text-slate-800">{tx.transaction_id}</div>
                                          <div className="text-xs text-emerald-600 font-medium">Refunded ₹{tx.amount}</div>
                                       </div>
                                       <ChevronLeft size={16} className="text-slate-400 rotate-180" />
                                    </div>
                                ))}
                              </div>
                          </div>
                        )}

                        <div>
                           <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Other Topics</div>
                           <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                              {['Recent Payments', 'Refund Status', 'Profile Settings', 'Security'].map((topic, i) => (
                                  <div key={topic} className={`p-4 text-sm font-medium text-slate-700 flex justify-between items-center cursor-pointer hover:bg-slate-50 ${i !== 3 ? 'border-b border-slate-100' : ''}`}>
                                     {topic}
                                     <ChevronLeft size={16} className="text-slate-400 rotate-180" />
                                  </div>
                              ))}
                           </div>
                        </div>
                    </div>
                 </div>
             );
         default: return null;
     }
  };

  const renderMerchantContent = () => {
     return (
         <div className="flex-1 bg-slate-50 overflow-y-auto flex flex-col">
            <div className="bg-paytm-dark text-white pt-10 pb-4 px-4 shrink-0 relative">
               <Callout num="4" text="Paytm UI updated" show={showIntegration} positionClass="top-8 right-4" />
               <div className="font-bold text-lg">Business Dashboard</div>
               <div className="text-xs text-paytm-primary font-mono mt-0.5">PROTOTYPE MODE</div>
            </div>
            <div className="p-4 space-y-4">
               <div className="text-sm font-bold text-slate-800">Recent Settlements</div>
               {['S302', 'S306'].map(id => {
                   const tx = txList.find(t => t.transaction_id === id);
                   if (!tx) return null;
                   const isS302 = id === 'S302';
                   const isS306 = id === 'S306';
                   
                   return (
                       <div key={id} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm relative">
                          {isS302 && <Callout num="3" text="Action API called" show={showIntegration} positionClass="-top-2 -left-2" />}
                          {isS306 && <Callout num="2" text="ZeroTouch decides" show={showIntegration} positionClass="-top-2 -left-2" />}
                          
                          <div className="flex justify-between items-start mb-3">
                             <div>
                               <div className="font-bold text-slate-800 text-sm">Batch {tx.transaction_id}</div>
                               <div className="text-xs text-slate-400 mt-0.5">Expected: ₹{tx.amount.toLocaleString('en-IN')}</div>
                             </div>
                             <div className={`text-[10px] font-bold px-2 py-1 rounded uppercase ${tx.resolution_status === 'ESCALATED' ? 'bg-rose-100 text-rose-700' : tx.resolution_status === 'NO_ACTION' || tx.resolution_status === 'RESOLVED' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                               {tx.resolution_status === 'PENDING' ? 'Processing' : tx.resolution_status === 'NO_ACTION' ? 'Reconciled' : tx.resolution_status}
                             </div>
                          </div>
                          
                          {tx.resolution_status === 'PENDING' ? (
                             <div className="bg-slate-50 rounded p-2 text-xs text-slate-600 border border-slate-200 flex items-center gap-1.5 font-medium">
                                <Clock size={14} className="text-slate-400" /> Checking ledger mismatch...
                             </div>
                          ) : isS302 ? (
                             <div className="space-y-2">
                                <div className="bg-emerald-50 rounded p-2 text-xs text-emerald-800 border border-emerald-100 font-medium">
                                   Settlement shortfall auto-reconciled. No ticket raised.
                                </div>
                                <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded border border-slate-100 space-y-1.5">
                                   <div className="flex justify-between"><span>Expected:</span> <span className="font-medium text-slate-800">₹50,000</span></div>
                                   <div className="flex justify-between text-rose-600"><span>Platform Fee:</span> <span>-₹1,000</span></div>
                                   <div className="flex justify-between font-bold border-t border-slate-200 pt-1.5 text-slate-800"><span>Received:</span> <span>₹49,000</span></div>
                                </div>
                             </div>
                          ) : isS306 ? (
                             <div className="space-y-2">
                                <div className="bg-rose-50 rounded p-3 text-xs text-rose-800 border border-rose-100 font-medium flex items-start gap-2">
                                   <ShieldAlert size={16} className="shrink-0 mt-0.5" />
                                   <span>Settlement held. KYC document expired. Escalated to compliance team.</span>
                                </div>
                             </div>
                          ) : null}
                       </div>
                   );
               })}
            </div>
         </div>
     );
  };

  return (
    <div className="w-full h-full flex flex-col items-center">
      
      {/* Top Controls */}
      <div className="w-full max-w-[320px] mb-4 space-y-3">
         <div className="flex bg-slate-100 p-1 rounded-lg">
            <button 
              onClick={() => { setViewMode('consumer'); setSelectedTxId(null); setActiveTab('home'); }}
              className={`flex-1 text-xs font-bold py-2 rounded transition-all ${viewMode === 'consumer' ? 'bg-white shadow-sm text-paytm-dark' : 'text-slate-500 hover:text-slate-700'}`}
            >
              Consumer App
            </button>
            <button 
              onClick={() => { setViewMode('merchant'); setSelectedTxId(null); setActiveTab('home'); }}
              className={`flex-1 text-xs font-bold py-2 rounded transition-all ${viewMode === 'merchant' ? 'bg-white shadow-sm text-paytm-dark' : 'text-slate-500 hover:text-slate-700'}`}
            >
              Business Tab
            </button>
         </div>
         
         <label onClick={() => setShowIntegration(!showIntegration)} className="flex items-center justify-between cursor-pointer group bg-slate-50 px-3 py-2 rounded-lg border border-slate-200 hover:bg-fuchsia-50 hover:border-fuchsia-200 transition-colors">
            <span className="text-xs font-bold text-slate-600 group-hover:text-fuchsia-800">Show integration points</span>
            <div className={`w-8 h-4 rounded-full relative transition-colors ${showIntegration ? 'bg-fuchsia-500' : 'bg-slate-300'}`}>
               <div className={`w-3 h-3 bg-white rounded-full absolute top-0.5 transition-transform ${showIntegration ? 'translate-x-4' : 'translate-x-0.5'}`} />
            </div>
         </label>
      </div>

      {/* Phone Hardware Mockup */}
      <div className="w-[320px] h-[650px] bg-slate-900 rounded-[3rem] shadow-2xl border-[8px] border-slate-800 relative overflow-hidden flex flex-col shrink-0">
        {/* Notch */}
        <div className="absolute top-0 inset-x-0 h-6 flex justify-center z-20">
          <div className="w-32 h-6 bg-slate-800 rounded-b-3xl"></div>
        </div>

        {viewMode === 'consumer' ? (
            <>
              {renderConsumerContent()}
              {/* Bottom Tab Bar */}
              {!selectedTxId && (
                  <div className="bg-white border-t border-slate-100 flex justify-around items-center pt-3 pb-5 shrink-0 z-10">
                    {[{id: 'home', icon: HomeIcon, label: 'Home'}, {id: 'history', icon: List, label: 'History'}, {id: 'inbox', icon: Bell, label: 'Inbox'}, {id: 'help', icon: HelpCircle, label: 'Help'}].map(tab => (
                        <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex flex-col items-center gap-1.5 ${activeTab === tab.id ? 'text-paytm-primary' : 'text-slate-400'}`}>
                           <tab.icon size={20} className={activeTab === tab.id ? 'fill-paytm-primary/20' : ''} />
                           <span className="text-[10px] font-bold">{tab.label}</span>
                        </button>
                    ))}
                  </div>
              )}
            </>
        ) : (
            renderMerchantContent()
        )}

        {/* Home Indicator */}
        <div className="absolute bottom-1 inset-x-0 flex justify-center z-20">
          <div className="w-32 h-1 bg-slate-300/50 rounded-full"></div>
        </div>
      </div>
    </div>
  );
}
