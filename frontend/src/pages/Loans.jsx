import { useCallback, useEffect, useState } from 'react';
import { loanService } from '../api/loanService.js';
import { formatINR } from '../components/CategoryPill.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';
import Spinner from '../components/Spinner.jsx';

const TYPES = [
  { value: 'home_loan',      label: 'Home loan' },
  { value: 'car_loan',       label: 'Car loan' },
  { value: 'personal_loan',  label: 'Personal loan' },
  { value: 'education_loan', label: 'Education loan' },
  { value: 'credit_card',    label: 'Credit card' },
  { value: 'other',          label: 'Other' },
];

const EMPTY_FORM = {
  name: '', liability_type: 'home_loan', principal_amount: '',
  interest_rate_annual: '', tenure_months: '', start_date: '',
};

/** Client-side mirror of the server's EMI formula — lets the user see the EMI
 *  update as they type, before the loan is ever saved. The server recomputes it
 *  on create regardless; this is a preview, not the source of truth. */
function previewEmi({ principal_amount, interest_rate_annual, tenure_months }) {
  const p = Number(principal_amount), rate = Number(interest_rate_annual), n = Number(tenure_months);
  if (!p || !n) return null;
  if (!rate) return p / n;
  const r = rate / 12 / 100;
  return (p * r * (1 + r) ** n) / ((1 + r) ** n - 1);
}

export default function Loans() {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setLoans(await loanService.list()); }
    catch (err) { setError(err.message || 'Could not load loans.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e) => {
    e.preventDefault();
    setSubmitting(true); setError('');
    try {
      await loanService.add({
        name: form.name.trim(),
        liability_type: form.liability_type,
        principal_amount: Number(form.principal_amount),
        interest_rate_annual: Number(form.interest_rate_annual),
        tenure_months: Number(form.tenure_months),
        start_date: form.start_date,
      });
      setForm(EMPTY_FORM);
      await load();
    } catch (err) { setError(err.message); }
    finally { setSubmitting(false); }
  };

  const handleRemove = async (id) => {
    try { await loanService.remove(id); await load(); }
    catch (err) { setError(err.message); }
  };

  const emi = previewEmi(form);
  const totalEmi = loans.reduce((sum, l) => sum + (l.months_remaining > 0 ? l.emi_amount : 0), 0);
  const totalOutstanding = loans.reduce((sum, l) => sum + l.outstanding_balance, 0);

  if (loading) {
    return <div className="flex h-full items-center justify-center p-10"><Spinner size={28} className="text-accent-text"/></div>;
  }

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-ink">Loans &amp; EMIs</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Reducing-balance amortization — outstanding balance is recomputed from the loan terms on every read.
        </p>
      </div>

      <ErrorBanner message={error} />

      {/* ── Totals ───────────────────────────────────────────────────────── */}
      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="card p-4">
          <p className="text-[11px] text-slate-500">Active loans</p>
          <p className="font-mono text-xl font-medium tabular-nums text-ink mt-1">{loans.length}</p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] text-slate-500">Monthly EMI outgo</p>
          <p className="font-mono text-xl font-medium tabular-nums text-ink mt-1">{formatINR(totalEmi)}</p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] text-slate-500">Total outstanding</p>
          <p className="font-mono text-xl font-medium tabular-nums text-debit mt-1">{formatINR(totalOutstanding)}</p>
        </div>
      </div>

      {/* ── Add loan ─────────────────────────────────────────────────────── */}
      <form onSubmit={handleAdd} className="card mb-5 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Name</label>
            <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="HDFC Home Loan" className="input-field text-sm w-40"/>
          </div>
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Type</label>
            <select value={form.liability_type} onChange={e => setForm(f => ({ ...f, liability_type: e.target.value }))}
              className="input-field text-sm w-36">
              {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Principal</label>
            <input required type="number" min="1" value={form.principal_amount}
              onChange={e => setForm(f => ({ ...f, principal_amount: e.target.value }))}
              className="input-field text-sm w-32"/>
          </div>
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Rate % p.a.</label>
            <input required type="number" min="0" max="50" step="0.01" value={form.interest_rate_annual}
              onChange={e => setForm(f => ({ ...f, interest_rate_annual: e.target.value }))}
              className="input-field text-sm w-24"/>
          </div>
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Tenure (months)</label>
            <input required type="number" min="1" max="480" value={form.tenure_months}
              onChange={e => setForm(f => ({ ...f, tenure_months: e.target.value }))}
              className="input-field text-sm w-28"/>
          </div>
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Start date</label>
            <input required type="date" value={form.start_date}
              onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))}
              className="input-field text-sm w-36"/>
          </div>
          <button type="submit" disabled={submitting} className="btn-primary text-sm">
            {submitting ? <Spinner size={14}/> : <><i className="ti ti-plus"/> Add loan</>}
          </button>
        </div>
        {emi && (
          <p className="mt-3 text-xs text-slate-500 border-t border-line pt-3">
            Estimated EMI: <span className="font-semibold text-ink">{formatINR(emi)}</span>
            <span className="text-slate-400"> · total payable {formatINR(emi * Number(form.tenure_months))}</span>
          </p>
        )}
      </form>

      {/* ── Loan list ────────────────────────────────────────────────────── */}
      {loans.length === 0 ? (
        <div className="card p-10 text-center text-sm text-slate-400">
          No loans tracked yet — add one above.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {loans.map(l => {
            const paidPct = l.tenure_months ? Math.round((l.months_elapsed / l.tenure_months) * 100) : 0;
            const typeLabel = TYPES.find(t => t.value === l.liability_type)?.label || l.liability_type;
            return (
              <div key={l.id} className="card p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-ink">{l.name}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">{typeLabel}</p>
                  </div>
                  <button onClick={() => handleRemove(l.id)} className="text-slate-400 hover:text-debit">
                    <i className="ti ti-trash"/>
                  </button>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-[11px] text-slate-500">EMI</p>
                    <p className="font-semibold text-ink">{formatINR(l.emi_amount)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] text-slate-500">Outstanding</p>
                    <p className="font-semibold text-debit">{formatINR(l.outstanding_balance)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] text-slate-500">Rate</p>
                    <p className="text-ink">{l.interest_rate_annual}% p.a.</p>
                  </div>
                  <div>
                    <p className="text-[11px] text-slate-500">Interest payable</p>
                    <p className="text-ink">{formatINR(l.total_interest_payable)}</p>
                  </div>
                </div>

                <div className="budget-bar-bg mt-4">
                  <div className="h-2 rounded-full bg-brand-500" style={{ width: `${paidPct}%` }}/>
                </div>
                <p className="text-[10px] text-slate-400 mt-1.5">
                  {l.months_elapsed} of {l.tenure_months} months paid ({paidPct}%) ·
                  {' '}{l.months_remaining} remaining · paid so far {formatINR(l.total_paid_so_far)}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
