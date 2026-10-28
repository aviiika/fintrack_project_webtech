/**
 * Recharts ships light-theme defaults (grey ticks, a white tooltip card). These
 * shared props bring every chart onto the night-ledger palette, so a page opts in
 * with a spread instead of repeating hex codes.
 */
import { createElement } from 'react';

export const GRID = '#2A2A44';     // line
export const AXIS = '#9A9CCF';     // slate-500, 6.9:1 on the panel surface

export const axisProps = {
  tick: { fill: AXIS, fontSize: 11 },
  stroke: GRID,
  tickLine: false,
};

export const tooltipProps = {
  contentStyle: {
    background: '#1C1C30', border: '1px solid #2A2A44', borderRadius: 2,
    color: '#EEF1FF', fontSize: 12,
  },
  labelStyle: { color: '#B8BAFF', marginBottom: 2 },
  itemStyle: { color: '#EEF1FF' },
  cursor: { fill: 'rgba(102,102,255,.10)' },
};

export const legendProps = {
  wrapperStyle: { fontSize: 11 },
  formatter: value => createElement('span', { style: { color: AXIS } }, value),
};

// Semantic series colours, so "income" is the same colour on every chart.
export const SERIES = {
  income: '#B9F0D7',      // Celadon
  spending: '#FF9AAE',    // rose
  neutral: '#B8BAFF',     // Periwinkle
};
