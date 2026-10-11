# Financify

Short-term Indonesian city inflation forecasting + financial impact planning.

## What it does

1. **Inflation forecast:** pick a city and get next month's headline inflation (month-to-month), compared with the previous month and shown against the last 24 months.
2. **Financial impact:** enter savings, income, expenses and a goal. Financify estimates what the goal will cost after inflation and how long it takes to save for it.

> The original 2023 Bangkit capstone is preserved in branch `main` (the legacy `CC/`, `ML/` and `MD/` folders are still here too).
> This `portfolio` branch is a methodological and product remaster.

## Original 2023 project vs v2 remaster

| | 2023 capstone | v2 |
|---|---|---|
| Data | one CSV, provenance unknown, ends 2023-11 | legacy CSV verified against the BPS WebAPI (99.99% identical), extended with official data to 2026-09, plus Bank Indonesia food prices |
| Sequences | all cities concatenated, so windows crossed city boundaries | lags built per city; a window never mixes cities |
| Target | `y = x[t]` (last input step, not a forecast) | `y = inflation[t+1]` |
| Scaling | MinMax fitted on the full dataset, and refitted in the Flask handler | scaler inside a pipeline fitted on train only, saved and reused |
| Placeholder zeros | treated as real 0% inflation | set to missing (1,224 rows) |
| CPI level | used raw across base-year breaks | not used. The model works on m-t-m inflation |
| Evaluation | none | chronological train/val/test split, naive baselines, ablation |
| Planner | predicted inflation subtracted from the goal as if it were money | inflation grows the goal's cost over the saving horizon |
| App | Android app + Flask on Cloud Run | single static web page (no server), plus a Flask JSON API |

## Data sources

Full provenance and processing rules are in [data/SOURCES.md](data/SOURCES.md).

| source | what | level | period |
|---|---|---|---|
| BPS (legacy capstone CSV) | m-t-m inflation | 82 cities | 2008-01 – 2016-12 (used) |
| BPS WebAPI, var 1 | m-t-m inflation | 150 cities | 2017-01 – 2026-09 |
| Bank Indonesia PIHPS | daily traditional-market prices: rice, chicken, egg, shallot, red chili | 110 regencies (all 82 modelled cities mapped) | 2017-07 – 2026-10 |

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

`target_inflation = inflation_mtm[t+1]` for each city. Features at origin `t` only use months ≤ `t`, plus calendar facts about month `t+1` that are known in advance.

## Feature engineering ([src/features.py](src/features.py))

| group | features |
|---|---|
| lags | `inflation_mtm[t]`, `inflation_lag_1..11` (12-month window) |
| rolling | 3/6/12-month mean, 12-month std |
| seasonality | target month sin/cos, December flag |
| islamic_calendar | Ramadan and Idul Fitri month flags for the target month (Eid moves ~11 days a year, so month-of-year alone misses it) |
| food_prices | m-o-m % change of the monthly mean PIHPS price at `t`: rice, chicken, egg, shallot, red chili |

## Split

Chronological, by target month:

| set | target months | rows |
|---|---|---|
| train | 2009-01 – 2023-12 | 13,464 (6,202 with food prices, which start in 2017) |
| validation | 2024-01 – 2024-12 | 984 |
| test | 2025-01 – 2026-09 | 1,722 |

Each feature configuration trains on every row it has data for, so configurations with food prices train on 2017+ only. All configurations are scored on the same validation and test rows. Feature groups and the model are chosen on validation. The selected config is then refitted on train+val and scored on test once.

## Baselines and models

- naive: `ŷ[t+1] = y[t]`
- seasonal naive: `ŷ[t+1] = y[t-11]`
- Ridge regression (standard-scaled)
- HistGradientBoostingRegressor (scikit-learn)

One global model across all cities. Windows are built per city.

## Ablation (validation 2024, MAE in pp)

Greedy forward selection: a group is kept only if it lowers validation MAE.

| model | features | val MAE | val RMSE | train rows | kept |
|---|---|---|---|---|---|
| ridge | lags | 0.352 | 0.448 | 13,464 | ✓ |
| ridge | + rolling | 0.351 | 0.447 | 13,464 | ✓ |
| ridge | + seasonality | 0.350 | 0.447 | 13,464 | ✓ |
| ridge | + islamic_calendar | 0.319 | 0.419 | 13,464 | ✓ |
| ridge | + food_prices | **0.286** | **0.392** | 6,202 | ✓ |
| hist_gbr | lags | 0.332 | 0.437 | 13,464 | ✓ |
| hist_gbr | + rolling | 0.332 | 0.437 | 13,464 | ✓ |
| hist_gbr | + seasonality | 0.338 | 0.453 | 13,464 | ✗ |
| hist_gbr | + islamic_calendar | 0.318 | 0.430 | 13,464 | ✓ |
| hist_gbr | + food_prices | 0.305 | 0.409 | 6,202 | ✓ |

Selected: **ridge with all five groups**. The Islamic-calendar flags give the largest single gain.

## Evaluation (test 2025-01 – 2026-09, 82 cities, n = 1,722)

| model | MAE (pp) | RMSE (pp) |
|---|---|---|
| naive | 0.694 | 0.953 |
| seasonal naive | 0.685 | 0.892 |
| hist_gbr | 0.514 | 0.689 |
| **ridge (selected)** | **0.494** | **0.663** |

The selected model cuts naive MAE by 29%.

- **High-volatility months** (2025-01, 03, 04, 12, 2026-02, 06; this includes the early-2025 electricity discount): ridge has MAE 0.722, against 0.990 for naive.
- **Other months:** ridge has MAE 0.403, against 0.576 for naive.
- **By city:** error ranges from 0.30 (Singkawang) to 0.99 (Ternate). Small eastern cities are hardest.

Details are in `artifacts/metrics/`: `mae_by_city.csv`, `mae_by_month.csv`, `volatility.json`, `actual_vs_predicted.png` and `residuals.png`.

### Honest caveat: food prices on test

`metrics.json` → `test_ablation_diagnostic` scores each kept ablation step on test. This is a diagnostic only and is never used for selection:

| ridge features | test MAE |
|---|---|
| lags + rolling + seasonality + islamic_calendar | **0.466** |
| + food_prices (selected) | 0.494 |

Food prices helped on the 2024 validation year (−0.033) but hurt on 2025–26 (+0.028). A side check showed that the shorter 2017+ history explains only about 0.007 of that, so the rest comes from the features themselves. The selection rule was not changed after seeing test. The takeaway is that one validation year is a noisy judge for a 5-feature group. Rolling-origin (walk-forward) validation over several years is the next step before trusting food prices.

Neural models (LSTM/GRU) were not tested. The linear model already beats gradient boosting, so there is no evidence that more capacity is the bottleneck.

## Financial impact methodology ([src/financial.py](src/financial.py), mirrored in [templates/planner.js](templates/planner.js))

- `monthly_saving = income − expenses`
- The goal grows with a **long-term annual assumption**, not with the one-month forecast. The default is the city's compounded inflation over the last 12 months, and the user can override it.
- Months to goal = smallest `n` with `savings + n·monthly_saving ≥ goal·(1+annual)^(n/12)`, found by scanning month by month (capped at 100 years).
- The plan assumes no investment return and constant income, expenses and inflation. It is a planning estimate, not financial advice.

## Architecture

```
download.py            BPS WebAPI + PIHPS scraper -> data/raw/
src/data.py            legacy clean + placeholder rules, BPS parse, merge, validation, coverage
src/pihps.py           daily prices -> monthly means, city <-> regency mapping
src/features.py        per-city lags/rolling/calendar/food features, target t+1
src/split.py           chronological split
train.py               baselines, ablation, selection, test, artifacts/model.joblib
evaluate.py            diagnostics + plots
src/inference.py       loads model.joblib + data/processed/ (no fitting)
app.py                 Flask: UI at / and JSON API
export_static.py       UI with every city's forecast embedded -> docs/index.html
```

## Web app

`docs/index.html` is a single self-contained page (~120 KB) with every city's forecast embedded. The planner runs in the browser, so the page needs no server and never sleeps. Host it on GitHub Pages (branch `portfolio`, folder `/docs`) or on a Hugging Face Static Space (see [deploy/hf-space/](deploy/hf-space/)). A link like `?city=yogyakarta` opens straight to that city.

## API

`python app.py` serves the same page plus JSON endpoints.

`POST /api/forecast`

```json
{"city": "Yogyakarta"}
```
```json
{"city": "YOGYAKARTA", "as_of": "2026-09", "forecast_period": "2026-10",
 "previous_inflation": 0.28, "predicted_inflation": 0.14, "change": -0.14, "trend": "down",
 "unit": "percent, month-to-month", "model": "ridge", "annual_inflation_12m": 3.3, "history": [...]}
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
python download.py pihps   # ~1 hour; resumable
python train.py            # audit + ablation + test metrics + artifacts/model.joblib
python evaluate.py         # diagnostics and plots
python export_static.py    # docs/index.html
python app.py              # http://localhost:8080
```

To refresh each month, re-run the steps from `download.py` to `export_static.py`, then commit.

## Tests

```bash
python -m pytest
```

The tests cover:

- data handling: placeholder handling, duplicates, date parsing, merging legacy and BPS data, PIHPS monthly means and city mapping
- features and split: t+1 targets, no city-crossing windows (lags and food prices), gap handling, chronological split
- serving: reuse of the stored model, unsupported cities, API errors
- planner: edge cases, and JS/Python planner parity (needs Node)

The inference tests need `train.py` to have been run first.

## Limitations

- The model only sees each city's own inflation history, the calendar and five food prices. No exchange rate, policy rate, energy prices or weather.
- One validation year. The food-price result above shows that this can mislead, so walk-forward validation is the next improvement.
- No uncertainty interval is returned. The UI shows the test MAE as a typical error band.
- The 68 cities BPS added in 2020/2024 are not covered yet because their history is too short.
- PIHPS is scraped from Bank Indonesia's public site endpoints, which may change without notice.

## Responsible use

The forecasts are statistical estimates with sizeable error, especially around policy shocks (fuel prices, electricity discounts). The planner output is illustrative, not financial advice.

## Team (2023 Bangkit capstone, G30SCAM)

The v2 remaster (data pipeline, modelling, evaluation, web app) builds on the original team project.

| Learning Path | Name | University |
|---|---|---|
| Machine Learning | Ahmad Rizgifan Fauzhy | Universitas Ahmad Dahlan |
| Machine Learning | Faris Zaidan Nafis | University of Gadjah Mada |
| Machine Learning | T.M. Fathin Rifat | University of Gadjah Mada |
| Cloud Computing | Mochammad Shandy Ferdiansyach | University of Gadjah Mada |
| Cloud Computing | Herdian Aji Laksana | Universitas Teknologi Digital Indonesia |
| Mobile Development | Lalu Bagoes Putra Ramadhan | Universitas Ahmad Dahlan |
| Mobile Development | Charlos Matio Simanjuntak | Universtas Mikroskil |
