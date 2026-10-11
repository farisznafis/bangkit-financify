# Financify

Short-term Indonesian city inflation forecasting + financial impact planning.

## What it does

Financify helps someone saving towards a goal (a laptop, a wedding, a down payment) see how rising prices in their city affect that goal.

1. **Inflation forecast:** pick a city and get next month's headline inflation (month-to-month), compared with the previous month and shown against the last 24 months, with the model's typical error.
2. **Financial impact:** enter savings, income, expenses and a goal. Financify estimates what the goal will cost after inflation and how long it takes to save for it.

## User flow

```
pick a city ──► Step 1: next-month forecast          ──► Step 2: savings plan
                 • predicted m-t-m inflation               • goal, savings, income, expenses
                 • up / down vs last month                 • inflation assumption, pre-filled with
                 • 24-month chart + ±MAE band                the city's last-12-month inflation
                 • last-12-month inflation of the city     • cost of the goal when reached
                                                           • months to goal, and how many of
                                                             those months inflation adds
```

- Step 1 answers *"which way are prices moving here?"*. It is a one-month model forecast.
- Step 2 answers *"what does that mean for my goal?"*. It compounds a **long-term annual rate** over the whole saving horizon. The default is the city's compounded inflation over the last 12 months, and the user can type their own. The one-month forecast is not compounded over years because a single month is too noisy for that (typical error ±0.44 pp, while the average month in the test period is +0.27%).
- The page is a single static file with every city's forecast embedded, and the planner runs in the browser. A link like `?city=yogyakarta` opens straight to that city's forecast.

## Data sources

Full provenance and processing rules are in [data/SOURCES.md](data/SOURCES.md).

| source | what | level | period |
|---|---|---|---|
| BPS (legacy CSV export) | m-t-m inflation | 82 cities | 2008-01 – 2016-12 (used) |
| BPS WebAPI, var 1 | m-t-m inflation | 150 cities | 2017-01 – 2026-09 |
| Bank Indonesia PIHPS | daily traditional-market prices for 10 commodities: rice, chicken, egg, shallot, red chili, beef, garlic, bird's eye chili, cooking oil, sugar | 110 regencies (all 82 modelled cities mapped) | 2017-07 – 2026-10 |

Where they overlap (2017-01 – 2023-11, 6,806 city-months), the legacy CSV and the official API agree on 99.99% of values. `python download.py bps` (needs `BPS_API_KEY` in `.env`) and `python download.py pihps` rebuild the raw data.

## Data validation

`python train.py` writes [artifacts/metrics/data_quality.json](artifacts/metrics/data_quality.json) and [coverage.csv](artifacts/metrics/coverage.csv). It checks:

- no duplicate city-month rows, valid dates, numeric values
- each city's months are contiguous (months missing from every source become explicit NaN rows)
- placeholder zeros in the legacy file are set to missing: `CPI == 0` (16 cities, 2008–2013) and `inflation == 0` while CPI moved (6 cities, 2011)
- robust per-city outlier report (|robust z| > 5, 170 rows). Outliers are reported, not removed
- minimum history of 96 valid months. The 82 long-running cities pass (shortest: 153 months). The 68 cities BPS added in 2020/2024 do not, and are not modelled
- legacy vs official agreement on the overlap period

## Forecasting target

`target_inflation = inflation_mtm[t+1]` for each city. Features at origin `t` use months ≤ `t`, calendar facts about month `t+1` that are known in advance, and (nowcast only) PIHPS prices from the first 5 trading days of month `t+1`. BPS publishes month `t`'s inflation at the start of month `t+1`, so those first days are already observed when a forecast is refreshed after about the 8th.

## Feature engineering ([src/features.py](src/features.py))

| group | features |
|---|---|
| lags | `inflation_mtm[t]`, `inflation_lag_1..11` (12-month window) |
| rolling | 3/6/12-month mean, 12-month std |
| seasonality | target month sin/cos, December flag |
| islamic_calendar | Ramadan and Idul Fitri month flags for the target month (Eid moves ~11 days a year, so month-of-year alone misses it) |
| food_prices | m-o-m % change of the monthly mean PIHPS price at `t`: rice, chicken, egg, shallot, red chili |
| food_prices_extra | same for beef, garlic, bird's eye chili, cooking oil, sugar |
| food_nowcast | mean of the first 5 priced days of month `t+1` vs the mean of month `t`, all 10 commodities |

Each food group ends with a `*_missing` flag. A missing price change (before PIHPS starts in 2017, a sparse month, or a nowcast before 5 trading days exist) becomes 0 with the flag set, so those rows still train and serve instead of being dropped. Every feature configuration therefore trains on the same 14,448 rows.

## Split

Chronological, by target month:

| set | target months | rows |
|---|---|---|
| rolling-origin validation | 2021, 2022, 2023, 2024 (one fold each) | 3,936 (984 per fold) |
| test | 2025-01 – 2026-09 | 1,722 |

Each validation fold trains on every target month before its year (expanding window). Feature groups and the model are chosen on the MAE pooled over all four folds. The selected config is then refitted on all rows up to 2024-12 and scored on test once.

## Baselines and models

- naive: `ŷ[t+1] = y[t]`
- seasonal naive: `ŷ[t+1] = y[t-11]`
- Ridge regression (standard-scaled)
- HistGradientBoostingRegressor (scikit-learn)

One global model across all cities. Windows are built per city.

## Ablation (rolling-origin validation 2021–2024, MAE in pp)

Greedy forward selection: a group is kept only if it lowers pooled validation MAE.

| model | step | pooled MAE | 2021 | 2022 | 2023 | 2024 | kept |
|---|---|---|---|---|---|---|---|
| ridge | lags | 0.380 | 0.309 | 0.564 | 0.295 | 0.352 | ✓ |
| ridge | + rolling | 0.380 | 0.310 | 0.564 | 0.295 | 0.351 | ✗ |
| ridge | + seasonality | 0.381 | 0.300 | 0.571 | 0.304 | 0.351 | ✗ |
| ridge | + islamic_calendar | 0.376 | 0.322 | 0.541 | 0.305 | 0.335 | ✓ |
| ridge | + food_prices | 0.362 | 0.283 | 0.584 | 0.280 | 0.302 | ✓ |
| ridge | + food_prices_extra | 0.363 | 0.284 | 0.583 | 0.281 | 0.302 | ✗ |
| ridge | + food_nowcast | 0.328 | 0.263 | 0.504 | 0.260 | 0.284 | ✓ |
| hist_gbr | lags | 0.381 | 0.290 | 0.606 | 0.297 | 0.332 | ✓ |
| hist_gbr | + rolling | 0.382 | 0.286 | 0.612 | 0.300 | 0.332 | ✗ |
| hist_gbr | + seasonality | 0.369 | 0.276 | 0.562 | 0.287 | 0.351 | ✓ |
| hist_gbr | + islamic_calendar | 0.356 | 0.271 | 0.542 | 0.290 | 0.322 | ✓ |
| hist_gbr | + food_prices | 0.349 | 0.267 | 0.550 | 0.266 | 0.311 | ✓ |
| hist_gbr | + food_prices_extra | 0.349 | 0.275 | 0.551 | 0.269 | 0.300 | ✗ |
| hist_gbr | + food_nowcast | **0.327** | 0.260 | 0.502 | 0.265 | 0.281 | ✓ |

Baselines on the same folds: naive 0.471, seasonal naive 0.471.

Selected: **hist_gbr** with lags, seasonality, islamic_calendar, food_prices and food_nowcast (0.327 vs 0.328 for ridge, effectively a tie). The food nowcast gives the largest single gain in both models. The five extra commodities add nothing on top of the first five, so they are not in the model. 2022 is the hardest year for every configuration (fuel price hike in September 2022).

## Evaluation (test 2025-01 – 2026-09, 82 cities, n = 1,722)

| model | MAE (pp) | RMSE (pp) |
|---|---|---|
| naive | 0.694 | 0.953 |
| seasonal naive | 0.685 | 0.892 |
| ridge | 0.422 | 0.593 |
| **hist_gbr (selected)** | **0.438** | **0.619** |

The selected model cuts naive MAE by 37%.

- **High-volatility months** (2025-01, 03, 04, 12, 2026-02, 06; this includes the early-2025 electricity discount): hist_gbr has MAE 0.735, against 0.990 for naive.
- **Other months:** hist_gbr has MAE 0.319, against 0.576 for naive.
- **By city:** error ranges from 0.24 (Batam) to 0.92 (Bau-Bau). Small eastern cities are hardest.

Details are in `artifacts/metrics/`: `mae_by_city.csv`, `mae_by_month.csv`, `volatility.json`, `actual_vs_predicted.png` and `residuals.png`.

### Test diagnostic

`metrics.json` → `test_ablation_diagnostic` scores each kept ablation step of the selected model on test. It is never used for selection:

| hist_gbr features | test MAE |
|---|---|
| lags | 0.504 |
| + seasonality | 0.494 |
| + islamic_calendar | 0.493 |
| + food_prices | 0.499 |
| + food_nowcast (selected) | **0.438** |

Monthly food price changes alone do not carry over to 2025–26, but the nowcast does. Disclosure: an earlier version of this pipeline (single 2024 validation year, no nowcast) was scored on this same test period, and the nowcast and rolling-origin validation were added after that. The selection rule never looks at test, but the test period is therefore not fully unseen by the developer.

## ML notebook

[notebooks/ml_pipeline.ipynb](notebooks/ml_pipeline.ipynb) runs the whole ML part cell by cell with outputs saved: data audit, PIHPS prices, features, rolling-origin folds, baselines, ablation, test, and a forecast fed into the planner. It calls the same `src/` and `train.py` functions, so its numbers match `metrics.json`, and it does not write any artifacts.

## Financial impact methodology ([src/financial.py](src/financial.py), mirrored in [templates/planner.js](templates/planner.js))

- `monthly_saving = income − expenses`
- The goal grows with a **long-term annual assumption**, not with the one-month forecast. The default is the city's compounded inflation over the last 12 months, and the user can override it.
- Months to goal = smallest `n` with `savings + n·monthly_saving ≥ goal·(1+annual)^(n/12)`, found by scanning month by month (capped at 100 years).
- The plan assumes no investment return and constant income, expenses and inflation. It is a planning estimate, not financial advice.

## Architecture

```
download.py            BPS WebAPI + PIHPS scraper -> data/raw/
src/data.py            legacy clean + placeholder rules, BPS parse, merge, validation, coverage
src/pihps.py           daily prices -> monthly means + first-5-day means, city <-> regency mapping
src/features.py        per-city lags/rolling/calendar/food/nowcast features, target t+1
src/split.py           dev/test split and rolling-origin folds
train.py               baselines, ablation, selection, test, artifacts/model.joblib
evaluate.py            diagnostics + plots
src/inference.py       loads model.joblib + data/processed/ (no fitting)
app.py                 Flask: UI at / and JSON API
export_static.py       UI with every city's forecast embedded -> docs/index.html
notebooks/             ml_pipeline.ipynb, the ML pipeline cell by cell
```

`CC/`, `ML/` and `MD/` hold the 2023 capstone code. The pipeline above does not use them.

## Web app

`docs/index.html` is a single self-contained page (~120 KB) with every city's forecast embedded. The planner runs in the browser, so the page needs no server and never sleeps. Host it on GitHub Pages (branch `portfolio`, folder `/docs`) or on a Hugging Face Static Space (see [deploy/hf-space/](deploy/hf-space/)).

## API

`python app.py` serves the same page plus JSON endpoints.

`POST /api/forecast`

```json
{"city": "Yogyakarta"}
```
```json
{"city": "YOGYAKARTA", "as_of": "2026-09", "forecast_period": "2026-10",
 "previous_inflation": 0.28, "predicted_inflation": 0.28, "change": 0.0, "trend": "unchanged",
 "unit": "percent, month-to-month", "model": "hist_gbr", "annual_inflation_12m": 3.3, "history": [...]}
```

`POST /api/financial-impact`

```json
{"city": "Yogyakarta", "current_savings": 15000000, "monthly_income": 10000000,
 "monthly_expenses": 6000000, "goal_amount": 100000000}
```
```json
{"goal_today": 100000000, "inflation_adjusted_goal": 106420579, "monthly_saving_capacity": 4000000,
 "months_to_goal": 23, "time_to_goal": {"years": 1, "months": 11},
 "annual_inflation_assumption_pct": 3.3, "assumption_source": "YOGYAKARTA compounded ...", ...}
```

Errors return HTTP 400 with `{"error": {"code": ..., "message": ...}}`. The codes are `unsupported_city`, `missing_forecast_data`, `negative_input`, `invalid_goal`, `invalid_input`, `no_saving_capacity`, `goal_unreachable` and `invalid_request`.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python download.py bps     # needs BPS_API_KEY in .env (free: https://webapi.bps.go.id/developer/)
python download.py pihps   # ~1 hour per commodity set on a fresh pull; resumable
python train.py            # audit + ablation + test metrics + artifacts/model.joblib
python evaluate.py         # diagnostics and plots
python export_static.py    # docs/index.html
python app.py              # http://localhost:8080
```

To refresh each month, re-run the steps from `download.py` to `export_static.py` **after about the 8th**, then commit. By then BPS has published last month's inflation and PIHPS has the 5 trading days the nowcast needs. Refreshing earlier still works, but the forecast runs without the nowcast (its missing flag is set).

## Tests

```bash
python -m pytest
```

The tests cover:

- data handling: placeholder handling, duplicates, date parsing, merging legacy and BPS data, PIHPS monthly and first-5-day means, city mapping
- features and split: t+1 targets, no city-crossing windows (lags and food prices), gap handling, missing-food fill + flag, nowcast from the target month's first days only, chronological split and rolling-origin folds
- serving: reuse of the stored model, unsupported cities, API errors
- planner: edge cases, and JS/Python planner parity (needs Node)

The inference tests need `train.py` to have been run first.

## Limitations

- The model only sees each city's own inflation history, the calendar and food prices. No exchange rate, policy rate, administered prices (fuel, electricity) or weather, which is why policy-shock months have the largest errors.
- The forecast depends on when the data was refreshed: before ~the 8th of the month it has no nowcast. Rows with the nowcast flag set come almost only from before 2017, so that fallback is learned from older data.
- No uncertainty interval is returned. The UI shows the test MAE as a typical error band.
- The 68 cities BPS added in 2020/2024 are not covered yet because their history is too short.
- PIHPS is scraped from Bank Indonesia's public site endpoints, which may change without notice.

## Responsible use

The forecasts are statistical estimates with sizeable error, especially around policy shocks (fuel prices, electricity discounts). The planner output is illustrative, not financial advice.

## Team (2023 Bangkit capstone, G30SCAM)

| Learning Path | Name | University |
|---|---|---|
| Machine Learning | Ahmad Rizgifan Fauzhy | Universitas Ahmad Dahlan |
| Machine Learning | Faris Zaidan Nafis | University of Gadjah Mada |
| Machine Learning | T.M. Fathin Rifat | University of Gadjah Mada |
| Cloud Computing | Mochammad Shandy Ferdiansyach | University of Gadjah Mada |
| Cloud Computing | Herdian Aji Laksana | Universitas Teknologi Digital Indonesia |
| Mobile Development | Lalu Bagoes Putra Ramadhan | Universitas Ahmad Dahlan |
| Mobile Development | Charlos Matio Simanjuntak | Universtas Mikroskil |
