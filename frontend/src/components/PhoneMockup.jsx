import React from 'react';
import { Smartphone, CheckCircle2, AlertCircle, Clock, ChevronLeft, Bell } from 'lucide-react';

export default function PhoneMockup({ transaction, result }) {
  // Determine transaction state to display on the phone
  let statusColor = 'text-slate-800';
  let statusText = 'Paid Successfully';
  let amountPrefix = '-';
  
  if (transaction) {
    if (transaction.resolution_status === 'RESOLVED') {
      statusColor = 'text-paytm-green';
      statusText = 'Refund Successful';
      amountPrefix = '+';
    } else if (transaction.resolution_status === 'ESCALATED' || transaction.resolution_status === 'PENDING') {
      statusColor = 'text-paytm-yellow';
      statusText = 'Payment Pending / Failed';
    }
  }

  return (
    <div className="flex flex-col items-center">
      {/* Phone Hardware Mockup */}
      <div className="w-[320px] h-[650px] bg-white rounded-[3rem] shadow-2xl border-[8px] border-slate-800 relative overflow-hidden flex flex-col">
        
        {/* Notch */}
        <div className="absolute top-0 inset-x-0 h-6 flex justify-center z-20">
          <div className="w-32 h-6 bg-slate-800 rounded-b-3xl"></div>
        </div>

        {/* App Header */}
        <div className="bg-paytm-dark text-white pt-10 pb-4 px-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-2">
            <ChevronLeft size={24} />
            <span className="font-semibold">Payment Details</span>
          </div>
          <div className="font-bold tracking-tight text-paytm-primary">Paytm</div>
        </div>

        {/* App Content */}
        {transaction ? (
          <div className="flex-1 bg-slate-50 flex flex-col">
            
            {/* Top Card */}
            <div className="bg-white p-6 flex flex-col items-center border-b border-slate-100">
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-3">
                <span className="text-2xl">🏪</span>
              </div>
              <h2 className="text-lg font-semibold text-slate-800">Fresh Mart Groceries</h2>
              <div className={`text-3xl font-bold mt-2 ${statusColor}`}>
                {amountPrefix}₹{transaction.amount.toLocaleString('en-IN')}
              </div>
              <div className="flex items-center gap-1.5 mt-2 text-sm font-medium text-slate-500">
                {transaction.resolution_status === 'RESOLVED' ? (
                  <><CheckCircle2 size={16} className="text-paytm-green" /> {statusText}</>
                ) : transaction.resolution_status === 'NO_ACTION' ? (
                  <><CheckCircle2 size={16} className="text-paytm-green" /> Paid Successfully</>
                ) : (
                  <><Clock size={16} className="text-paytm-yellow" /> {statusText}</>
                )}
              </div>
            </div>

            {/* Timeline */}
            <div className="p-6 flex-1">
              <div className="text-sm font-bold text-slate-800 mb-4">Payment Timeline</div>
              
              <div className="relative pl-4 border-l-2 border-slate-200 space-y-6">
                
                {/* Step 1: Initiated */}
                <div className="relative">
                  <div className="absolute -left-[21px] w-3 h-3 rounded-full bg-paytm-primary ring-4 ring-white"></div>
                  <div className="text-sm font-semibold text-slate-800">Payment Initiated</div>
                  <div className="text-xs text-slate-500">From HDFC Bank **** 1234</div>
                </div>

                {/* Step 2: Bank Debited */}
                {transaction.bank_status === 'DEBITED' && (
                  <div className="relative">
                    <div className="absolute -left-[21px] w-3 h-3 rounded-full bg-paytm-primary ring-4 ring-white"></div>
                    <div className="text-sm font-semibold text-slate-800">Bank Debited</div>
                    <div className="text-xs text-slate-500">Money left your account</div>
                  </div>
                )}

                {/* Step 3: Resolution Status */}
                {transaction.resolution_status === 'RESOLVED' && (
                  <div className="relative">
                    <div className="absolute -left-[21px] w-3 h-3 rounded-full bg-paytm-green ring-4 ring-white"></div>
                    <div className="text-sm font-semibold text-paytm-green">Refund Processed</div>
                    <div className="text-xs text-slate-500">Refund initiated automatically</div>
                  </div>
                )}
                {transaction.resolution_status === 'ESCALATED' && (
                  <div className="relative">
                    <div className="absolute -left-[21px] w-3 h-3 rounded-full bg-paytm-yellow ring-4 ring-white"></div>
                    <div className="text-sm font-semibold text-paytm-yellow">Under Review</div>
                    <div className="text-xs text-slate-500">We are actively investigating this</div>
                  </div>
                )}
              </div>
            </div>

            {/* Push Notification Overlay */}
            {result?.notification_sent && (
              <div className="absolute bottom-6 left-4 right-4 bg-white rounded-xl shadow-lg border border-slate-100 p-4 animate-in slide-in-from-bottom-4">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded bg-paytm-primary/10 flex items-center justify-center flex-shrink-0">
                    <Bell size={16} className="text-paytm-primary" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-800">Paytm Updates</div>
                    <div className="text-xs text-slate-600 mt-1 leading-snug">
                      Your refund of ₹{transaction.amount} has been initiated successfully. No action needed!
                    </div>
                  </div>
                </div>
              </div>
            )}

          </div>
        ) : (
          <div className="flex-1 bg-slate-50 flex items-center justify-center text-slate-400 p-6 text-center">
            Select a transaction to view in the Paytm app
          </div>
        )}

        {/* Home Indicator */}
        <div className="absolute bottom-2 inset-x-0 flex justify-center z-20">
          <div className="w-32 h-1 bg-slate-300 rounded-full"></div>
        </div>
      </div>
    </div>
  );
}
