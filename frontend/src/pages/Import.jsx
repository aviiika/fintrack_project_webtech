import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { financeService } from '../api/financeService.js';
import ErrorBanner from '../components/ErrorBanner.jsx';
import Spinner from '../components/Spinner.jsx';

/** Date-format hints shown under each bank, so the user can sanity-check their
 *  CSV before uploading rather than after a parse failure. */
const HINTS = {
  hdfc: 'dd/mm/yy format', sbi: 'dd MMM yyyy', icici: 'dd/mm/yyyy',
  axis: 'dd-mm-yyyy', kotak: 'dd-mm-yyyy', paytm: 'yyyy-mm-dd',
};
const MAX_MB = 10;

export default function Import() {
  const [banks, setBanks] = useState([]);
  const [bank, setBank] = useState('');
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const loadMeta = useCallback(async () => {
    try {
      const [b, h] = await Promise.all([
        financeService.banks(),
        financeService.importHistory().catch(() => []),
      ]);
      setBanks(b);
      setHistory(h);
      if (b.length && !bank) setBank(b[0].key);
    } catch (err) { setError(err.message || 'Could not load bank list.'); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { loadMeta(); }, [loadMeta]);

  /** Shared by drop and browse — one place to validate, so a dropped file can't
   *  skip the checks a browsed file goes through. */
  const acceptFile = (f) => {
    setError(''); setResult(null);
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.csv')) {
      setError('Only .csv files are supported.'); return;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`File is ${(f.size / 1024 / 1024).toFixed(1)} MB — the limit is ${MAX_MB} MB.`); return;
    }
    setFile(f);
  };

  const handleDrop = (e) => {
    e.preventDefault(); setDragging(false);
    acceptFile(e.dataTransfer.files?.[0]);
  };

  const handleUpload = async () => {
    if (!file || !bank) return;
    setUploading(true); setError(''); setResult(null); setProgress(0);
    try {
      const r = await financeService.upload(file, bank, setProgress);
      setResult(r);
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
      setHistory(await financeService.importHistory().catch(() => history));
    } catch (err) {
      setError(err.message || 'Import failed.');
    } finally { setUploading(false); }
  };

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-ink">Import bank statement</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Upload a CSV exported from your bank. Transactions are parsed, de-duplicated,
          and categorised automatically by the ML model.
        </p>
      </div>

      <ErrorBanner message={error} />

      {result && (
        <div className="mb-5 rounded-sm border border-credit/40 bg-credit/10 p-4">
          <p className="flex items-center gap-2 text-sm font-medium text-credit">
            <i className="ti ti-circle-check"/> {result.message}
          </p>
          <div className="mt-2 flex gap-5 text-xs text-credit">
            <span><strong>{result.parsed}</strong> rows parsed</span>
            <span><strong>{result.added}</strong> added</span>
            <span><strong>{result.skipped}</strong> duplicates skipped</span>
          </div>
          <div className="mt-3 flex gap-2">
            <Link to="/transactions" className="btn-primary text-xs py-1.5 px-3">
              <i className="ti ti-list"/> Review transactions
            </Link>
            <Link to="/dashboard" className="btn-ghost text-xs py-1.5 px-3">
              <i className="ti ti-layout-dashboard"/> Go to dashboard
            </Link>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="col-span-2 flex flex-col gap-5">
          {/* ── Step 1: bank ──────────────────────────────────────────────── */}
          <div className="card p-5">
            <p className="mb-3 text-sm font-medium text-ink">
              1. Select your bank <span className="ml-1 text-[11px] text-debit">required</span>
            </p>
            {banks.length === 0 ? <Spinner size={18} className="text-accent-text"/> : (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
                {banks.map(b => (
                  <button key={b.key} onClick={() => setBank(b.key)} type="button"
                    className={`flex items-center gap-2.5 rounded-sm border p-2.5 text-left transition-colors ${
                      bank === b.key
                        ? 'border-accent bg-brand-50 ring-1 ring-accent/40'
                        : 'border-line hover:bg-paper'
                    }`}>
                    <span className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-sm text-xs font-bold ${
                      bank === b.key ? 'bg-brand-600 text-white' : 'bg-surface-2 text-slate-500'
                    }`}>
                      {b.key.slice(0, 2).toUpperCase()}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-xs font-medium text-ink">{b.name}</span>
                      <span className="block text-[10px] text-slate-400">{HINTS[b.key] || 'auto-detected'}</span>
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* ── Step 2: file ──────────────────────────────────────────────── */}
          <div className="card p-5">
            <p className="mb-3 text-sm font-medium text-ink">
              2. Upload file <span className="ml-1 text-[11px] text-debit">required</span>
            </p>
            <div
              onDragOver={e => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
              role="button" tabIndex={0}
              onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
              className={`flex cursor-pointer flex-col items-center justify-center rounded-sm border-2 border-dashed p-10 transition-colors ${
                dragging ? 'border-accent bg-brand-50' : 'border-line hover:border-accent/70 hover:bg-surface-2'
              }`}>
              <i className={`ti ${file ? 'ti-file-check' : 'ti-cloud-upload'} mb-2 text-3xl ${
                file ? 'text-credit' : 'text-slate-400'}`}/>
              {file ? (
                <>
                  <p className="text-sm font-medium text-ink">{file.name}</p>
                  <p className="mt-0.5 text-[11px] text-slate-400">
                    {(file.size / 1024).toFixed(1)} KB · click to pick a different file
                  </p>
                </>
              ) : (
                <>
                  <p className="text-sm text-slate-600">Drag &amp; drop CSV here</p>
                  <p className="mt-0.5 text-[11px] text-slate-400">
                    or click to browse · .csv files only · max {MAX_MB} MB
                  </p>
                </>
              )}
              <input ref={inputRef} type="file" accept=".csv,text/csv" className="hidden"
                onChange={e => acceptFile(e.target.files?.[0])}/>
            </div>

            {uploading && (
              <div className="mt-3">
                <div className="budget-bar-bg">
                  <div className="h-2 rounded-full bg-brand-500 transition-all" style={{ width: `${progress}%` }}/>
                </div>
                <p className="mt-1 text-[11px] text-slate-400">Uploading… {progress}%</p>
              </div>
            )}

            <button onClick={handleUpload} disabled={!file || !bank || uploading}
              className="btn-primary mt-4 w-full text-sm">
              {uploading
                ? <><Spinner size={14}/> Importing…</>
                : <><i className="ti ti-upload"/> Import transactions</>}
            </button>
          </div>
        </div>

        {/* ── Recent imports ──────────────────────────────────────────────── */}
        <div className="card p-5">
          <p className="mb-3 text-sm font-medium text-ink">Recent imports</p>
          {history.length === 0 ? (
            <p className="text-xs text-slate-400">Nothing imported yet.</p>
          ) : (
            <div className="flex flex-col gap-3">
              {history.map(h => (
                <div key={h.id} className="flex items-start gap-2.5">
                  <i className="ti ti-file-spreadsheet mt-0.5 text-base text-slate-400"/>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium text-ink">{h.filename}</p>
                    <p className="text-[10px] text-slate-400">
                      {h.bank.toUpperCase()} · {h.rows_added}/{h.rows_parsed} rows ·{' '}
                      {new Date(h.imported_at).toLocaleDateString('en-IN',
                        { day: 'numeric', month: 'short' })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="mt-5 rounded-sm bg-paper p-3">
            <p className="text-[11px] font-medium text-slate-600">
              <i className="ti ti-info-circle mr-1"/>Duplicate protection
            </p>
            <p className="mt-1 text-[10px] leading-relaxed text-slate-500">
              Re-importing the same statement is safe. Rows are matched on date,
              description and amount, so overlapping exports only add what&apos;s new.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
