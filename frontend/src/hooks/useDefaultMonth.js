import { useEffect, useState } from 'react';
import { financeService } from '../api/financeService.js';

const thisMonth = () => new Date().toISOString().slice(0, 7);

/**
 * Picks the month a page should open on: the most recent month that actually
 * has transactions, falling back to the current month when the ledger is empty.
 *
 * Without this, someone importing statements from a few months back opens the
 * app on today's month, sees zeroes everywhere, and reasonably concludes the
 * import didn't work.
 *
 * Returns [month, setMonth, ready]. `ready` is false until the month list has
 * resolved, so a page can avoid firing a request for the wrong month first and
 * then immediately re-fetching for the right one.
 */
export function useDefaultMonth() {
  const [month, setMonth] = useState(thisMonth);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    financeService.months()
      .then((months) => {
        if (cancelled) return;
        // Don't jump the user forward past today if they have future-dated rows.
        const usable = months.filter((m) => m <= thisMonth());
        if (usable.length) setMonth(usable[0]);
        else if (months.length) setMonth(months[0]);
      })
      .catch(() => { /* keep the current-month default */ })
      .finally(() => { if (!cancelled) setReady(true); });
    return () => { cancelled = true; };
  }, []);

  return [month, setMonth, ready];
}
