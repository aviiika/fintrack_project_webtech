import { useCallback, useEffect, useRef, useState } from 'react';
import { financeService } from '../api/financeService.js';
import { mlService } from '../api/mlService.js';
import { CategoryPill, formatINR } from '../components/CategoryPill.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';
import MonthPicker from '../components/MonthPicker.jsx';
import Spinner from '../components/Spinner.jsx';
import { useDefaultMonth } from '../hooks/useDefaultMonth.js';

const PAGE_SIZE = 25;

/** Small badge showing HOW a category was assigned — this is what makes the ML
 *  layer visible on the screen where it actually matters. */
function SourceBadge({ source, confidence }) {
  if (!source) return null;
  const map = {
    ml:                   { label: 'Model',  cls: 'stamp' },
    manual:               { label: 'You',    cls: 'bg-brand-600 text-white' },
    rules_low_confidence: { label: 'Rules',  cls: 'bg-warn/15 text-warn' },
    rules_no_model:       { label: 'Rules',  cls: 'bg-surface-2 text-slate-500' },
    rules:                { label: 'Rules',  cls: 'bg-surface-2 text-slate-500' },
  };
  const m = map[source] || { label: source, cls: 'bg-surface-2 text-slate-500' };
  const pct = confidence != null ? ` ${Math.round(confidence * 100)}%` : '';
  const title = {
    ml: 'Predicted by the ML model',
    manual: 'You corrected this — it now trains the model at 2x weight',
    rules_low_confidence: 'ML confidence was below threshold, so keyword rules decided',
    rules_no_model: 'No model trained yet, so keyword rules decided',
  }[source] || source;
  return (
    <span title={title} className={`ml-2 rounded-sm px-1.5 py-0.5 font-mono text-[10px] font-medium ${m.cls}`}>
      {m.label}{source === 'ml' ? pct : ''}
    </span>
  );
}

export default function Transactions() {
  const [month, setMonth, monthReady] = useDefaultMonth();
  const [allMonths, setAllMonths] = useState(false);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [txnType, setTxnType] = useState('');
  const [page, setPage] = useState(0);

  const [data, setData] = useState({ items: [], total: 0 });
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [savingId, setSavingId] = useState(null);
  const [correctionStatus, setCorrectionStatus] = useState(null);
  const [toast, setToast] = useState('');

  // Debounce the search box so typing doesn't fire a request per keystroke.
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const searchTimer = useRef(null);
  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => { setDebouncedSearch(search); setPage(0); }, 350);
    return () => clearTimeout(searchTimer.current);
  }, [search]);

  const load = useCallback(async () => {
    if (!monthReady) return;
    setLoading(true); setError('');
    try {
      const params = {
        skip: page * PAGE_SIZE, limit: PAGE_SIZE,
        ...(allMonths ? {} : { month }),
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        ...(category ? { category } : {}),
        ...(txnType ? { txn_type: txnType } : {}),
      };
      setData(await financeService.transactions(params));
    } catch (err) {
      setError(err.message || 'Could not load transactions.');
    } finally { setLoading(false); }
  }, [month, allMonths, debouncedSearch, category, txnType, page, monthReady]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    financeService.categories().then(setCategories).catch(() => {});
    mlService.correctionStatus().then(setCorrectionStatus).catch(() => {});
  }, []);

  /** The feedback loop's entry point: changing a category marks the row
   *  user_corrected, bumps the counter, and may trigger an auto-retrain. */
  const handleCategoryChange = async (txn, newCategory) => {
    if (!newCategory || newCategory === txn.category) { setEditingId(null); return; }
    setSavingId(txn.id);
    try {
      const updated = await financeService.updateTransaction(txn.id, { category: newCategory });
      setData(d => ({ ...d, items: d.items.map(t => (t.id === txn.id ? updated : t)) }));
      const status = await mlService.correctionStatus().catch(() => null);
      if (status) {
        const crossed = correctionStatus && status.corrections_this_cycle < correctionStatus.corrections_this_cycle;
        setCorrectionStatus(status);
        setToast(crossed
          ? 'Correction saved — threshold reached, model retrained.'
          : `Correction saved — ${status.next_retrain_in} more until the model retrains.`);
        setTimeout(() => setToast(''), 4000);
      }
    } catch (err) {
      setError(err.message || 'Could not update category.');
    } finally { setSavingId(null); setEditingId(null); }
  };

  const handleDelete = async (txn) => {
    if (!window.confirm(`Delete "${txn.description}"? This cannot be undone.`)) return;
    try {
      await financeService.deleteTransaction(txn.id);
      await load();
    } catch (err) { setError(err.message || 'Could not delete transaction.'); }
  };

  const totalPages = Math.ceil(data.total / PAGE_SIZE);
  const from = data.total === 0 ? 0 : page * PAGE_SIZE + 1;
  const to = Math.min((page + 1) * PAGE_SIZE, data.total);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex-shrink-0 border-b border-line bg-surface px-6 py-4">
        <div className="flex items-baseline justify-between">
          <div>
            <h1 className="text-lg font-semibold text-ink">All transactions</h1>
            <p className="mt-0.5 text-sm text-slate-500">
              {data.total} record{data.total === 1 ? '' : 's'} · {allMonths ? 'all time' : month}
              {correctionStatus && (
                <span className="ml-2 text-xs text-slate-400">
                  · {correctionStatus.corrections_this_cycle}/{correctionStatus.threshold_for_retrain} corrections
                  toward next retrain
                </span>
              )}
            </p>
          </div>
          {toast && (
            <span className="rounded-sm bg-credit/10 px-3 py-1.5 text-xs text-credit">
              <i className="ti ti-circle-check mr-1"/>{toast}
            </span>
          )}
        </div>

        {/* ── Filters ───────────────────────────────────────────────────────── */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <div className="relative">
            <i className="ti ti-search pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-sm text-slate-400"/>
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search description…"
              className="input-field py-1 pl-8 text-xs w-52"/>
          </div>

          {!allMonths && <MonthPicker value={month} onChange={m => { setMonth(m); setPage(0); }}/>}

          <label className="flex cursor-pointer items-center gap-1.5 text-xs text-slate-600">
            <input type="checkbox" checked={allMonths}
              onChange={e => { setAllMonths(e.target.checked); setPage(0); }}
              className="rounded border-line"/>
            All months
          </label>

          <select value={category} onChange={e => { setCategory(e.target.value); setPage(0); }}
            className="input-field py-1 text-xs">
            <option value="">All categories</option>
            {categories.map(c => <option key={c} value={c}>{c}</option>)}
          </select>

          <select value={txnType} onChange={e => { setTxnType(e.target.value); setPage(0); }}
            className="input-field py-1 text-xs">
            <option value="">Debit + credit</option>
            <option value="debit">Debit only</option>
            <option value="credit">Credit only</option>
          </select>

          {(search || category || txnType || allMonths) && (
            <button onClick={() => { setSearch(''); setCategory(''); setTxnType(''); setAllMonths(false); setPage(0); }}
              className="text-xs text-slate-500 hover:text-ink">
              <i className="ti ti-x mr-0.5"/>Clear
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <ErrorBanner message={error} />

        {loading ? (
          <div className="flex items-center justify-center p-10"><Spinner size={28} className="text-accent-text"/></div>
        ) : data.items.length === 0 ? (
          <div className="card p-12 text-center">
            <i className="ti ti-search-off mb-3 block text-4xl text-slate-300"/>
            <p className="text-sm text-slate-500">No transactions match these filters.</p>
          </div>
        ) : (
          <>
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-paper text-[11px] text-slate-500">
                  <tr>
                    <th className="px-4 py-2 text-left">Date</th>
                    <th className="px-4 py-2 text-left">Description</th>
                    <th className="px-4 py-2 text-left">Category</th>
                    <th className="px-4 py-2 text-left">Bank</th>
                    <th className="px-4 py-2 text-right">Amount</th>
                    <th className="px-4 py-2 text-right">Balance</th>
                    <th className="px-4 py-2"/>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {data.items.map(t => (
                    <tr key={t.id} className="hover:bg-paper">
                      <td className="whitespace-nowrap px-4 py-2.5 text-xs text-slate-500">{t.date}</td>
                      <td className="max-w-xs px-4 py-2.5">
                        <span className="block truncate text-ink" title={t.description}>
                          {t.description}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        {editingId === t.id ? (
                          <select autoFocus defaultValue={t.category || ''}
                            onBlur={() => setEditingId(null)}
                            onChange={e => handleCategoryChange(t, e.target.value)}
                            className="input-field py-0.5 text-xs">
                            <option value="">— pick —</option>
                            {categories.map(c => <option key={c} value={c}>{c}</option>)}
                          </select>
                        ) : (
                          <button onClick={() => setEditingId(t.id)}
                            title="Click to correct — your correction trains the model"
                            className="flex items-center hover:opacity-75">
                            {savingId === t.id
                              ? <Spinner size={14} className="text-accent-text"/>
                              : <><CategoryPill category={t.category}/>
                                  <SourceBadge source={t.category_source} confidence={t.category_confidence}/></>}
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-xs uppercase text-slate-500">{t.bank}</td>
                      <td className={`whitespace-nowrap px-4 py-2.5 text-right font-medium ${
                        t.txn_type === 'credit' ? 'text-credit' : 'text-ink'
                      }`}>
                        {t.txn_type === 'credit' ? '+' : '−'}{formatINR(t.amount)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-right text-xs text-slate-400">
                        {t.balance != null ? formatINR(t.balance) : '—'}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <button onClick={() => handleDelete(t)} title="Delete"
                          className="text-slate-300 hover:text-debit">
                          <i className="ti ti-trash text-sm"/>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* ── Pagination ────────────────────────────────────────────────── */}
            <div className="mt-3 flex items-center justify-between">
              <p className="text-xs text-slate-500">
                Showing {from}–{to} of {data.total}
              </p>
              <div className="flex items-center gap-1">
                <button disabled={page === 0} onClick={() => setPage(p => p - 1)}
                  className="btn-ghost px-2 py-1 text-xs">
                  <i className="ti ti-chevron-left"/>
                </button>
                <span className="px-2 text-xs text-slate-500">
                  Page {page + 1} of {totalPages || 1}
                </span>
                <button disabled={page + 1 >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="btn-ghost px-2 py-1 text-xs">
                  <i className="ti ti-chevron-right"/>
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
