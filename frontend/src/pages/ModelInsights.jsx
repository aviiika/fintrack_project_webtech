import { useCallback, useEffect, useState } from 'react';
import { mlService } from '../api/mlService.js';
import { CategoryPill, formatINR } from '../components/CategoryPill.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';
import Spinner from '../components/Spinner.jsx';

/** The ML Insights page — makes the model visible, demoable, and controllable. */
export default function ModelInsights() {
  const [info, setInfo] = useState(null);
  const [status, setStatus] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [error, setError] = useState('');

  // Live prediction preview state
  const [previewText, setPreviewText] = useState('');
  const [previewTxnType, setPreviewTxnType] = useState('debit');
  const [previewResult, setPreviewResult] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [i, s, f, a] = await Promise.all([
        mlService.modelInfo(),
        mlService.correctionStatus().catch(() => null),
        mlService.forecast().catch(() => null),
        mlService.anomalies().catch(() => []),
      ]);
      setInfo(i); setStatus(s); setForecast(f); setAnomalies(a);
    } catch (err) {
      setError(err.message || 'Could not load model data.');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const handleRetrain = async () => {
    setRetraining(true); setError('');
    try {
      const r = await mlService.retrain();
      if (r.status === 'trained') await loadAll();
      else setError(r.message);
    } catch (err) { setError(err.message); }
    finally { setRetraining(false); }
  };

  const handlePredict = async () => {
    if (!previewText.trim()) return;
    setPreviewLoading(true);
    try {
      const r = await mlService.predict(previewText.trim(), previewTxnType);
      setPreviewResult(r);
    } catch (err) {
      setPreviewResult({ error: err.message });
    } finally { setPreviewLoading(false); }
  };

  if (loading) {
    return <div className="flex h-full items-center justify-center p-10"><Spinner size={28} className="text-accent-text"/></div>;
  }

  const isActive = info?.status === 'active';
  const accuracyPct = isActive ? Math.round(info.accuracy * 100) : null;

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-ink">Model Insights</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Live view of the transaction categoriser — accuracy, training data, and the human-in-the-loop feedback cycle.
        </p>
      </div>

      <ErrorBanner message={error} />

      {/* ── Top row: model status + feedback loop ──────────────────────── */}
      <div className="mb-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Model status card */}
        <div className="card col-span-2 p-5">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-xs text-slate-500 mb-1">Categoriser model</p>
              <div className="flex items-center gap-2">
                <span className={`inline-block h-2 w-2 rounded-full ${isActive ? 'bg-credit animate-pulse' : 'bg-warn'}`}/>
                <span className="font-semibold text-ink">
                  {isActive ? 'Active — ML + rules fallback' : 'No model yet — using keyword rules'}
                </span>
              </div>
            </div>
            <button onClick={handleRetrain} disabled={retraining}
              className="btn-primary text-xs py-1.5 px-3">
              {retraining ? <><Spinner size={14}/> Training...</> : <><i className="ti ti-refresh"/> Retrain now</>}
            </button>
          </div>

          {isActive ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <p className="text-[11px] text-slate-500">Accuracy</p>
                <p className="text-2xl font-bold text-credit mt-1">{accuracyPct}%</p>
              </div>
              <div>
                <p className="text-[11px] text-slate-500">Trained on</p>
                <p className="text-2xl font-bold text-ink mt-1">{info.trained_on_samples}<span className="text-xs text-slate-400 ml-1">samples</span></p>
              </div>
              <div>
                <p className="text-[11px] text-slate-500">Categories</p>
                <p className="text-2xl font-bold text-ink mt-1">{info.classes?.length || 0}</p>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500 mt-2">
              Import at least 50 transactions, then click Retrain to train your first model.
            </p>
          )}

          {isActive && info.trained_at && (
            <p className="mt-4 text-[10px] text-slate-400 border-t border-line pt-3">
              Last trained: {new Date(info.trained_at).toLocaleString('en-IN')}
              {info.active_model_path && <> · <span className="font-mono">{info.active_model_path.split('/').pop()}</span></>}
            </p>
          )}
        </div>

        {/* Feedback loop card */}
        <div className="card p-5">
          <p className="text-xs text-slate-500 mb-2">
            <i className="ti ti-arrow-back-up mr-1"/> Feedback loop
          </p>
          <p className="text-3xl font-bold text-accent-text">
            {status?.corrections_this_cycle ?? 0}
            <span className="text-sm text-slate-400 font-normal"> / {status?.threshold_for_retrain ?? 25}</span>
          </p>
          <p className="text-xs text-slate-500 mt-1">corrections until auto-retrain</p>

          <div className="budget-bar-bg mt-3">
            <div className="h-2 rounded-full bg-brand-500 transition-all"
                 style={{ width: `${Math.min(100, ((status?.corrections_this_cycle || 0) / (status?.threshold_for_retrain || 25)) * 100)}%` }}/>
          </div>

          <p className="text-[10px] text-slate-400 mt-3">
            {status?.total_lifetime_corrections ?? 0} total corrections across all cycles.
            Each correction trains the model to recognise your style.
          </p>
        </div>
      </div>

      {/* ── Live prediction preview ────────────────────────────────────── */}
      <div className="card mb-5 p-5">
        <p className="text-xs text-slate-500 mb-3">
          <i className="ti ti-wand mr-1"/> Try the model
        </p>
        <div className="flex gap-2">
          <input value={previewText} onChange={e => setPreviewText(e.target.value)}
            placeholder='Try: "Zomato Food Order" or "NEFT-Salary"'
            onKeyDown={e => e.key === 'Enter' && handlePredict()}
            className="input-field flex-1 text-sm"/>
          <select value={previewTxnType} onChange={e => setPreviewTxnType(e.target.value)}
            className="input-field w-24 text-sm">
            <option value="debit">Debit</option>
            <option value="credit">Credit</option>
          </select>
          <button onClick={handlePredict} disabled={previewLoading || !previewText.trim()}
            className="btn-primary text-sm">
            {previewLoading ? <Spinner size={14}/> : 'Predict'}
          </button>
        </div>

        {previewResult && !previewResult.error && (
          <div className="mt-4 flex items-center gap-4 p-3 rounded-sm bg-paper border border-line">
            <CategoryPill category={previewResult.category}/>
            <div className="flex-1">
              <p className="text-xs text-slate-500">
                Source: <code className={`font-mono text-[11px] px-1.5 py-0.5 rounded ${
                  previewResult.source === 'ml' ? 'bg-credit/15 text-credit' : 'bg-warn/15 text-warn'
                }`}>{previewResult.source}</code>
                {previewResult.confidence != null && <> · confidence <span className="font-mono">{(previewResult.confidence * 100).toFixed(0)}%</span></>}
              </p>
              {previewResult.rules_fallback_reason && (
                <p className="text-[11px] text-slate-400 mt-1 italic">{previewResult.rules_fallback_reason}</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Bottom row: forecast + anomalies ───────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Forecast */}
        <div className="card p-5">
          <p className="text-xs text-slate-500 mb-3">
            <i className="ti ti-trending-up mr-1"/> This month's spending forecast
          </p>
          {forecast?.projected_month_end != null ? (
            <>
              <p className="text-2xl font-bold text-ink">{formatINR(forecast.projected_month_end)}</p>
              <p className="text-xs text-slate-500 mt-1">
                Projected total — spent {formatINR(forecast.spent_so_far)} in {forecast.days_elapsed}/{forecast.days_in_month} days
                <br/>Daily rate: {formatINR(forecast.daily_rate || 0)}
              </p>
              {forecast.projected_overspend != null && forecast.projected_overspend > 0 && (
                <div className="mt-3 p-2 rounded-sm bg-debit/10 border border-debit/40 text-xs text-debit">
                  <i className="ti ti-alert-triangle mr-1"/>
                  Projected to exceed total budget by {formatINR(forecast.projected_overspend)}
                </div>
              )}
            </>
          ) : (
            <p className="text-xs text-slate-400">Not enough data yet — forecast kicks in after day 3 of the month.</p>
          )}
        </div>

        {/* Anomalies */}
        <div className="card p-5">
          <p className="text-xs text-slate-500 mb-3">
            <i className="ti ti-flag mr-1"/> Unusual transactions ({anomalies.length})
          </p>
          {anomalies.length === 0 ? (
            <p className="text-xs text-slate-400">No statistical outliers found. Your spending is consistent.</p>
          ) : (
            <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
              {anomalies.slice(0, 5).map(a => (
                <div key={a.id} className="flex items-start gap-2 text-xs">
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-ink">{a.description}</p>
                    <p className="text-[10px] text-slate-400">
                      {formatINR(a.amount)} · {a.times_above_average}x your typical ({formatINR(a.typical_amount)})
                    </p>
                  </div>
                  <span className="text-[10px] rounded-sm bg-warn/15 text-warn px-1.5 py-0.5 font-mono">
                    z={a.z_score}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
