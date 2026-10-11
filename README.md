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
| Sequences | all cities concatenated, so windows crossed city boundaries | lags built per city; a window never mixes cities |
| Target | `y = x[t]` (last input step, not a forecast) | `y = inflation[t+1]` |
| Scaling | MinMax fitted on the full dataset, and refitted in the Flask handler | scaler inside a pipeline fitted on train only, saved and reused |
| Placeholder zeros | treated as real 0% inflation | set to missing (1,224 rows) |
| CPI level | used raw across base-year breaks | not used. The model works on m-t-m inflation |
| Evaluation | none | chronological train/val/test split, naive baselines, ablation |
| Planner | predicted inflation subtracted from the goal as if it were money | inflation grows the goal's cost over the saving horizon |

## Data sources

BPS city month-to-month inflation and CPI, 82 cities, 2008-01 to 2023-11, from the legacy capstone file. See [data/SOURCES.md](data/SOURCES.md) for provenance, the processing rules and the sources that are not used yet. No external sources (PIHPS, JISDOR, BI Rate, BMKG and others) are used yet.

## Data validation

`python train.py` writes [artifacts/metrics/data_quality.json](artifacts/metrics/data_quality.json) and [coverage.csv](artifacts/metrics/coverage.csv). It checks:

- no duplicate city-month rows, valid dates, numeric values
- each city's months are contiguous
- placeholder zeros are set to missing: `CPI == 0` (16 cities, 2008–2013) and `inflation == 0` while CPI moved (6 cities, 2011)
- robust per-city outlier report (|robust z| > 5). Outliers are reported, not removed
- minimum history of 96 valid months. All 82 cities pass, and the shortest history is 119 months

## Forecasting target

`target_inflation = inflation_mtm[t+1]` for each city. Features at origin `t` only use months ≤ `t`, plus calendar facts about month `t+1` that are known in advance.

## Feature engineering ([src/features.py](src/features.py))

| group | features |
|---|---|
| lags | `inflation_mtm[t]`, `inflation_lag_1..11` (12-month window) |
| rolling | 3/6/12-month mean, 12-month std |
| seasonality | target month sin/cos, December flag |
| islamic_calendar | Ramadan and Idul Fitri month flags for the target month (Eid moves ~11 days a year, so month-of-year alone misses it) |

## Split

Chronological, by target month:

| set | target months | rows |
|---|---|---|
| train | 2009-01 – 2020-12 | 10,512 |
| validation | 2021-01 – 2021-12 | 984 |
| test | 2022-01 – 2023-11 | 1,886 |

Feature groups and the model are chosen on validation. The selected config is then refitted on train+val and scored on test once.

## Baselines and models

- naive: `ŷ[t+1] = y[t]`
- seasonal naive: `ŷ[t+1] = y[t-11]`
- Ridge regression (standard-scaled)
- HistGradientBoostingRegressor (scikit-learn)

One global model across all cities. Windows are built per city.

## Ablation (validation MAE, pp)

Greedy forward selection: a group is kept only if it lowers validation MAE.

| model | features | MAE | RMSE | kept |
|---|---|---|---|---|
| ridge | lags | 0.309 | 0.406 | ✓ |
| ridge | + rolling | 0.310 | 0.406 | ✗ |
| ridge | + seasonality | 0.300 | 0.397 | ✓ |
| ridge | + islamic_calendar | 0.297 | 0.394 | ✓ |
| hist_gbr | lags | 0.290 | 0.400 | ✓ |
| hist_gbr | + rolling | 0.286 | 0.393 | ✓ |
| hist_gbr | + seasonality | 0.272 | 0.375 | ✓ |
| hist_gbr | + islamic_calendar | **0.269** | **0.369** | ✓ |

## Evaluation (test, 2022-01 – 2023-11, 82 cities, n = 1,886)

| model | MAE (pp) | RMSE (pp) |
|---|---|---|
| naive | 0.571 | 0.798 |
| seasonal naive | 0.592 | 0.742 |
| ridge | 0.428 | 0.571 |
| **hist_gbr (selected)** | **0.412** | **0.556** |

The six most volatile test months (2022-03, 04, 06, 07, 09, 12, which include the September 2022 fuel-price hike) are much harder. In those months hist_gbr has MAE 0.672 against 0.745 for naive, and Ridge does better there at 0.639. City-level error ranges from about 0.24 (Cirebon) to 0.89 (Tanjung Pandan). See `artifacts/metrics/` for `mae_by_city.csv`, `mae_by_month.csv`, `volatility.json`, `actual_vs_predicted.png` and `residuals.png`.

Neural models (LSTM/GRU) were not tested in v2. The tabular models already beat both baselines, and an LSTM would add TensorFlow for an unproven gain. Any future LSTM must beat hist_gbr on the same split.

## Financial impact methodology ([src/financial.py](src/financial.py))

- `monthly_saving = income − expenses`
- The goal grows with a **long-term annual assumption**, not with the one-month forecast. The default is the city's compounded inflation over the last 12 months (the 12 months to 2023-11), and the request can override it with `annual_inflation`.
- Months to goal = smallest `n` with `savings + n·monthly_saving ≥ goal·(1+annual)^(n/12)`, found by scanning month by month (capped at 100 years).
- The plan assumes no investment return and constant income, expenses and inflation. It is a planning estimate, not financial advice.

## Architecture

```
data/raw/inflasi_v3.csv
  └─ src/data.py        clean, placeholder rules, validation, coverage
     └─ src/features.py per-city lags/rolling/calendar, target t+1
        └─ src/split.py chronological split
           └─ train.py  baselines, ablation, selection, test, artifacts/model.joblib
                         evaluate.py  diagnostics + plots
src/inference.py  loads model.joblib + data/processed/panel.csv (no fitting)
src/financial.py  planner
app.py            Flask API + UI (templates/index.html)
```

## API

`POST /api/forecast`

```json
{"city": "Yogyakarta"}
```
```json
{"city": "YOGYAKARTA", "as_of": "2023-11", "forecast_period": "2023-12",
 "previous_inflation": 0.35, "predicted_inflation": 0.55, "change": 0.2, "trend": "up",
 "unit": "percent, month-to-month", "model": "hist_gbr", "history": [...]}
```

`POST /api/financial-impact`

```json
{"city": "Yogyakarta", "current_savings": 15000000, "monthly_income": 10000000,
 "monthly_expenses": 6000000, "goal_amount": 100000000}
```
```json
{"goal_today": 100000000, "inflation_adjusted_goal": 106736734, "monthly_saving_capacity": 4000000,
 "months_to_goal": 23, "time_to_goal": {"years": 1, "months": 11},
 "annual_inflation_assumption_pct": 3.46, "assumption_source": "YOGYAKARTA compounded ...", ...}
```

Errors return HTTP 400 with `{"error": {"code": ..., "message": ...}}`. The codes are `unsupported_city`, `missing_forecast_data`, `negative_input`, `invalid_goal`, `invalid_input`, `no_saving_capacity`, `goal_unreachable` and `invalid_request`.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python train.py      # audit + ablation + test metrics + artifacts/model.joblib
python evaluate.py   # diagnostics and plots
python app.py        # http://localhost:8080
```

## Tests

```bash
python -m pytest
```

The tests cover placeholder handling, duplicates, date parsing, t+1 targets, no city-crossing windows, gap handling, chronological split, reuse of the stored model, unsupported cities, API errors and planner edge cases. The inference tests need `train.py` to have been run first.

## Limitations

- The data stops at 2023-11, so the "next month" forecast is for 2023-12. Updating the data means re-downloading from BPS (see SOURCES.md) and re-running `train.py`.
- The provenance of the legacy file (BPS table IDs and retrieval date) was not recorded.
- Only the city's own inflation history and calendar are used. No food prices, exchange rate, policy rate or weather data.
- A single train/validation/test split. Walk-forward validation would give a more robust estimate.
- No uncertainty interval is returned. The typical test error is about ±0.4 pp per city-month.
- The 2024 BPS sample expansion (150 cities) is not covered.

## Responsible use

The forecasts are statistical estimates with sizeable error, especially around policy shocks. The planner output is illustrative, not financial advice.

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
