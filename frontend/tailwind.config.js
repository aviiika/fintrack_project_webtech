export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: { extend: {
    colors: {
      // The five brand colours, exactly as supplied.
      slateblue:  '#6666FF',   // Medium Slate Blue
      periwinkle: '#B8BAFF',
      columbia:   '#C9E8FF',   // Columbia Blue
      richblack:  '#0C0C16',   // Rich Black
      celadon:    '#B9F0D7',

      // Roles. Pages use these names, never raw hex, so the whole app re-themes
      // from this one block.
      paper:   '#0C0C16',                                  // app background: Rich Black
      surface: { DEFAULT:'#141424', 2:'#1C1C30' },         // panels / raised + inputs
      spine:   '#11111F',                                  // sidebar
      line:    '#2A2A44',                                  // hairlines
      ink:     '#EEF1FF',                                  // primary text (17:1 on paper)
      accent:  { DEFAULT:'#6666FF', soft:'#C9E8FF', text:'#B8BAFF' }, // fills / highlights / text-safe
      credit:  '#B9F0D7',   // Celadon: money in, verified, healthy
      debit:   '#FF9AAE',   // soft rose: money out, over budget (the one off-palette hue)
      warn:    '#FFD08A',   // sand: low-confidence, nearing a limit

      // `brand-*` is the Medium Slate Blue ramp. Low numbers are dark tints for
      // highlight backgrounds on a dark UI; 500 is the exact brand colour; 600 is
      // a half-step deeper so white button text clears 4.5:1 (it is 4.3:1 on 500).
      brand: {
        50:'#15153C', 100:'#1E1E52', 200:'#2E2E7A', 300:'#4343C9',
        400:'#5555F0', 500:'#6666FF', 600:'#5B5BF2', 700:'#4848D6', 800:'#3A3AB0',
      },
      // Re-pointed so every existing `text-slate-*` / `bg-slate-*` in the pages
      // lands on a readable dark-theme tone: 400-600 are text (>= 4.8:1 on any
      // surface), 100-300 are fills and rules.
      slate: {
        50:'#101020', 100:'#1C1C30', 200:'#2A2A44', 300:'#4A4A73',
        400:'#8587B8', 500:'#9A9CCF', 600:'#B8BAFF', 700:'#C9E8FF',
        800:'#E4E8FF', 900:'#EEF1FF',
      },
    },
    fontFamily: {
      sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
      mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
    },
  }}, plugins: [],
};
