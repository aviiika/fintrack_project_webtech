# FinTrack Pro

ML-augmented personal finance platform — multi-bank CSV ingestion, adaptive transaction
categorisation with a human-in-the-loop feedback loop, statistical anomaly detection,
spending forecasts, a live stock portfolio over WebSockets, and net worth tracking.

## What's new in Pro (vs base FinTrack)

| Capability | Base | Pro |
|---|---|---|
| Transaction categorisation | Keyword rules only | **TF-IDF + Logistic Regression**, with keyword fallback |
| User corrections | Just updates the row | **Feed back as training labels (weighted 2x)**, auto-retrain every 25 |
| Anomaly detection | Not available | **Z-score outliers** vs user's own category history |
| Spending forecast | Not available | **Linear-trend projection** of month-end total |
| Model observability | Not available | **Model Insights page** — accuracy, F1 per class, retrain button, live predict preview |
| Model versioning | Not applicable | **Registry.json pointer** + versioned .joblib artifacts (free rollback) |
| Stock portfolio | Not available | **Holdings marked to market** via yfinance, with gain/loss roll-up |
| Price delivery | Not applicable | **WebSocket push** (`/ws/prices`) — no polling |
| Caching | None | **TTL cache** in front of the price feed (Redis-shaped API) |
| Net worth | Not available | **Cash + investments - liabilities**, with daily snapshot history |
| Loans / EMIs | Not available | **Reducing-balance amortization**, outstanding derived on read |
| Background work | None | **APScheduler**: price warmup, nightly snapshot, nightly retrain sweep |
| Export | None | **Multi-sheet .xlsx** + CSV, generated server-side |
| Bundle | One 638 kB chunk | **Route-level code splitting** — 228 kB initial, charts load on demand |
| Offline | None | **PWA**: installable, offline app shell, API never cached (see below) |
| Hardening | FastAPI defaults | **Security headers + sliding-window login rate limit** |

## Architecture

```
backend/app/
├── ml/                                 ← NEW: all ML lives here, isolated
│   ├── features/text_features.py       ← Noise stripping (UPI refs, bank codes)
│   ├── training/train_categoriser.py   ← Standalone training script
│   ├── inference/
│   │   ├── categoriser_service.py      ← Class-aware confidence gating + rules fallback
│   │   ├── backfill.py                 ← Re-predict rows imported before a model existed
│   │   ├── anomaly_service.py          ← Z-score outlier detection
│   │   └── forecast_service.py         ← Linear-trend spend projection
│   ├── registry.py                     ← Active model registry + rollback helper
│   └── models/                         ← Versioned .joblib artifacts (gitignored)
├── background/
│   └── scheduler.py                    ← NEW: APScheduler jobs (price warmup, snapshots, retrain)
├── models/
│   ├── correction_counter.py           ← NEW: tracks corrections, triggers retrain
│   ├── stock_holding.py                ← NEW: a position in one listed stock
│   ├── liability.py                     ← NEW: loan terms (outstanding is derived, not stored)
│   └── networth_snapshot.py            ← NEW: daily net worth reading (built by scheduler)
├── routes/
│   ├── ml.py                           ← NEW: /api/v1/ml/* endpoints
│   ├── portfolio.py                    ← NEW: holdings CRUD + /ws/prices WebSocket
│   ├── loans.py                        ← NEW: /api/v1/loans/*
│   └── networth.py                     ← NEW: /api/v1/networth/*
└── services/
    ├── transaction_service.py          ← Enhanced: ML predict, feedback loop, auto-retrain
    ├── cache_service.py                ← NEW: TTL cache (stands in for Redis)
    ├── stock_service.py                ← NEW: yfinance wrapper, cached, degrades gracefully
    ├── portfolio_service.py            ← NEW: mark-to-market + gain/loss roll-up
    ├── loan_service.py                 ← NEW: EMI formula + reducing-balance amortization
    └── networth_service.py             ← NEW: assets - liabilities, snapshot persistence
```

## ML Pipeline

```
┌────────────────────────────────────────────────────────────────────┐
│ 1. CSV import  →  predict_batch() categorises every row            │
│    if ML confidence >= 0.55: use ML prediction                     │
│    else: fall back to keyword rules                                │
│                                                                     │
│ 2. User sees wrong category, clicks edit, picks correct one        │
│    → user_corrected=True, category_source="manual"                 │
│    → correction counter increments                                 │
│                                                                     │
│ 3. Every 25 corrections → auto-retrain fires                       │
│    → user-corrected rows weighted 2x in training                   │
│    → new model.joblib saved, registry.json updated                 │
│    → inference cache invalidated, new model goes live immediately  │
│                                                                     │
│ 4. Next import uses the improved model → fewer corrections needed  │
└────────────────────────────────────────────────────────────────────┘
```

## Calibrating the confidence gate — a bug worth describing

The inference layer defers to keyword rules whenever the model isn't confident
("selective prediction"). The threshold was originally a hardcoded `0.55`.

That number is quietly wrong, and the failure is silent. With 13 categories a
uniform guess sits at `1/13 = 0.077`, and a real prediction on short, noisy bank
descriptions peaks around `0.30–0.35`. Measured across the whole seeded corpus
the **maximum confidence any row achieved was 0.34** — so the gate could never
open. The model trained successfully, reported 64% accuracy on the Model
Insights page, and then never once decided a category. Everything was "working";
the ML layer was dead code.

The fix is to scale the gate to the class count instead of hardcoding it:

```
threshold = clamp(multiplier / n_classes, floor, ceiling)     # 2.5 / 13 = 0.19
```

plus a **margin check**: top-1 must beat top-2 by `ml_confidence_margin`.
Probability mass alone can't tell "clearly Groceries" from "a coin-flip between
Groceries and Food & Dining that landed a basis point apart" — and a coin flip
should defer to the rules, not be reported as an ML decision.

Measured effect on the seeded data: **29 of 70 rows claimed by the model, with
0 re-categorised** — i.e. it now speaks exactly where it already agreed with the
hand-written rules, and stays quiet everywhere else. `tests/test_ml_confidence.py`
pins this, including an explicit regression test that the 13-class threshold sits
below what the model can actually produce.

The lesson generalises: a magic constant that encodes an unstated assumption
(here, "binary classifier") fails silently rather than loudly.

## Live price flow (Week 2)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Browser opens ONE WebSocket: /api/v1/ws/prices?token=<jwt>          │
│   (a WS handshake can't set an Authorization header, so the JWT     │
│    rides as a query param and is validated by the same decoder)     │
│                      ↓                                               │
│ Server loop, every ws_push_interval_seconds (default 5s):           │
│   read user's holdings → get_prices(symbols) → push one JSON frame  │
│                      ↓                                               │
│ get_prices() is cache-aside: TTL cache (60s) in front of yfinance,  │
│   so 12 pushes/minute collapse to 1 upstream call per symbol        │
│                      ↓                                               │
│ If the upstream fails (no internet, rate-limited, delisted symbol): │
│   serve a deterministic fallback price with is_live=false           │
│   → the UI shows an amber dot instead of green; never a 500         │
└─────────────────────────────────────────────────────────────────────┘
```

Two details worth pointing at in a viva:
- `get_prices` is blocking I/O, so the WebSocket loop hands it to a thread via
  `asyncio.to_thread` — otherwise one slow upstream call freezes the event loop for
  *every* connected client, and it freezes worst exactly when the feed is slowest.
- Jobs that touch the network (price warmup) run in the scheduler, never in a request
  handler, so no user-facing request ever waits on Yahoo Finance.

## Net worth & loans (Week 3)

Outstanding loan balance is **never stored as a column** — it's recomputed from the
loan terms on every read using the reducing-balance formula. That means there's no
"update the outstanding balance every month" job that can be forgotten, fail silently,
or drift out of sync with reality. The trade-off (a loop per loan per read) is trivially
cheap at this scale and buys correctness-by-construction.

EMI math is deliberately *not* machine learning — same reasoning as using z-scores for
anomaly detection rather than another model. A loan ledger has to be deterministic and
hand-checkable; a closed-form formula is the right tool, and knowing when *not* to reach
for ML is part of the argument this project makes.

## Week 4 — PWA, code splitting, hardening

**Route-level code splitting.** Every authenticated page is `React.lazy`-loaded.
Recharts alone is ~350 kB and only four pages render charts, so eager loading
made the *login screen* pay for charting code it never uses. Login is
deliberately not lazy — it's the first paint for a signed-out visitor, so
splitting it would be a regression.

| | Before | After |
|---|---|---|
| Initial JS | 638 kB (one chunk, size warning) | **228 kB** (76 kB gzipped) |
| Charts | always loaded | separate 351 kB chunk, on demand |
| Per-page chunks | — | 5–34 kB each |

**PWA.** Installable with a manifest, maskable icons and an offline app shell.
The caching policy is the part worth defending: hashed static assets are
cache-first (a new build produces a new URL, so a cached file can never be
stale), but **`/api/*` is never cached**. Serving a stale balance or a stale
holding price from disk is worse than showing an error, so API traffic always
hits the network and fails honestly when offline. The service worker registers
in production builds only — in dev it would serve stale modules and look exactly
like "my edit didn't apply".

**Security hardening** (`app/utils/security_middleware.py`), mapped to OWASP Top 10:

| Control | OWASP | Note |
|---|---|---|
| `X-Frame-Options: DENY`, `frame-ancestors 'none'` | A05 | Clickjacking |
| `X-Content-Type-Options: nosniff` | A05 | MIME confusion |
| `Content-Security-Policy: default-src 'none'` | A05 | Strictest possible — this API serves only JSON |
| `Referrer-Policy: strict-origin-when-cross-origin` | A01 | Stops URL-embedded IDs leaking cross-site |
| `Strict-Transport-Security` | A02 | No silent HTTP downgrade |
| Sliding-window login rate limit | A07 | 10 attempts / 5 min / IP |
| Per-user query scoping (pre-existing) | A01 | Every query filters on `owner_id` |

The rate limiter uses a **sliding** window, not a fixed one: a fixed per-minute
counter lets an attacker send `limit` requests at 11:59:59 and `limit` more at
12:00:00 — double the intended rate across the boundary. Keeping the actual
timestamps and expiring them individually closes that gap. It's in-memory, so it
resets on restart and isn't shared between workers; that's an honest limitation
of single-process deployment, and the fix is the same shape as the price cache
(move the deque into Redis).

## Quick start (Windows)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\dev.ps1 install
copy backend\.env.example backend\.env
.\dev.ps1 seed       # creates demo user + trains initial model
.\dev.ps1 dev        # opens both servers
```

Open http://localhost:5173, log in with `demo@fintrack.app` / `demo12345`.
All **eight** pages are implemented and wired to live endpoints:

| Page | What it does |
|---|---|
| Dashboard | Metrics, category bars, donut, daily trend, recent transactions, CSV export |
| Import CSV | Bank picker, drag-and-drop upload with progress, import history, duplicate protection |
| Transactions | Search / filter / paginate, **inline category edit** (drives the ML feedback loop), ML-vs-rules badges |
| Reports | Annual income-vs-spend, savings trend, top categories, budget tracker, 3 export formats |
| Model Insights | Accuracy, sample count, retrain button, live predict box, forecast, anomalies |
| Portfolio | Holdings marked to market, live WebSocket price feed |
| Net Worth | Assets − liabilities, snapshot history chart, liability breakdown |
| Loans & EMIs | Reducing-balance amortization, live EMI preview while typing |

The seed creates a demo user with 70 transactions across **three** bank formats
(HDFC / SBI / ICICI), 4 stock holdings, 2 loans, 7 budgets, and trains an initial
ML model — so every page has real data on first run.

### Demo path for a viva

1. **Transactions** — point at the green `ML 29%` and amber `Rules` badges side by
   side. That's the confidence gate deciding, per row, whether the model is
   trusted. Hover a badge for the reason.
2. Click any category pill, change it. Watch the correction counter tick
   (`0/25 → 1/25`) and the badge flip to `You`. That row now trains at 2x weight.
3. **Model Insights** — type a description into "Try the model" and hit Predict:
   it shows the predicted category, the source, and the confidence.
4. **Portfolio** — the "Live feed connected" dot is a real WebSocket pushing ticks.
5. **Net Worth** — hit "Snapshot today" to run, on demand, the same job the
   nightly scheduler performs.

### Offline / no-internet behaviour

Stock prices come from Yahoo Finance via yfinance. If that's unreachable (campus
firewall, no internet during a viva), the app does **not** break: `stock_service`
falls back to deterministic per-symbol prices and marks them `is_live: false`, which
renders as an amber dot next to the price instead of green. Everything else —
portfolio maths, net worth, charts — works identically.

## Key API endpoints (NEW in Pro)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/ml/model-info` | Active model metadata (accuracy, F1, classes) |
| GET | `/api/v1/ml/versions` | All saved model artifacts (newest first) |
| POST | `/api/v1/ml/predict` | Preview a prediction for a description |
| POST | `/api/v1/ml/retrain` | Manually trigger retraining |
| GET | `/api/v1/ml/correction-status` | Corrections remaining until auto-retrain |
| GET | `/api/v1/ml/anomalies` | Statistical outliers (z-score > 2.5) |
| GET | `/api/v1/ml/forecast` | Month-end spend projection |
| GET | `/api/v1/portfolio/holdings` | List stock holdings |
| POST | `/api/v1/portfolio/holdings` | Add a holding |
| DELETE | `/api/v1/portfolio/holdings/{id}` | Remove a holding |
| GET | `/api/v1/portfolio/summary` | Holdings marked to market + gain/loss roll-up |
| WS | `/api/v1/ws/prices?token=<jwt>` | **WebSocket** live price stream |
| GET | `/api/v1/loans` | Loans with derived amortization schedule |
| POST | `/api/v1/loans` | Add a loan (EMI computed server-side) |
| DELETE | `/api/v1/loans/{id}` | Remove a loan |
| GET | `/api/v1/networth` | Assets - liabilities, with breakdown |
| GET | `/api/v1/networth/history` | Snapshot time series (built by scheduler) |
| POST | `/api/v1/networth/snapshot` | Take today's snapshot on demand |
| GET | `/api/v1/transactions/months` | Months that contain data (UI lands on one of these) |
| GET | `/api/v1/export/transactions.csv` | CSV export, optional `?month=` |
| GET | `/api/v1/export/report.xlsx` | Multi-sheet workbook (transactions, pivot, summary) |

## Configuration (new settings)

| Setting | Default | Purpose |
|---|---|---|
| `stock_price_cache_ttl_seconds` | 60 | How long a fetched price stays cached |
| `ws_push_interval_seconds` | 5 | How often the WebSocket pushes a tick |
| `networth_snapshot_hour` | 2 | UTC hour for the nightly snapshot job |
| `enable_background_jobs` | true | Set false to run without the scheduler (tests do this) |
| `ml_confidence_multiplier` | 2.5 | Gate = this x random baseline (1 / n_classes) |
| `ml_confidence_floor` / `_ceiling` | 0.15 / 0.60 | Clamp on the computed gate |
| `ml_confidence_margin` | 0.04 | Top-1 must beat top-2 by this much |
| `ml_min_training_samples` | 50 | Below this, training refuses and rules stay in charge |
| `ml_retrain_every_n_corrections` | 25 | Auto-retrain trigger |

## Testing

```powershell
.\dev.ps1 test
# 57 tests pass
```

| Area | Tests |
|---|---|
| ML categoriser | 11 (model info, insufficient data, training, predict, feedback loop) |
| ML confidence gating | 7 (class scaling, floor/ceiling, near-tie veto, reachability regression) |
| ML backfill | 3 (no-op without model, assigns ML source, **never overwrites a correction**) |
| Text features | 6 (UPI refs, bank codes, handles, empty input) |
| Portfolio | 6 (CRUD, gain/loss maths, auth, 404 on foreign row) |
| Loans | 6 (EMI vs known values, zero-interest, fresh vs part-paid schedule, API) |
| Net worth | 3 (empty case, three-way combination, snapshot upsert + history) |
| Exports | 4 (CSV header/rows, month filter, valid workbook, auth) |
| Security | 6 (headers, brute-force block, Retry-After, sliding window, key isolation) |
| Base (imports, transactions, budgets) | 5 |

Stock prices are mocked via the `mock_stock_prices` fixture and the scheduler is
disabled (`enable_background_jobs=False`), so the suite is deterministic and runs
fully offline. The login rate limiter is reset between tests by an autouse
fixture — it's a process-wide singleton, and without the reset the shared
`testclient` IP exhausts the window partway through the run.

## Known limitations

Stated plainly, because knowing them is part of the work:

- **Model accuracy is 64%** on 68 seeded samples across 13 categories. That's a
  small-data number, not a ceiling — the feedback loop is the mechanism by which
  it improves, and each correction trains at 2x weight.
- **Rate limiter and price cache are in-memory**, so they reset on restart and
  aren't shared across workers. Both are written against a get/set interface so
  moving them to Redis is a one-file change.
- **Cash balance is derived from imported transactions**, not a live bank feed,
  so it's only as complete as the statements imported.
- **Anomaly detection needs ≥5 transactions in a category** before z-scores mean
  anything; below that it stays silent rather than flagging noise.
- **Offline stock prices are reference-anchored estimates**, flagged
  `is_live: false` and rendered with an amber dot. They are never presented as
  real quotes.
