/**
 * Month selector used by Dashboard, Transactions and Reports.
 *
 * A native <input type="month"> handles keyboard entry, locale formatting and
 * mobile pickers for free, so the only thing worth adding is prev/next stepping
 * — which is how people actually move through months.
 */
function shift(month, delta) {
  const [y, m] = month.split('-').map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

export default function MonthPicker({ value, onChange, className = '' }) {
  return (
    <div className={`flex items-center gap-1 ${className}`}>
      <button type="button" onClick={() => onChange(shift(value, -1))}
        aria-label="Previous month"
        className="rounded-sm border border-line bg-surface px-2 py-1 text-slate-500 hover:bg-surface-2">
        <i className="ti ti-chevron-left text-sm"/>
      </button>
      <input type="month" value={value} onChange={e => e.target.value && onChange(e.target.value)}
        aria-label="Month"
        className="input-field py-1 text-xs"/>
      <button type="button" onClick={() => onChange(shift(value, 1))}
        aria-label="Next month"
        className="rounded-sm border border-line bg-surface px-2 py-1 text-slate-500 hover:bg-surface-2">
        <i className="ti ti-chevron-right text-sm"/>
      </button>
    </div>
  );
}
