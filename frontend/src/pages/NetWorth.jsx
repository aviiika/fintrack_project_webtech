import { useCallback, useEffect, useState } from 'react';
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { axisProps, GRID, legendProps, SERIES, tooltipProps } from '../components/chartTheme.js';
import { networthService } from '../api/networthService.js';
import { formatINR } from '../components/CategoryPill.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';
import Spinner from '../components/Spinner.jsx';

/** Net Worth page — pulls the transaction ledger, the stock portfolio, and the
 *  loan tracker into one number, plus the snapshot history the scheduler builds. */
export default function NetWorth() {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [snapping, setSnapping] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, h] = await Promise.all([
        networthService.summary(),
        networthService.history().catch(() => []),
      ]);
      setSummary(s); setHistory(h);
    } catch (err) {
      setError(err.message || 'Could not load net worth.');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSnapshot = async () => {
    setSnapping(true); setError('');
    try { await networthService.snapshot(); await load(); }
    catch (err) { setError(err.message); }
    finally { setSnapping(false); }
  };

  if (loading) {
    return <div className="flex h-full items-center justify-center p-10"><Spinner size={28} className="text-accent-text"/></div>;
  }

  const positive = (summary?.net_worth ?? 0) >= 0;

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-lg font-semibold text-ink">Net Worth</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Cash from your imported ledger, plus live portfolio value, minus what you still owe.
          </p>
        </div>
        <button onClick={handleSnapshot} disabled={snapping} className="btn-ghost text-xs py-1.5 px-3">
          {snapping ? <><Spinner size={14}/> Saving…</> : <><i className="ti ti-camera"/> Snapshot today</>}
        </button>
      </div>

      <ErrorBanner message={error} />

      {/* ── Headline ─────────────────────────────────────────────────────── */}
      <div className="card mb-5 p-5">
        <p className="text-xs text-slate-500">Net worth</p>
        <p className={`text-3xl font-bold mt-1 ${positive ? 'text-ink' : 'text-debit'}`}>
          {formatINR(summary?.net_worth ?? 0)}
        </p>
        <div className="mt-4 grid grid-cols-2 gap-4 border-t lg:grid-cols-4 border-line pt-4">
          <div>
            <p className="text-[11px] text-slate-500">Cash</p>
            <p className="font-semibold text-ink mt-0.5">{formatINR(summary?.cash_balance ?? 0)}</p>
          </div>
          <div>
            <p className="text-[11px] text-slate-500">Investments</p>
            <p className="font-semibold text-ink mt-0.5">{formatINR(summary?.investments_value ?? 0)}</p>
          </div>
          <div>
            <p className="text-[11px] text-slate-500">Total assets</p>
            <p className="font-semibold text-credit mt-0.5">{formatINR(summary?.total_assets ?? 0)}</p>
          </div>
          <div>
            <p className="text-[11px] text-slate-500">Liabilities</p>
            <p className="font-semibold text-debit mt-0.5">{formatINR(summary?.total_liabilities ?? 0)}</p>
          </div>
        </div>
      </div>

      {/* ── History chart ────────────────────────────────────────────────── */}
      <div className="card mb-5 p-5">
        <p className="text-xs text-slate-500 mb-3">
          <i className="ti ti-chart-line mr-1"/> Net worth over time
        </p>
        {history.length < 2 ? (
          <p className="text-xs text-slate-400">
            Only {history.length} snapshot{history.length === 1 ? '' : 's'} so far. The nightly
            background job adds one per day — or hit &quot;Snapshot today&quot; above to add one now.
          </p>
        ) : (
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID}/>
                <XAxis dataKey="date" {...axisProps}/>
                <YAxis {...axisProps} tickFormatter={v => `${(v / 1000).toFixed(0)}k`}/>
                <Tooltip formatter={v => formatINR(v)} {...tooltipProps}/>
                <Line type="monotone" dataKey="net_worth" stroke={SERIES.neutral} strokeWidth={2} dot={false} name="Net worth"/>
                <Line type="monotone" dataKey="total_assets" stroke={SERIES.income} strokeWidth={1.5} dot={false} name="Assets"/>
                <Line type="monotone" dataKey="total_liabilities" stroke={SERIES.spending} strokeWidth={1.5} dot={false} name="Liabilities"/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* ── Liability breakdown ──────────────────────────────────────────── */}
      <div className="card p-5">
        <p className="text-xs text-slate-500 mb-3">
          <i className="ti ti-receipt mr-1"/> Outstanding liabilities ({summary?.liabilities?.length ?? 0})
        </p>
        {(summary?.liabilities ?? []).length === 0 ? (
          <p className="text-xs text-slate-400">No loans tracked. Add one on the Loans page.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {summary.liabilities.map(l => {
              const paidPct = l.tenure_months
                ? Math.round((l.months_elapsed / l.tenure_months) * 100) : 0;
              return (
                <div key={l.id}>
                  <div className="flex items-baseline justify-between text-sm">
                    <span className="font-medium text-ink">{l.name}</span>
                    <span className="text-slate-500">{formatINR(l.outstanding_balance)} left</span>
                  </div>
                  <div className="budget-bar-bg mt-1.5">
                    <div className="h-2 rounded-full bg-brand-500" style={{ width: `${paidPct}%` }}/>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1">
                    {l.months_elapsed}/{l.tenure_months} months paid · EMI {formatINR(l.emi_amount)}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
