import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { axisProps, GRID, legendProps, SERIES, tooltipProps } from '../components/chartTheme.js';
import { downloadFile, financeService } from '../api/financeService.js';
import { CHART_COLORS, categoryIcon, formatINR } from '../components/CategoryPill.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';
import MonthPicker from '../components/MonthPicker.jsx';
import Spinner from '../components/Spinner.jsx';
import { useDefaultMonth } from '../hooks/useDefaultMonth.js';


function Metric({ icon, label, value, sub, tone = 'slate' }) {
  const toneClass = { slate: 'text-ink', emerald: 'text-credit', red: 'text-debit' }[tone];
  return (
    <div className="card p-4">
      <p className="flex items-center gap-1.5 text-xs text-slate-500">
        <i className={`ti ${icon}`}/>{label}
      </p>
      <p className={`mt-2 font-mono text-2xl font-medium tabular-nums tracking-tight ${toneClass}`}>{value}</p>
      <p className="mt-1 text-[11px] text-slate-500">{sub}</p>
    </div>
  );
}

export default function Dashboard() {
  const [month, setMonth, monthReady] = useDefaultMonth();
  const [bank, setBank] = useState('all');
  const [stats, setStats] = useState(null);
  const [budgets, setBudgets] = useState([]);
  const [loading, setLoading] = useState(true);   // first paint only
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    // Wait for the default month to resolve, otherwise we'd fetch today's month
    // and then immediately re-fetch the month that actually has data.
    if (!monthReady) return;
    setRefreshing(true); setError('');
    try {
      // The bank filter is applied server-side, so every figure below follows it.
      const [s, b] = await Promise.all([
        financeService.dashboard(month, bank),
        financeService.budgets(month).catch(() => []),
      ]);
      setStats(s); setBudgets(b);
    } catch (err) {
      setError(err.message || 'Could not load dashboard.');
    } finally { setLoading(false); setRefreshing(false); }
  }, [month, bank, monthReady]);

  useEffect(() => { load(); }, [load]);

  // Offer exactly the banks that have data this month. If the selected bank has no
  // rows in a newly picked month it stays selectable, so the empty state is explicit.
  const bankChips = useMemo(() => {
    const present = (stats?.banks || []).map(b => b.bank);
    return ['all', ...(bank !== 'all' && !present.includes(bank) ? [bank] : []), ...present];
  }, [stats, bank]);
  const recent = stats?.recent_transactions || [];

  const overBudget = useMemo(() => budgets.filter(b => b.over_budget), [budgets]);

  const catData = stats?.spending_by_category || [];
  const maxCat = catData.length ? catData[0].amount : 0;
  const totalSpend = catData.reduce((s, c) => s + c.amount, 0);
  const donutData = useMemo(() => {
    const top = catData.slice(0, 4);
    const rest = catData.slice(4).reduce((s, c) => s + c.amount, 0);
    return rest > 0 ? [...top, { category: 'Others', amount: rest }] : top;
  }, [catData]);

  const maxDaily = Math.max(1, ...(stats?.daily_trend || []).map(d => d.amount));

  const handleExport = async () => {
    try {
      await downloadFile('/export/transactions.csv', `fintrack_${month}.csv`, { month });
    } catch (err) { setError(err.message || 'Export failed.'); }
  };

  if (loading) {
    return <div className="flex h-full items-center justify-center p-10"><Spinner size={28} className="text-accent-text"/></div>;
  }

  return (
    <div className={`flex-1 overflow-auto p-6 transition-opacity ${refreshing ? 'opacity-60' : ''}`}>
      <h1 className="page-title">Dashboard</h1>
      <div className="mb-5 mt-1 h-px w-12 bg-accent"/>
      {/* ── Filter bar ────────────────────────────────────────────────────── */}
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <MonthPicker value={month} onChange={setMonth}/>
        <div className="flex gap-1">
          {bankChips.map(b => (
            <button key={b} onClick={() => setBank(b)}
              className={`rounded-sm px-2.5 py-1 text-xs capitalize transition-colors ${
                bank === b ? 'bg-brand-600 text-white' : 'bg-surface border border-line text-slate-600 hover:bg-surface-2'
              }`} aria-pressed={bank === b}>
              {b === 'all' ? 'All banks' : b.toUpperCase()}
            </button>
          ))}
        </div>
        <button onClick={handleExport} className="btn-ghost ml-auto text-xs py-1.5 px-3">
          <i className="ti ti-download"/> Export CSV
        </button>
      </div>

      <ErrorBanner message={error} />

      {/* ── Metrics ───────────────────────────────────────────────────────── */}
      <div className="mb-5 grid grid-cols-2 gap-4 xl:grid-cols-4">
        <Metric icon="ti-arrow-down-circle" label="Total income" tone="emerald"
          value={formatINR(stats?.total_income ?? 0)}
          sub={`${stats?.credit_count ?? 0} credit source${stats?.credit_count === 1 ? '' : 's'}`}/>
        <Metric icon="ti-arrow-up-circle" label="Total spent" tone="red"
          value={formatINR(stats?.total_spent ?? 0)}
          sub={`${stats?.debit_count ?? 0} transactions`}/>
        <Metric icon="ti-piggy-bank" label="Savings"
          value={formatINR(stats?.savings ?? 0)}
          sub={`${stats?.savings_rate ?? 0}% savings rate`}/>
        <Metric icon="ti-alert-triangle" label="Over budget"
          tone={overBudget.length ? 'red' : 'emerald'}
          value={`${overBudget.length} ${overBudget.length === 1 ? 'category' : 'categories'}`}
          sub={(overBudget.length ? overBudget.map(b => b.category).join(', ') : 'All within limits')
            + (bank !== 'all' ? ' · budgets cover all banks' : '')}/>
      </div>

      {stats?.transaction_count === 0 ? (
        <div className="card p-12 text-center">
          <i className="ti ti-mood-empty mb-3 block text-4xl text-slate-300"/>
          <p className="text-sm text-slate-500">No {bank !== 'all' ? `${bank.toUpperCase()} ` : ''}transactions for {month}.</p>
          <Link to="/import" className="btn-primary mt-4 inline-flex text-sm">
            <i className="ti ti-upload"/> Import a statement
          </Link>
        </div>
      ) : (
        <>
          {/* ── Charts ────────────────────────────────────────────────────── */}
          <div className="mb-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
            {/* Category bars */}
            <div className="card p-5 lg:col-span-2">
              <div className="mb-4 flex items-baseline justify-between">
                <p className="text-sm font-medium text-ink">Spending by category</p>
                <span className="font-mono text-[11px] text-slate-500">
                  {bank !== 'all' ? `${bank.toUpperCase()} · ` : ''}{month}
                </span>
              </div>
              <div className="flex flex-col gap-2.5">
                {catData.slice(0, 8).map((c, i) => (
                  <div key={c.category} className="flex items-center gap-3">
                    <span className="w-24 flex-shrink-0 truncate text-xs text-slate-600">{c.category}</span>
                    <div className="h-5 flex-1 overflow-hidden rounded-sm bg-paper">
                      <div className="h-5 rounded-sm transition-all"
                        style={{ width: `${maxCat ? (c.amount / maxCat) * 100 : 0}%`,
                                  background: CHART_COLORS[i % CHART_COLORS.length] }}/>
                    </div>
                    <span className="amount w-20 flex-shrink-0 text-xs font-medium text-ink">
                      {formatINR(c.amount)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Donut */}
            <div className="card p-5">
              <p className="mb-2 text-sm font-medium text-ink">Breakdown</p>
              <div style={{ height: 150 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={donutData} dataKey="amount" nameKey="category"
                      innerRadius={38} outerRadius={60} paddingAngle={2}>
                      {donutData.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]}/>
                      ))}
                    </Pie>
                    <Tooltip formatter={v => formatINR(v)} {...tooltipProps}/>
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 flex flex-col gap-1">
                {donutData.map((c, i) => (
                  <div key={c.category} className="flex items-center gap-1.5 text-[11px] text-slate-600">
                    <span className="h-2 w-2 flex-shrink-0 rounded-sm"
                      style={{ background: CHART_COLORS[i % CHART_COLORS.length] }}/>
                    <span className="flex-1 truncate">{c.category}</span>
                    <span className="font-mono tabular-nums text-slate-500">
                      {totalSpend ? Math.round((c.amount / totalSpend) * 100) : 0}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ── Daily trend ───────────────────────────────────────────────── */}
          <div className="card mb-5 p-5">
            <p className="mb-4 text-sm font-medium text-ink">Daily spend trend</p>
            {(stats?.daily_trend || []).length === 0 ? (
              <p className="text-xs text-slate-500">No debits this month.</p>
            ) : (
              <div className="flex h-24 items-end gap-1">
                {stats.daily_trend.map(d => (
                  <div key={d.date} className="group relative flex-1"
                    title={`${d.date}: ${formatINR(d.amount)}`}>
                    <div className="w-full rounded-t-sm bg-accent/60 transition-colors group-hover:bg-accent-text"
                      style={{ height: `${Math.max(4, (d.amount / maxDaily) * 96)}px` }}/>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Recent transactions ───────────────────────────────────────── */}
          <div className="card p-5">
            <div className="mb-3 flex items-baseline justify-between">
              <p className="text-sm font-medium text-ink">
                Recent transactions
                {bank !== 'all' && <span className="ml-1.5 text-[11px] font-normal text-slate-500">
                  ({bank.toUpperCase()} only)
                </span>}
              </p>
              <Link to="/transactions" className="text-xs text-accent-text underline-offset-2 hover:underline">View all transactions</Link>
            </div>
            {recent.length === 0 ? (
              <p className="text-xs text-slate-500">
                No recent transactions{bank !== 'all' ? ` from ${bank.toUpperCase()}` : ''}.
              </p>
            ) : (
              <div>
                {recent.map(t => (
                  <div key={t.id} className="ledger-row">
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-sm bg-surface-2 text-accent-text">
                      <i className={`ti ${categoryIcon(t.category)} text-sm`}/>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-ink">{t.description}</p>
                      <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[11px] text-slate-500">
                        <span>{t.category || 'Uncategorized'}</span>
                        <span className="font-mono">{t.bank.toUpperCase()}</span>
                        <span className="font-mono">{t.date}</span>
                        {t.category_source === 'ml' && t.category_confidence != null && (
                          <span className="stamp" title="Category chosen by the model, with its confidence">
                            model {Math.round(t.category_confidence * 100)}%
                          </span>
                        )}
                      </p>
                    </div>
                    <span className={`flex-shrink-0 text-sm font-medium ${
                      t.txn_type === 'credit' ? 'amount-credit' : 'amount-debit'
                    }`}>
                      {t.txn_type === 'credit' ? '+' : '−'}{formatINR(t.amount)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
