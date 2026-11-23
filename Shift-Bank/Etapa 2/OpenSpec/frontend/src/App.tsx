import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { accountNumberValid, routingNumberValid, scheduleActionAllowed, statusLabel, transferLabel, validateLimits, validateMoney, validateRecipient } from './validation.mjs';
import { startRefreshPolling } from './refreshPolling.mjs';
import './App.css';

type Account = { id: string; name: string; balance: string };
type Beneficiary = { id: string; name: string; bank_name: string; routing_number: string; account_number: string };
type HistoryItem = { id: string; source_account_id: string; source_account_name: string; destination_account_id?: string | null; destination_account_name: string; recipient_name?: string; amount: string; timestamp: string; status: string; transfer_type?: string; failure_reason?: string | null; settled_at?: string | null; schedule_id?: string };
type Schedule = { id: string; transfer_type: 'internal' | 'ach'; source_account_id: string; destination_account_id?: string; recipient_name?: string; bank_name?: string; amount: string; frequency: string; status: string; next_execution_at: string; executions: Array<{ id: string; status: string; failure_reason?: string }> };
type Limits = { per_transfer: string; daily: string; daily_usage: string };
type Tab = 'overview' | 'transfer' | 'beneficiaries' | 'limits' | 'recurring';
type PendingMfa = { kind: 'internal' | 'ach' | 'schedule'; id: string; amount: string; destination: string };

const emptyRecipient = { name: '', bank_name: '', routing_number: '', account_number: '' };
async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } });
  const body = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error((body as { detail?: string })?.detail || `Request failed (${response.status})`);
  return body as T;
}
const json = (method: string, body?: unknown): RequestInit => ({ method, body: body === undefined ? undefined : JSON.stringify(body) });
const formatCOP = (value: string | number) => {
  const [whole = '0', fraction = '00'] = String(value).split('.');
  try {
    const formatted = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(BigInt(whole));
    return `${formatted},${(fraction + '00').slice(0, 2)} COP`;
  } catch { return `${String(value)} COP`; }
};
const localDate = (value: string) => new Date(value).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }) + ' UTC';

export default function App() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [limits, setLimits] = useState<Limits>({ per_transfer: '5000000.00', daily: '10000000.00', daily_usage: '0.00' });
  const [limitForm, setLimitForm] = useState({ per_transfer: '', daily: '' });
  const [tab, setTab] = useState<Tab>('overview');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [pendingMfa, setPendingMfa] = useState<PendingMfa | null>(null);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaSeconds, setMfaSeconds] = useState(300);
  const [filter, setFilter] = useState('All');

  const [transferType, setTransferType] = useState<'internal' | 'ach'>('internal');
  const [sourceId, setSourceId] = useState('acc_checking');
  const [destinationId, setDestinationId] = useState('acc_savings');
  const [transferAmount, setTransferAmount] = useState('');
  const [recipientChoice, setRecipientChoice] = useState('new');
  const [recipientForm, setRecipientForm] = useState(emptyRecipient);
  const [saveRecipient, setSaveRecipient] = useState(false);

  const [beneficiaryForm, setBeneficiaryForm] = useState(emptyRecipient);
  const [editingBeneficiary, setEditingBeneficiary] = useState<string | null>(null);

  const [scheduleType, setScheduleType] = useState<'internal' | 'ach'>('internal');
  const [scheduleSource, setScheduleSource] = useState('acc_checking');
  const [scheduleDestination, setScheduleDestination] = useState('acc_savings');
  const [scheduleAmount, setScheduleAmount] = useState('');
  const [frequency, setFrequency] = useState('daily');
  const [startDate, setStartDate] = useState('');
  const [scheduleRecipientChoice, setScheduleRecipientChoice] = useState('new');
  const [scheduleRecipient, setScheduleRecipient] = useState(emptyRecipient);

  async function refresh(syncLimitForm = false) {
    const [a, h, b, l, s] = await Promise.all([
      api<Account[]>('/api/accounts'), api<HistoryItem[]>('/api/history'), api<Beneficiary[]>('/api/beneficiaries'),
      api<Limits>('/api/limits'), api<Schedule[]>('/api/recurring-schedules')
    ]);
    setAccounts(a); setHistory(h); setBeneficiaries(b); setLimits(l);
    if (syncLimitForm) setLimitForm({ per_transfer: l.per_transfer, daily: l.daily });
    setSchedules(s);
    if (a.length > 1 && !a.some(account => account.id === sourceId)) setSourceId(a[0].id);
  }
  useEffect(() => { refresh(true).catch(e => setError(e.message)); }, []);
  useEffect(() => startRefreshPolling(() => refresh().catch(e => setError(e.message))), []);
  useEffect(() => {
    if (!pendingMfa || mfaSeconds <= 0) return;
    const timer = window.setTimeout(() => setMfaSeconds(value => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [pendingMfa, mfaSeconds]);

  function startMfa(kind: PendingMfa['kind'], id: string, amount: string, destination: string) {
    setPendingMfa({ kind, id, amount, destination }); setMfaCode(''); setMfaSeconds(300); setError('');
  }
  async function confirmMfa(event: FormEvent) {
    event.preventDefault(); if (!pendingMfa || mfaCode.length !== 6) return;
    setBusy(true); setError('');
    try {
      const endpoint = pendingMfa.kind === 'internal' ? `/api/transfers/${pendingMfa.id}/confirm` : pendingMfa.kind === 'ach' ? `/api/ach-transfers/${pendingMfa.id}/confirm` : `/api/recurring-schedules/${pendingMfa.id}/confirm`;
      await api(endpoint, json('POST', { code: mfaCode }));
      setPendingMfa(null); setNotice(pendingMfa.kind === 'schedule' ? 'Recurring schedule authorized and active.' : 'Transfer authorized and accepted.');
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'MFA confirmation failed');
      if ((e instanceof Error ? e.message : '').toLowerCase().includes('first execution time has passed')) setPendingMfa(null);
    } finally { setBusy(false); }
  }

  async function submitTransfer(event: FormEvent) {
    event.preventDefault(); setError(''); setNotice('');
    if (!validateMoney(transferAmount)) return setError('Enter a positive amount with at most two decimal places.');
    if (transferType === 'internal' && sourceId === destinationId) return setError('Choose different source and destination accounts.');
    const selected = beneficiaries.find(b => b.id === recipientChoice);
    const rec = selected ? { beneficiary_id: selected.id } : recipientForm;
    if (transferType === 'ach' && !selected && validateRecipient(recipientForm)) return setError(validateRecipient(recipientForm));
    setBusy(true);
    try {
      if (transferType === 'internal') {
        const result = await api<{ status: string; transfer_id?: string }>('/api/transfers', json('POST', { source_account_id: sourceId, destination_account_id: destinationId, amount: transferAmount }));
        if (result.status === 'PENDING_MFA' && result.transfer_id) startMfa('internal', result.transfer_id, transferAmount, accounts.find(a => a.id === destinationId)?.name || 'Internal account');
        else { setNotice('Internal transfer completed.'); setTransferAmount(''); await refresh(); }
      } else {
        const result = await api<{ status: string; transfer_id: string; mfa_required: boolean }>('/api/ach-transfers', json('POST', { source_account_id: sourceId, amount: transferAmount, ...rec, save_recipient: saveRecipient && !selected }));
        if (result.mfa_required) startMfa('ach', result.transfer_id, transferAmount, selected?.name || recipientForm.name);
        else { setNotice('ACH transfer accepted and shown as pending.'); setTransferAmount(''); setSaveRecipient(false); await refresh(); }
      }
    } catch (e) { setError(e instanceof Error ? e.message : 'Transfer could not be submitted'); }
    finally { setBusy(false); }
  }

  async function saveLimits(event: FormEvent) {
    event.preventDefault(); setError('');
    if (!validateLimits(limitForm.per_transfer, limitForm.daily)) return setError('Both limits must be positive values with at most two decimal places.');
    setBusy(true);
    try { await api('/api/limits', json('PUT', limitForm)); await refresh(true); setNotice('Transfer limits saved.'); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not save limits'); }
    finally { setBusy(false); }
  }

  async function saveBeneficiary(event: FormEvent) {
    event.preventDefault(); setError('');
    if (validateRecipient(beneficiaryForm)) return setError(validateRecipient(beneficiaryForm));
    setBusy(true);
    try {
      await api(editingBeneficiary ? `/api/beneficiaries/${editingBeneficiary}` : '/api/beneficiaries', json(editingBeneficiary ? 'PUT' : 'POST', beneficiaryForm));
      setBeneficiaryForm(emptyRecipient); setEditingBeneficiary(null); await refresh(); setNotice('Beneficiary saved.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not save beneficiary'); }
    finally { setBusy(false); }
  }
  async function removeBeneficiary(id: string) {
    setError(''); try { await api(`/api/beneficiaries/${id}`, json('DELETE')); await refresh(); setNotice('Beneficiary removed. Historical recipient details are preserved.'); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not remove beneficiary'); }
  }

  async function createSchedule(event: FormEvent) {
    event.preventDefault(); setError('');
    if (!validateMoney(scheduleAmount)) return setError('Enter a positive amount with at most two decimal places.');
    const selected = beneficiaries.find(b => b.id === scheduleRecipientChoice);
    if (scheduleType === 'ach' && !selected && validateRecipient(scheduleRecipient)) return setError(validateRecipient(scheduleRecipient));
    setBusy(true);
    try {
      const result = await api<{ schedule_id: string; status: string }>('/api/recurring-schedules', json('POST', {
        transfer_type: scheduleType, source_account_id: scheduleSource, amount: scheduleAmount, frequency, start_date: startDate || null,
        ...(scheduleType === 'internal' ? { destination_account_id: scheduleDestination } : selected ? { beneficiary_id: selected.id } : scheduleRecipient)
      }));
      if (result.status === 'PENDING_MFA') startMfa('schedule', result.schedule_id, scheduleAmount, 'Recurring payment');
      else { setNotice('Recurring schedule created. The next occurrence is shown in UTC.'); setScheduleAmount(''); await refresh(); }
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not create schedule'); }
    finally { setBusy(false); }
  }
  async function scheduleAction(id: string, action: 'pause' | 'resume' | 'cancel') {
    setError(''); try { await api(`/api/recurring-schedules/${id}/${action}`, json('POST')); await refresh(); setNotice(`Schedule ${action}d.`); }
    catch (e) { setError(e instanceof Error ? e.message : `Could not ${action} schedule`); }
  }

  const filteredHistory = history.filter(item => filter === 'All' || item.source_account_id === filter || item.destination_account_id === filter);
  const nav: Array<[Tab, string]> = [['overview','Accounts & history'],['transfer','Transfer'],['beneficiaries','Beneficiaries'],['limits','Transfer limits'],['recurring','Recurring payments']];
  const accountSelect = (value: string, onChange: (value: string) => void, id: string) => <select id={id} value={value} onChange={e => onChange(e.target.value)} className="form-control">{accounts.map(a => <option key={a.id} value={a.id}>{a.name} · {formatCOP(a.balance)}</option>)}</select>;
  const recipientFields = (value: typeof emptyRecipient, setter: (value: typeof emptyRecipient) => void, prefix: string) => <>
    <div className="form-group"><label htmlFor={`${prefix}-name`}>Beneficiary name</label><input id={`${prefix}-name`} className="form-control" value={value.name} onChange={e => setter({...value,name:e.target.value})} required /></div>
    <div className="form-group"><label htmlFor={`${prefix}-bank`}>Bank name</label><input id={`${prefix}-bank`} className="form-control" value={value.bank_name} onChange={e => setter({...value,bank_name:e.target.value})} required /></div>
    <div className="form-group"><label htmlFor={`${prefix}-routing`}>Routing number</label><input id={`${prefix}-routing`} className="form-control" inputMode="numeric" value={value.routing_number} onChange={e => setter({...value,routing_number:e.target.value.replace(/\D/g,'').slice(0,9)})} aria-invalid={value.routing_number.length>0&&!routingNumberValid(value.routing_number)} required /><small>{value.routing_number.length>0&&!routingNumberValid(value.routing_number)?'Enter exactly 9 numeric digits.':'Exactly 9 digits'}</small></div>
    <div className="form-group"><label htmlFor={`${prefix}-account`}>Account number</label><input id={`${prefix}-account`} className="form-control" inputMode="numeric" value={value.account_number} onChange={e => setter({...value,account_number:e.target.value.replace(/\D/g,'').slice(0,17)})} aria-invalid={value.account_number.length>0&&!accountNumberValid(value.account_number)} required /><small>{value.account_number.length>0&&!accountNumberValid(value.account_number)?'Enter 4–17 numeric digits.':'4–17 digits'}</small></div>
  </>;

  return <main className="app-container">
    <header className="header-card"><div className="header-brand"><h1>Shift Bank</h1><p>Mock banking · COP</p></div><div className="user-profile"><div className="user-name">Jane Doe</div><div className="user-id">ID: usr_101</div></div></header>
    <nav aria-label="Banking sections" className="stage2-nav">{nav.map(([key,label])=><button key={key} className={`filter-tab ${tab===key?'active':''}`} onClick={()=>{setTab(key);setError('');setNotice('')}}>{label}</button>)}</nav>
    {error&&<div role="alert" className="alert alert-error">{error}<button onClick={()=>setError('')}>Dismiss</button></div>}
    {notice&&<div role="status" className="alert alert-success">{notice}<button onClick={()=>setNotice('')}>Dismiss</button></div>}
    <section className="accounts-grid">{accounts.map(a=><article key={a.id} className={`account-card ${a.id==='acc_checking'?'account-checking':'account-savings'}`}><div><div className="account-type">{a.name}</div><div className="account-id-label">{a.id}</div></div><strong className="account-balance">{formatCOP(a.balance)}</strong></article>)}</section>

    {tab==='overview'&&<section className="card"><div className="history-header"><h2 className="history-title">Transaction history</h2><select aria-label="Account history filter" value={filter} onChange={e=>setFilter(e.target.value)} className="form-control"><option value="All">All accounts</option>{accounts.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select></div>
      {filteredHistory.length===0?<p>No transactions yet.</p>:<div className="ledger-list">{filteredHistory.map(item=><article className="ledger-item" key={item.id}><div className="tx-details"><strong>{transferLabel(item.transfer_type)}</strong><div className="tx-accounts">{item.source_account_name} → {item.destination_account_name||item.recipient_name||'External recipient'}</div><small>{localDate(item.timestamp)} · Ref {item.id}</small>{item.failure_reason&&<div role="alert">{item.failure_reason}</div>}{item.settled_at&&<small>Settled {localDate(item.settled_at)}</small>}</div><div className="ledger-right"><strong>{formatCOP(item.amount)}</strong><span className={`badge badge-${item.status.toLowerCase().replace('_','-')}`}>{statusLabel(item.status)}</span></div></article>)}</div>}</section>}

    {tab==='transfer'&&<section className="card"><h2>Transfer funds</h2><p>Choose an internal transfer or simulated external ACH transfer.</p><form onSubmit={submitTransfer}>
      <div className="form-group"><label htmlFor="transfer-type">Transfer type</label><select id="transfer-type" className="form-control" value={transferType} onChange={e=>setTransferType(e.target.value as 'internal'|'ach')}><option value="internal">Internal · owned accounts</option><option value="ach">External ACH · simulated</option></select></div>
      <div className="form-group"><label htmlFor="transfer-source">Source account</label>{accountSelect(sourceId,setSourceId,'transfer-source')}</div>
      {transferType==='internal'?<div className="form-group"><label htmlFor="transfer-destination">Destination account</label>{accountSelect(destinationId,setDestinationId,'transfer-destination')}</div>:<>
        <div className="form-group"><label htmlFor="recipient-choice">Recipient</label><select id="recipient-choice" className="form-control" value={recipientChoice} onChange={e=>setRecipientChoice(e.target.value)}><option value="new">Enter new recipient</option>{beneficiaries.map(b=><option key={b.id} value={b.id}>{b.name} · {b.bank_name}</option>)}</select></div>
        {recipientChoice==='new'&&<>{recipientFields(recipientForm,setRecipientForm,'transfer-recipient')}<label><input type="checkbox" checked={saveRecipient} onChange={e=>setSaveRecipient(e.target.checked)} /> Save this beneficiary for later</label></>}
      </>}
      <div className="form-group"><label htmlFor="transfer-amount">Amount (COP)</label><input id="transfer-amount" className="form-control" inputMode="decimal" value={transferAmount} onChange={e=>setTransferAmount(e.target.value)} aria-invalid={transferAmount!==''&&!validateMoney(transferAmount)} required/>{transferAmount!==''&&!validateMoney(transferAmount)&&<small role="alert">Enter a positive value with no more than two decimal places.</small>}<small>Per-transfer limit: {formatCOP(limits.per_transfer)} · Daily usage: {formatCOP(limits.daily_usage)} / {formatCOP(limits.daily)}</small></div>
      <button className="btn btn-primary" disabled={busy||!validateMoney(transferAmount)}>{busy?'Processing…':'Submit transfer'}</button></form></section>}

    {tab==='limits'&&<section className="card"><h2>Transfer limits</h2><p>Limits apply to internal, ACH, and recurring transfers across your accounts. Daily usage is calculated in UTC.</p><form onSubmit={saveLimits}>
      <div className="form-group"><label htmlFor="per-transfer-limit">Maximum per transfer (COP)</label><input id="per-transfer-limit" className="form-control" inputMode="decimal" value={limitForm.per_transfer} onChange={e=>setLimitForm({...limitForm,per_transfer:e.target.value})} required />{limitForm.per_transfer!==''&&!validateMoney(limitForm.per_transfer)&&<small role="alert">Limit must be positive and use at most two decimal places.</small>}</div>
      <div className="form-group"><label htmlFor="daily-limit">Maximum per UTC day (COP)</label><input id="daily-limit" className="form-control" inputMode="decimal" value={limitForm.daily} onChange={e=>setLimitForm({...limitForm,daily:e.target.value})} required />{limitForm.daily!==''&&!validateMoney(limitForm.daily)&&<small role="alert">Limit must be positive and use at most two decimal places.</small>}</div>
      <p>Used today (UTC): {formatCOP(limits.daily_usage)}</p><button className="btn btn-primary" disabled={busy||!validateLimits(limitForm.per_transfer,limitForm.daily)}>Save limits</button>
    </form></section>}

    {tab==='beneficiaries'&&<section className="card"><h2>Saved beneficiaries</h2><form onSubmit={saveBeneficiary}><h3>{editingBeneficiary?'Update beneficiary':'Add beneficiary'}</h3>{recipientFields(beneficiaryForm,setBeneficiaryForm,'beneficiary')}<button className="btn btn-primary" disabled={busy||!routingNumberValid(beneficiaryForm.routing_number)||!accountNumberValid(beneficiaryForm.account_number)}>{editingBeneficiary?'Save changes':'Create beneficiary'}</button>{editingBeneficiary&&<button type="button" className="btn btn-secondary" onClick={()=>{setEditingBeneficiary(null);setBeneficiaryForm(emptyRecipient)}}>Stop editing</button>}</form><div className="ledger-list">{beneficiaries.map(b=><article className="ledger-item" key={b.id}><div><strong>{b.name}</strong><div>{b.bank_name} · routing {b.routing_number} · account {b.account_number}</div></div><div><button className="btn btn-secondary" onClick={()=>{setEditingBeneficiary(b.id);setBeneficiaryForm({name:b.name,bank_name:b.bank_name,routing_number:b.routing_number,account_number:b.account_number})}}>Edit</button><button className="btn btn-secondary" onClick={()=>removeBeneficiary(b.id)}>Delete</button></div></article>)}</div></section>}

    {tab==='recurring'&&<section className="card"><h2>Recurring payments</h2><p>Frequencies use fixed intervals of 1, 7, or 30 days. Start dates and next runs use UTC.</p><form onSubmit={createSchedule}>
      <div className="form-group"><label htmlFor="schedule-type">Transfer type</label><select id="schedule-type" className="form-control" value={scheduleType} onChange={e=>setScheduleType(e.target.value as 'internal'|'ach')}><option value="internal">Internal</option><option value="ach">External ACH</option></select></div>
      <div className="form-group"><label htmlFor="schedule-source">Source account</label>{accountSelect(scheduleSource,setScheduleSource,'schedule-source')}</div>
      {scheduleType==='internal'?<div className="form-group"><label htmlFor="schedule-destination">Destination account</label>{accountSelect(scheduleDestination,setScheduleDestination,'schedule-destination')}</div>:<>
        <div className="form-group"><label htmlFor="schedule-recipient-choice">Recipient</label><select id="schedule-recipient-choice" className="form-control" value={scheduleRecipientChoice} onChange={e=>setScheduleRecipientChoice(e.target.value)}><option value="new">Enter recipient details</option>{beneficiaries.map(b=><option key={b.id} value={b.id}>{b.name} · {b.bank_name}</option>)}</select></div>
        {scheduleRecipientChoice==='new'&&recipientFields(scheduleRecipient,setScheduleRecipient,'schedule-recipient')}
      </>}
      <div className="form-group"><label htmlFor="schedule-amount">Amount (COP)</label><input id="schedule-amount" className="form-control" inputMode="decimal" value={scheduleAmount} onChange={e=>setScheduleAmount(e.target.value)} required />{scheduleAmount!==''&&!validateMoney(scheduleAmount)&&<small role="alert">Enter a positive value with no more than two decimal places.</small>}</div>
      <div className="form-group"><label htmlFor="frequency">Frequency</label><select id="frequency" className="form-control" value={frequency} onChange={e=>setFrequency(e.target.value)}><option value="daily">Daily · every 1 day</option><option value="weekly">Weekly · every 7 days</option><option value="monthly">Monthly · every 30 days</option></select></div>
      <div className="form-group"><label htmlFor="start-date">First execution date (optional, 00:00 UTC)</label><input id="start-date" type="date" className="form-control" value={startDate} onChange={e=>setStartDate(e.target.value)} /></div>
      <button className="btn btn-primary" disabled={busy||!validateMoney(scheduleAmount)}>Create schedule</button>
    </form>
    <h3>Your schedules</h3>{schedules.length===0?<p>No recurring schedules yet.</p>:<div className="ledger-list">{schedules.map(s=><article className="ledger-item schedule-row" key={s.id}><div><strong>{transferLabel(`recurring_${s.transfer_type}`)} · {formatCOP(s.amount)}</strong><div>{s.source_account_id} → {s.destination_account_id||s.recipient_name} · {s.frequency}</div><div>Status: {statusLabel(s.status)} · Next: {s.next_execution_at?localDate(s.next_execution_at):'—'}</div>{s.executions?.map(o=><small className="execution-row" key={o.id}>Occurrence {statusLabel(o.status)}{o.failure_reason?`: ${o.failure_reason}`:''}</small>)}</div><div>{(['pause','resume','cancel'] as const).filter(action=>scheduleActionAllowed(s.status,action)).map(action=><button key={action} className="btn btn-secondary" onClick={()=>scheduleAction(s.id,action)}>{action}</button>)}</div></article>)}</div>}</section>}

    {pendingMfa&&<div className="modal-overlay open" role="dialog" aria-modal="true" aria-labelledby="mfa-title"><div className="modal-window"><h2 id="mfa-title">MFA authorization</h2><p>{pendingMfa.kind==='schedule'?'Authorize this recurring schedule. Future executions will recheck current balance and limits.':`Authorize ${pendingMfa.kind==='ach'?'external ACH':'internal'} transfer of ${formatCOP(pendingMfa.amount)} to ${pendingMfa.destination}.`}</p><p>Code expires in {Math.floor(mfaSeconds/60)}:{String(mfaSeconds%60).padStart(2,'0')}. Existing mock code: 123456.</p><form onSubmit={confirmMfa}><label htmlFor="mfa-code">Six-digit code</label><input id="mfa-code" className="form-control" inputMode="numeric" maxLength={6} value={mfaCode} onChange={e=>setMfaCode(e.target.value.replace(/\D/g,'').slice(0,6))} required/><div className="modal-actions"><button type="button" className="btn btn-secondary" onClick={()=>setPendingMfa(null)}>Cancel</button><button className="btn btn-primary" disabled={busy||mfaCode.length!==6||mfaSeconds===0}>{busy?'Verifying…':'Confirm'}</button></div></form>{mfaSeconds===0&&<p role="alert">The five-minute authorization window has expired.</p>}</div></div>}
  </main>;
}
