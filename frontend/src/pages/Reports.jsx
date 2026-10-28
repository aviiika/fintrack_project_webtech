import { useCallback, useEffect, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { axisProps, GRID, legendProps, SERIES, tooltipProps } from '../components/chartTheme.js';
import { downloadFile, financeService } from '../api/financeService.js';
import { CHART_COLORS, formatINR } from '../components/CategoryPill.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';
import MonthPicker from '../components/MonthPicker.jsx';
import Spinner from '../components/Spinner.jsx';
import { useDefaultMonth } from '../hooks/useDefaultMonth.js';

const MONTH_LABEL = (m) => new Date(`${m}-01`).toLocaleDateString('en-IN', { month: 'short' });

export default function Reports() {
  const [month, setMonth, monthReady] = useDefaultMonth();
  const [year, setYear] = useState(() => new Date().getFullYear());
  const [annual, setAnnual] = useState(null);
  const [budgets, setBudgets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState('');

  // Budget editing
  const [editingBudgets, setEditingBudgets] = useState(false);
  const [drafts, setDrafts] = useState({});
  const [savingBudgets, setSavingBudgets] = useState(false);
  const [newBudget, setNewBudget] = useState({ category: '', monthly_limit: '' });
  const [categories, setCategories] = useState([]);

  const load = useCallback(async () => {
    if (!monthReady) return;
    setLoading(true); setError('');
    try {
      const [a, b] = await Promise.all([
        financeService.annual(year),
        financeService.budgets(month).catch(() => []),
      ]);
      setAnnual(a); setBudgets(b);
    } catch (err) {
      setError(err.message || 'Could not load reports.');
    } finally { setLoading(false); }
  }, [year, month, monthReady]);

  useEffect(() => { load(); }, [load]);

  // Follow the resolved month into its year, so the annual charts aren't showing
  // an empty current year while the month picker sits on a month with data.
  useEffect(() => {
    if (monthReady) setYear(Number(month.slice(0, 4)));
  }, [monthReady, month]);
  useEffect(() => { financeService.categories().then(setCategories).catch(() => {}); }, []);

  const handleDownload = async (kind) => {
    setDownloading(kind); setError('');
    try {
      if (kind === 'csv') {
        await downloadFile('/export/transactions.csv', `fintrack_${month}.csv`, { month });
      } else if (kind === 'csv-year') {
        await downloadFile('/export/transactions.csv', `fintrack_all.csv`);
      } else {
        await downloadFile('/export/report.xlsx', `fintrack_report_${month}.xlsx`, { month });
      }
    } catch (err) {
      setError(err.message || 'Download failed.');
    } finally { setDownloading(''); }
  };

  const startEditing = () => {
    setDrafts(Object.fromEntries(budgets.map(b => [b.id, String(b.monthly_limit)])));
    setEditingBudgets(true);
  };

  const saveBudgets = async () => {
    setSavingBudgets(true); setError('');
    try {
      // Only PATCH what actually changed — no point sending 7 identical writes.
      const changed = budgets.filter(b => Number(drafts[b.id]) !== b.monthly_limit
                                           && Number(drafts[b.id]) > 0);
      await Promise.all(changed.map(b =>
        financeService.updateBudget(b.id, { monthly_limit: Number(drafts[b.id]) })));
      setEditingBudgets(false);
      await load();
    } catch (err) {
      setError(err.message || 'Could not save budgets.');
    } finally { setSavingBudgets(false); }
  };

  const addBudget = async (e) => {
    e.preventDefault();
    if (!newBudget.category || !newBudget.monthly_limit) return;
    try {
      await financeService.createBudget({
        category: newBudget.category,
        monthly_limit: Number(newBudget.monthly_limit),
        month,
      });
      setNewBudget({ category: '', monthly_limit: '' });
      await load();
    } catch (err) { setError(err.message || 'Could not add budget.'); }
  };

  const removeBudget = async (id) => {
    try { await financeService.deleteBudget(id); await load(); }
    catch (err) { setError(err.message || 'Could not delete budget.'); }
  };

  if (loading) {
    return <div className="flex h-full items-center justify-center p-10"><Spinner size={28} className="text-accent-text"/></div>;
  }

  const monthlyData = (annual?.monthly || []).map(m => ({
    ...m, label: MONTH_LABEL(m.month),
    savings: round2(m.income - m.spending),
  }));
  const topCats = annual?.top_categories || [];
  const overCount = budgets.filter(b => b.over_budget).length;

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-ink">Reports &amp; Budgets</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Annual trends, category breakdowns, and per-category budget tracking.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <MonthPicker value={month} onChange={setMonth}/>
          <select value={year} onChange={e => setYear(Number(e.target.value))}
            className="input-field py-1 text-xs">
            {Array.from(new Set([
              year,
              ...[0, 1, 2].map(d => new Date().getFullYear() - d),
            ])).sort((a, b) => b - a).map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </div>

      <ErrorBanner message={error} />

      {/* ── Export actions ────────────────────────────────────────────────── */}
      <div className="mb-5 grid grid-cols-1 gap-4 md:grid-cols-3">
        <ExportCard icon="ti-file-spreadsheet" title="Excel report"
          desc={`Multi-sheet .xlsx for ${month} — transactions, category pivot, monthly summary`}
          busy={downloading === 'xlsx'} onClick={() => handleDownload('xlsx')}/>
        <ExportCard icon="ti-file-text" title="Monthly CSV"
          desc={`Flat export of every ${month} transaction, with ML source and confidence`}
          busy={downloading === 'csv'} onClick={() => handleDownload('csv')}/>
        <ExportCard icon="ti-database-export" title="Full history CSV"
          desc="Every transaction ever imported, across all months and banks"
          busy={downloading === 'csv-year'} onClick={() => handleDownload('csv-year')}/>
      </div>

      {/* ── Annual income vs spending ─────────────────────────────────────── */}
      <div className="card mb-5 p-5">
        <p className="mb-4 text-sm font-medium text-ink">
          Annual overview — {year}
        </p>
        <div style={{ height: 240 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID}/>
              <XAxis dataKey="label" {...axisProps}/>
              <YAxis {...axisProps} tickFormatter={v => `${(v / 1000).toFixed(0)}k`}/>
              <Tooltip formatter={v => formatINR(v)} {...tooltipProps}/>
              <Legend {...legendProps}/>
              <Bar dataKey="income" fill={SERIES.income} name="Income" radius={[3, 3, 0, 0]}/>
              <Bar dataKey="spending" fill={SERIES.spending} name="Spending" radius={[3, 3, 0, 0]}/>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="mb-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Savings trend */}
        <div className="card p-5">
          <p className="mb-4 text-sm font-medium text-ink">Savings trend — {year}</p>
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID}/>
                <XAxis dataKey="label" {...axisProps}/>
                <YAxis {...axisProps} tickFormatter={v => `${(v / 1000).toFixed(0)}k`}/>
                <Tooltip formatter={v => formatINR(v)} {...tooltipProps}/>
                <Line type="monotone" dataKey="savings" stroke={SERIES.neutral} strokeWidth={2}
                  dot={{ r: 2 }} name="Savings"/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top categories for the year */}
        <div className="card p-5">
          <p className="mb-4 text-sm font-medium text-ink">Top categories — {year}</p>
          {topCats.length === 0 ? (
            <p className="text-xs text-slate-400">No spending recorded for {year}.</p>
          ) : (
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topCats.slice(0, 7)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID}/>
                  <XAxis type="number" {...axisProps} tick={{ ...axisProps.tick, fontSize: 10 }}
                    tickFormatter={v => `${(v / 1000).toFixed(0)}k`}/>
                  <YAxis type="category" dataKey="category" width={95} {...axisProps} tick={{ ...axisProps.tick, fontSize: 10 }}/>
                  <Tooltip formatter={v => formatINR(v)} {...tooltipProps}/>
                  <Bar dataKey="amount" radius={[0, 3, 3, 0]}>
                    {topCats.slice(0, 7).map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]}/>
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* ── Budget tracker ────────────────────────────────────────────────── */}
      <div className="card p-5">
        <div className="mb-4 flex items-baseline justify-between">
          <div>
            <p className="text-sm font-medium text-ink">Budget tracker</p>
            <p className="mt-0.5 text-xs text-slate-500">
              {month} — {overCount > 0
                ? <span className="text-debit">{overCount} budget{overCount === 1 ? '' : 's'} exceeded</span>
                : <span className="text-credit">all within limits</span>}
            </p>
          </div>
          {editingBudgets ? (
            <div className="flex gap-2">
              <button onClick={() => setEditingBudgets(false)} className="btn-ghost text-xs py-1 px-2.5">
                Cancel
              </button>
              <button onClick={saveBudgets} disabled={savingBudgets} className="btn-primary text-xs py-1 px-2.5">
                {savingBudgets ? <Spinner size={12}/> : 'Save limits'}
              </button>
            </div>
          ) : (
            <button onClick={startEditing} disabled={budgets.length === 0}
              className="btn-ghost text-xs py-1 px-2.5">
              <i className="ti ti-edit"/> Edit limits
            </button>
          )}
        </div>

        {budgets.length === 0 ? (
          <p className="mb-4 text-xs text-slate-400">No budgets set for {month}. Add one below.</p>
        ) : (
          <div className="mb-5 flex flex-col gap-3">
            {budgets.map(b => (
              <div key={b.id}>
                <div className="flex items-baseline justify-between text-sm">
                  <span className="font-medium text-ink">{b.category}</span>
                  <span className="flex items-center gap-2">
                    <span className={
                      b.status === 'over' ? 'text-xs text-debit'
                        : b.status === 'warning' ? 'text-xs text-warn' : 'text-xs text-credit'
                    }>
                      {b.status === 'over'
                        ? `Over by ${formatINR(b.spent - b.monthly_limit)}`
                        : b.status === 'warning' ? 'Close to limit' : 'On track'}
                    </span>
                    {editingBudgets ? (
                      <span className="flex items-center gap-1">
                        <span className="text-xs text-slate-500">{formatINR(b.spent)} /</span>
                        <input type="number" min="1" value={drafts[b.id] ?? ''}
                          onChange={e => setDrafts(d => ({ ...d, [b.id]: e.target.value }))}
                          className="input-field w-24 py-0.5 text-xs"/>
                        <button onClick={() => removeBudget(b.id)} title="Remove budget"
                          className="text-slate-300 hover:text-debit">
                          <i className="ti ti-trash text-sm"/>
                        </button>
                      </span>
                    ) : (
                      <span className="text-xs text-slate-500">
                        {formatINR(b.spent)} / {formatINR(b.monthly_limit)}
                      </span>
                    )}
                  </span>
                </div>
                <div className="budget-bar-bg mt-1.5">
                  <div className={`h-2 rounded-full transition-all ${
                    b.status === 'over' ? 'bg-debit'
                      : b.status === 'warning' ? 'bg-warn' : 'bg-credit'
                  }`} style={{ width: `${Math.min(100, b.percent_used)}%` }}/>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add budget */}
        <form onSubmit={addBudget} className="flex items-end gap-2 border-t border-line pt-4">
          <div>
            <label className="mb-1 block text-[10px] text-slate-500">Category</label>
            <select required value={newBudget.category}
              onChange={e => setNewBudget(n => ({ ...n, category: e.target.value }))}
              className="input-field py-1 text-xs">
              <option value="">Pick a category…</option>
              {categories
                .filter(c => !budgets.some(b => b.category === c))
                .map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[10px] text-slate-500">Monthly limit</label>
            <input required type="number" min="1" value={newBudget.monthly_limit}
              onChange={e => setNewBudget(n => ({ ...n, monthly_limit: e.target.value }))}
              placeholder="5000" className="input-field w-28 py-1 text-xs"/>
          </div>
          <button type="submit" className="btn-primary text-xs py-1.5 px-3">
            <i className="ti ti-plus"/> Add budget
          </button>
        </form>
      </div>
    </div>
  );
}

function ExportCard({ icon, title, desc, busy, onClick }) {
  return (
    <button onClick={onClick} disabled={busy}
      className="card p-4 text-left transition-colors hover:border-accent hover:bg-brand-50 disabled:opacity-60">
      <p className="flex items-center gap-2 text-sm font-medium text-ink">
        {busy ? <Spinner size={16} className="text-accent-text"/> : <i className={`ti ${icon} text-base text-accent-text`}/>}
        {title}
      </p>
      <p className="mt-1.5 text-[11px] leading-relaxed text-slate-500">{desc}</p>
      <p className="mt-2 text-[11px] font-medium text-accent-text">
        {busy ? 'Preparing…' : 'Download →'}
      </p>
    </button>
  );
}

function round2(n) { return Math.round(n * 100) / 100; }
