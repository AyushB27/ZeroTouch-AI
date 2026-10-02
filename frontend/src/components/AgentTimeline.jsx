import React from 'react';
import { CheckCircle2, XCircle, Loader2, Info, AlertTriangle } from 'lucide-react';

const TYPE_STYLES = {
  INVESTIGATION: { dot: 'bg-blue-500', text: 'text-slate-700' },
  POLICY: { dot: 'bg-violet-500', text: 'text-violet-700' },
  ACTION: { dot: 'bg-teal-500', text: 'text-teal-700' },
  VERIFICATION: { dot: 'bg-emerald-500', text: 'text-emerald-700' },
  NOTIFICATION: { dot: 'bg-sky-500', text: 'text-sky-700' },
  ESCALATION: { dot: 'bg-rose-500', text: 'text-rose-700' },
  ERROR: { dot: 'bg-red-500', text: 'text-red-700' },
};

function EventIcon({ status }) {
  if (status === 'SUCCESS') return <CheckCircle2 size={14} className="text-emerald-500 flex-shrink-0" />;
  if (status === 'FAILED') return <XCircle size={14} className="text-red-500 flex-shrink-0" />;
  return <Info size={14} className="text-slate-400 flex-shrink-0" />;
}

export default function AgentTimeline({ events, isRunning }) {
  return (
    <div className="h-full bg-white rounded-xl border border-slate-200 p-5 flex flex-col">
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-100">
        <h3 className="text-sm font-bold text-paytm-dark">Live Agent Trace</h3>
        {isRunning && (
          <div className="flex items-center gap-1.5 text-paytm-primary">
            <Loader2 size={14} className="animate-spin" />
            <span className="text-xs font-semibold">Running</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto pr-2">
        {events.length === 0 && !isRunning && (
          <div className="text-center py-12">
            <div className="text-slate-300 mb-2">
              <div className="w-10 h-10 rounded-full border-2 border-slate-200 mx-auto flex items-center justify-center">
                <div className="w-2.5 h-2.5 rounded-full bg-slate-300" />
              </div>
            </div>
            <div className="text-sm text-slate-400 font-medium">Awaiting event trigger...</div>
          </div>
        )}

        <div className="space-y-0">
          {events.map((event, i) => {
            const style = TYPE_STYLES[event.type] || TYPE_STYLES.INVESTIGATION;
            const isLast = i === events.length - 1;
            return (
              <div key={i} className="timeline-item flex items-start gap-4">
                <div className="flex flex-col items-center mt-1">
                  <div className={`w-2.5 h-2.5 rounded-full ${style.dot} flex-shrink-0 ring-4 ring-white relative z-10`} />
                  {!isLast && (
                    <div className="w-0.5 h-10 bg-slate-100 -mt-1 -mb-1" />
                  )}
                </div>
                <div className="flex-1 min-w-0 pb-4">
                  <div className="flex items-start gap-2">
                    <EventIcon status={event.status} />
                    <span className={`text-sm ${style.text} leading-snug font-medium`}>{event.message}</span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1 font-mono uppercase tracking-wider">
                    {event.type} • {new Date(event.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
