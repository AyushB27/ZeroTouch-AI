import React, { useEffect, useState } from 'react';
import { Activity, Bot, BookOpen, CheckCircle2, CircleDollarSign, Clock3, FileText, RefreshCw, ShieldCheck, Ticket, Users } from 'lucide-react';
import { decideAccessRequest, getAdminEnterpriseOverview } from '../api';

const headings = {
  customers: ['customer_id','name','email','account_status'], employees: ['employee_id','name','department_id','role','status'],
  conversations: ['conversation_id','user_id','title','channel'], tasks: ['task_id','title','assigned_agent','status','priority'],
  tickets: ['ticket_id','customer_id','category','priority','status','summary'],
  transactions: ['transaction_id','amount','bank_status','network_status','resolution_status'],
  refunds: ['refund_id','transaction_id','amount','status','created_at'], agents: ['name','status','mode'],
  knowledge: ['document_id','title','category','content'], audit: ['timestamp','user_id','agent','tool','status','result_summary'],
  leads: ['lead_id','name','company','stage','score','consent_status'],
  campaigns: ['campaign_id','name','channel','status','audience','impressions','clicks','conversions','spend','revenue'],
  access_requests: ['request_id','employee_id','system_name','access_level','status','business_reason'],
};
const labels = { it_requests: 'IT tickets', access_requests: 'Access requests', onboarding: 'Onboarding plans', training: 'Training assignments' };
const metricTiles = [
  ['customers','Customers',Users,'text-blue-700','bg-blue-50'],['employees','Employees',Users,'text-violet-700','bg-violet-50'],
  ['conversations','Conversations',Activity,'text-cyan-700','bg-cyan-50'],['tasks','Tasks',CheckCircle2,'text-emerald-700','bg-emerald-50'],
  ['tickets','Support tickets',Ticket,'text-amber-700','bg-amber-50'],['transactions','Transactions',CircleDollarSign,'text-indigo-700','bg-indigo-50'],
  ['refunds','Refunds',RefreshCw,'text-rose-700','bg-rose-50'],['knowledge','Knowledge docs',BookOpen,'text-sky-700','bg-sky-50'],
];
const title = { overview:'Enterprise overview', customers:'Customers', employees:'Employees', conversations:'Conversations', tasks:'Tasks', tickets:'Support tickets', transactions:'Transactions', refunds:'Refunds', agents:'Agent registry', knowledge:'Knowledge library', audit:'Audit logs', settings:'Settings', leads:'Sales leads', campaigns:'Campaigns', access_requests:'Access requests' };

export default function AdminConsole({ view }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [decisionBusy, setDecisionBusy] = useState('');
  async function refresh() { setLoading(true); setError(''); try { setData(await getAdminEnterpriseOverview()); } catch (err) { setError(err.message || 'Could not load admin overview.'); } finally { setLoading(false); } }
  useEffect(() => { refresh(); }, []);

  const rows = view === 'agents' ? data?.agents : data?.records?.[view];
  const columns = headings[view] || [];
  const format = value => value == null ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value);
  return <main className="min-w-0 flex-1 overflow-y-auto bg-[#f7f9fc] p-5 sm:p-8">
    <div className="mx-auto max-w-7xl">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3"><div><div className="text-[10px] font-bold uppercase tracking-[.16em] text-blue-700">ZeroTouch · Admin</div><h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">{title[view] || 'Enterprise overview'}</h1><p className="mt-1 text-xs text-slate-500">Company operations, business records, agents, and audit activity.</p></div><button onClick={refresh} disabled={loading} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:border-blue-300 disabled:opacity-50"><RefreshCw size={14} className={loading?'animate-spin':''}/>Refresh</button></div>
      {error&&<div className="mb-5 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">{error}</div>}
      {loading&&!data?<div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">Loading enterprise records…</div>:null}
      {data&&view==='overview'&&<>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{metricTiles.map(([key,label,Icon,color,bg])=><div key={key} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className={`grid h-10 w-10 place-items-center rounded-xl ${color} ${bg}`}><Icon size={18}/></div><div><div className="text-[10px] font-semibold text-slate-500">{label}</div><div className="text-xl font-bold text-slate-900">{data.metrics[key] ?? 0}</div></div></div>)}</div>
        <div className="mt-4 grid gap-4 xl:grid-cols-[1.35fr_.65fr]">
          <section className="rounded-xl border border-slate-200 bg-white p-5"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-sm font-bold">Operational workload</h2><p className="mt-1 text-[10px] text-slate-500">Current records across departments</p></div><Activity size={17} className="text-blue-700"/></div><div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{['departments','expenses','it_requests','access_requests','onboarding','training','leads','campaigns','audit'].map(key=><div key={key} className="rounded-lg bg-slate-50 p-3"><div className="text-[10px] text-slate-500">{labels[key]||key[0].toUpperCase()+key.slice(1)}</div><div className="mt-1 text-lg font-bold text-slate-800">{data.metrics[key]||0}</div></div>)}</div></section>
          <section className="rounded-xl border border-slate-200 bg-white p-5"><div className="mb-3 flex items-center gap-2"><Bot size={17} className="text-blue-700"/><h2 className="text-sm font-bold">Agent registry</h2></div><div className="space-y-2">{(data.agents||[]).map(agent=><div key={agent.name} className="flex items-center justify-between border-b border-slate-100 pb-2 last:border-0"><span className="text-[11px] font-semibold text-slate-700">{agent.name}</span><span className="flex items-center gap-1 text-[9px] font-bold text-emerald-700"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500"/>{agent.status}</span></div>)}</div></section>
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2"><DataTable title="Recent tasks" rows={(data.records.tasks||[]).slice(0,6)} fields={headings.tasks}/><DataTable title="Recent audit activity" rows={(data.records.audit||[]).slice(0,6)} fields={headings.audit.slice(0,5)}/></div>
      </>}
      {data&&view==='access_requests'&&<section className="space-y-3">{(rows||[]).map(row=><article key={row.request_id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4"><div className="min-w-[220px] flex-1"><div className="text-xs font-bold text-slate-800">{row.system_name} · {row.access_level}</div><div className="mt-1 text-[10px] text-slate-500">Employee {row.employee_id} · {row.request_id}</div><p className="mt-2 text-[11px] text-slate-600">{row.business_reason}</p></div><div className="flex items-center gap-2"><span className={`rounded-full px-2.5 py-1 text-[9px] font-bold ${row.status==='PENDING_APPROVAL'?'bg-amber-50 text-amber-800':'bg-slate-100 text-slate-600'}`}>{row.status.replaceAll('_',' ')}</span>{row.status==='PENDING_APPROVAL'&&<><button disabled={decisionBusy===row.request_id} onClick={async()=>{setDecisionBusy(row.request_id);try{await decideAccessRequest(row.request_id,'APPROVE');await refresh()}catch(err){setError(err.message)}finally{setDecisionBusy('')}}} className="rounded-lg bg-emerald-700 px-3 py-2 text-[10px] font-bold text-white disabled:opacity-50">Approve</button><button disabled={decisionBusy===row.request_id} onClick={async()=>{setDecisionBusy(row.request_id);try{await decideAccessRequest(row.request_id,'REJECT');await refresh()}catch(err){setError(err.message)}finally{setDecisionBusy('')}}} className="rounded-lg border border-rose-200 px-3 py-2 text-[10px] font-bold text-rose-700 disabled:opacity-50">Reject</button></>}</div></article>)}</section>}
      {data&&headings[view]&&view!=='access_requests'&&<DataTable title={`${title[view]} · ${data.metrics[view] ?? 0} total`} rows={rows||[]} fields={columns} format={format}/>}
      {data&&view==='settings'&&<div className="grid max-w-3xl gap-4 md:grid-cols-2"><Setting label="AI provider" value={data.settings.grok_enabled?`Grok enabled · ${data.settings.grok_model}`:'Development fallback · no xAI key configured'} icon={Bot}/><Setting label="Database" value={data.settings.database} icon={FileText}/><Setting label="Data and actions" value="Role protected · audit logged · registered tools only" icon={ShieldCheck}/><Setting label="Approvals" value="Privileged access and high-risk financial actions remain gated" icon={Clock3}/></div>}
      {data&&['conversations','tasks','tickets','transactions','refunds','employees','customers','knowledge','audit','agents','leads','campaigns','access_requests'].includes(view)&&!rows?.length&&<div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">No records to display.</div>}
    </div>
  </main>;
}

function DataTable({title,rows,fields,format}) { return <section className="min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white"><div className="border-b border-slate-100 px-4 py-3"><h2 className="text-xs font-bold text-slate-800">{title}</h2></div><div className="overflow-auto"><table className="min-w-full text-left"><thead><tr className="bg-slate-50">{fields.map(field=><th key={field} className="whitespace-nowrap px-3 py-2 text-[9px] font-bold uppercase tracking-wider text-slate-400">{field.replaceAll('_',' ')}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{(rows||[]).slice(0,100).map((row,index)=><tr key={row.id||row.task_id||row.transaction_id||row.customer_id||row.employee_id||row.conversation_id||row.refund_id||row.ticket_id||row.audit_id||index} className="align-top hover:bg-slate-50">{fields.map(field=><td key={field} className="max-w-[320px] min-w-[80px] px-3 py-2.5 text-[10px] leading-4 text-slate-600"><span className="line-clamp-2 break-words">{format?format(row[field]):row[field] == null?'—':String(row[field])}</span></td>)}</tr>)}</tbody></table></div></section>; }
function Setting({label,value,icon:Icon}) { return <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4"><div className="grid h-9 w-9 place-items-center rounded-lg bg-blue-50 text-blue-700"><Icon size={17}/></div><div><div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{label}</div><div className="mt-1 text-xs font-semibold leading-5 text-slate-700">{value}</div></div></div>; }
