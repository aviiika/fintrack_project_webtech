/**
 * Category tints. Fourteen categories don't each get their own hue: that is how a
 * dark UI turns into confetti. Instead the palette's own colours are grouped by
 * meaning, and the icon plus the label do the rest of the telling-apart.
 *   slate  : everyday spending (Medium Slate Blue tint, Periwinkle text)
 *   sky    : needs and bills (Columbia Blue)
 *   mint   : money working for you or coming in (Celadon)
 *   rose   : obligations (EMIs)
 *   mute   : unsorted
 */
const T = {
  slate: 'bg-slateblue/20 text-periwinkle',
  sky:   'bg-columbia/10 text-columbia',
  mint:  'bg-celadon/15 text-celadon',
  rose:  'bg-debit/15 text-debit',
  mute:  'bg-surface-2 text-slate-500',
};
const P = {
  'Food & Dining':T.slate, 'Groceries':T.sky,
  'Transport':T.slate,     'Utilities':T.sky,
  'Entertainment':T.slate, 'Shopping':T.sky,
  'Health':T.sky,          'Education':T.slate,
  'Rent & Housing':T.sky,  'EMI / Loans':T.rose,
  'Investments':T.mint,    'Income':T.mint,
  'Transfers':T.mute,      'Uncategorized':T.mute,
};
/** Tabler icon per category — used for the round icon beside a transaction row. */
const ICONS = {
  'Food & Dining':'ti-motorbike', 'Groceries':'ti-shopping-cart',
  'Transport':'ti-car', 'Utilities':'ti-bolt',
  'Entertainment':'ti-device-tv', 'Shopping':'ti-shopping-bag',
  'Health':'ti-heartbeat', 'Education':'ti-school',
  'Rent & Housing':'ti-home', 'EMI / Loans':'ti-receipt',
  'Investments':'ti-trending-up', 'Income':'ti-cash',
  'Transfers':'ti-transfer', 'Uncategorized':'ti-help-circle',
};

export function categoryIcon(category) {
  return ICONS[category] || 'ti-circle-dashed';
}

export function CategoryPill({ category }) {
  const c = P[category] || T.mute;
  return <span className={`cat-pill ${c}`}>{category || 'Uncategorized'}</span>;
}

/** Hex colours for Recharts (which needs real colours, not Tailwind classes).
 *  Index-stable so the donut and bars agree. The first four are the brand colours
 *  in the order that separates best on Rich Black; the rest are lightness steps
 *  and the two functional hues (rose, sand), so eight bars never repeat. */
export const CHART_COLORS = [
  '#6666FF', '#B9F0D7', '#B8BAFF', '#C9E8FF', '#4848D6',
  '#7FD9B5', '#FF9AAE', '#FFD08A', '#8E90E0', '#6B6D99',
];
export function formatINR(a) {
  return new Intl.NumberFormat('en-IN', { style:'currency', currency:'INR', maximumFractionDigits:0 }).format(a);
}
