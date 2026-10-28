import { useCallback, useEffect, useState } from 'react';
import { portfolioService } from '../api/portfolioService.js';
import { useLivePrices } from '../hooks/useLivePrices.js';
import { formatINR } from '../components/CategoryPill.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';
import Spinner from '../components/Spinner.jsx';

const EMPTY_FORM = { symbol: '', exchange: 'NSE', quantity: '', avg_buy_price: '' };

/** Stock portfolio page — holdings table marked-to-market with a live WebSocket feed. */
export default function Portfolio() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  const { prices: livePrices, connected } = useLivePrices(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setSummary(await portfolioService.summary());
    } catch (err) {
      setError(err.message || 'Could not load portfolio.');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e) => {
    e.preventDefault();
    setSubmitting(true); setError('');
    try {
      await portfolioService.add({
        symbol: form.symbol.toUpperCase().trim(),
        exchange: form.exchange,
        quantity: Number(form.quantity),
        avg_buy_price: Number(form.avg_buy_price),
      });
      setForm(EMPTY_FORM);
      await load();
    } catch (err) { setError(err.message); }
    finally { setSubmitting(false); }
  };

  const handleRemove = async (id) => {
    try { await portfolioService.remove(id); await load(); }
    catch (err) { setError(err.message); }
  };

  if (loading) {
    return <div className="flex h-full items-center justify-center p-10"><Spinner size={28} className="text-accent-text"/></div>;
  }

  const gainPositive = (summary?.total_gain_loss ?? 0) >= 0;

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-ink">Portfolio</h1>
          <p className="mt-0.5 text-sm text-slate-500">Your stock holdings, marked to market live.</p>
        </div>
        <span className={`flex items-center gap-1.5 text-xs ${connected ? 'text-credit' : 'text-slate-400'}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-credit animate-pulse' : 'bg-slate-300'}`}/>
          {connected ? 'Live feed connected' : 'Reconnecting…'}
        </span>
      </div>

      <ErrorBanner message={error} />

      {/* ── Summary row ──────────────────────────────────────────────────── */}
      <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div className="card p-4">
          <p className="text-[11px] text-slate-500">Invested</p>
          <p className="font-mono text-xl font-medium tabular-nums text-ink mt-1">{formatINR(summary?.total_invested ?? 0)}</p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] text-slate-500">Current value</p>
          <p className="font-mono text-xl font-medium tabular-nums text-ink mt-1">{formatINR(summary?.total_current_value ?? 0)}</p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] text-slate-500">Gain / loss</p>
          <p className={`text-xl font-bold mt-1 ${gainPositive ? 'text-credit' : 'text-debit'}`}>
            {gainPositive ? '+' : ''}{formatINR(summary?.total_gain_loss ?? 0)}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] text-slate-500">Return</p>
          <p className={`text-xl font-bold mt-1 ${gainPositive ? 'text-credit' : 'text-debit'}`}>
            {gainPositive ? '+' : ''}{(summary?.total_gain_loss_pct ?? 0).toFixed(2)}%
          </p>
        </div>
      </div>

      {/* ── Add holding ──────────────────────────────────────────────────── */}
      <form onSubmit={handleAdd} className="card mb-5 p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-[10px] text-slate-500 mb-1">Symbol</label>
          <input required value={form.symbol} onChange={e => setForm(f => ({ ...f, symbol: e.target.value }))}
            placeholder="RELIANCE" className="input-field text-sm w-32"/>
        </div>
        <div>
          <label className="block text-[10px] text-slate-500 mb-1">Exchange</label>
          <select value={form.exchange} onChange={e => setForm(f => ({ ...f, exchange: e.target.value }))}
            className="input-field text-sm w-24">
            <option value="NSE">NSE</option><option value="BSE">BSE</option>
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-slate-500 mb-1">Quantity</label>
          <input required type="number" min="0.01" step="0.01" value={form.quantity}
            onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
            className="input-field text-sm w-28"/>
        </div>
        <div>
          <label className="block text-[10px] text-slate-500 mb-1">Avg buy price</label>
          <input required type="number" min="0.01" step="0.01" value={form.avg_buy_price}
            onChange={e => setForm(f => ({ ...f, avg_buy_price: e.target.value }))}
            className="input-field text-sm w-28"/>
        </div>
        <button type="submit" disabled={submitting} className="btn-primary text-sm">
          {submitting ? <Spinner size={14}/> : <><i className="ti ti-plus"/> Add holding</>}
        </button>
      </form>

      {/* ── Holdings table ───────────────────────────────────────────────── */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-paper text-[11px] text-slate-500">
            <tr>
              <th className="text-left px-4 py-2">Symbol</th>
              <th className="text-right px-4 py-2">Qty</th>
              <th className="text-right px-4 py-2">Avg buy</th>
              <th className="text-right px-4 py-2">Price</th>
              <th className="text-right px-4 py-2">Current value</th>
              <th className="text-right px-4 py-2">Gain / loss</th>
              <th className="px-4 py-2"/>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {(summary?.holdings ?? []).length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-slate-400 text-sm">
                No holdings yet — add one above.
              </td></tr>
            ) : summary.holdings.map(h => {
              const live = livePrices[h.symbol];
              const price = live?.price ?? h.current_price;
              const isLive = live ? live.is_live : h.is_live;
              const gain = h.quantity * price - h.invested_value;
              const positive = gain >= 0;
              return (
                <tr key={h.id} className="hover:bg-paper">
                  <td className="px-4 py-2.5 font-medium text-ink">
                    {h.symbol}
                    <span className="ml-1.5 text-[10px] text-slate-400">{h.exchange}</span>
                  </td>
                  <td className="px-4 py-2.5 text-right">{h.quantity}</td>
                  <td className="amount px-4 py-2.5">{formatINR(h.avg_buy_price)}</td>
                  <td className="px-4 py-2.5 text-right">
                    {formatINR(price)}
                    <span className={`ml-1.5 inline-block h-1.5 w-1.5 rounded-full ${isLive ? 'bg-credit' : 'bg-warn'}`}
                          title={isLive ? 'Live price' : 'Fallback price (feed unavailable)'}/>
                  </td>
                  <td className="amount px-4 py-2.5">{formatINR(h.quantity * price)}</td>
                  <td className={`px-4 py-2.5 text-right font-medium ${positive ? 'text-credit' : 'text-debit'}`}>
                    {positive ? '+' : ''}{formatINR(gain)}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <button onClick={() => handleRemove(h.id)} className="text-slate-400 hover:text-debit">
                      <i className="ti ti-trash"/>
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
