"""Per-city features at forecast origin t; target is inflation_mtm at t+1."""
import numpy as np
import pandas as pd

LAGS = 12  # window = inflation_mtm at t plus lags 1..11

# Idul Fitri (1 Syawal) dates as observed in Indonesia. Ramadan's mid-point is ~15 days before.
EID_FITR = pd.to_datetime([
    "2008-10-01", "2009-09-20", "2010-09-10", "2011-08-31", "2012-08-19", "2013-08-08",
    "2014-07-28", "2015-07-17", "2016-07-06", "2017-06-25", "2018-06-15", "2019-06-05",
    "2020-05-24", "2021-05-13", "2022-05-02", "2023-04-22", "2024-04-10", "2025-03-31",
    "2026-03-20", "2027-03-10",
])

FEATURE_GROUPS = {
    "lags": ["inflation_mtm"] + [f"inflation_lag_{k}" for k in range(1, LAGS)],
    "rolling": ["inflation_roll_3", "inflation_roll_6", "inflation_roll_12", "inflation_std_12"],
    "seasonality": ["month_sin", "month_cos", "year_end_flag"],
    "islamic_calendar": ["ramadan_flag", "eid_fitr_flag"],
    "food_prices": [f"{c}_price_mom" for c in ("rice", "chicken", "egg", "shallot", "chili")],
}


def _month_key(dates):
    return dates.dt.year * 12 + dates.dt.month


def build_features(panel, prices=None):
    """panel: contiguous monthly rows per city (see data.validate). Rows with gaps in the window get NaN.
    prices: optional PIHPS monthly means (pihps.load_monthly); without it food features are NaN."""
    out = panel[["city", "date", "inflation_mtm"]].sort_values(["city", "date"]).reset_index(drop=True)
    g = out.groupby("city")["inflation_mtm"]
    commodities = [c.removesuffix("_price_mom") for c in FEATURE_GROUPS["food_prices"]]
    priced = out[["city", "date"]].merge(prices, on=["city", "date"], how="left") if prices is not None \
        else out[["city", "date"]].assign(**{c: np.nan for c in commodities})
    for c in commodities:
        # month t mean vs month t-1 mean, both complete before the t+1 target month starts
        out[f"{c}_price_mom"] = priced.groupby("city")[c].pct_change(fill_method=None) * 100
    for k in range(1, LAGS):
        out[f"inflation_lag_{k}"] = g.shift(k)
    for w in (3, 6, 12):
        out[f"inflation_roll_{w}"] = g.transform(lambda s: s.rolling(w).mean())
    out["inflation_std_12"] = g.transform(lambda s: s.rolling(12).std())

    # Calendar features describe the target month; they are known in advance.
    target_date = out["date"] + pd.offsets.MonthBegin(1)
    if target_date.max() > EID_FITR.max():
        raise ValueError("extend EID_FITR before forecasting past it")
    month = target_date.dt.month
    out["target_date"] = target_date
    out["month_sin"] = np.sin(2 * np.pi * month / 12)
    out["month_cos"] = np.cos(2 * np.pi * month / 12)
    out["year_end_flag"] = (month == 12).astype(int)
    key = _month_key(target_date)
    out["eid_fitr_flag"] = key.isin(_month_key(pd.Series(EID_FITR))).astype(int)
    out["ramadan_flag"] = key.isin(_month_key(pd.Series(EID_FITR - pd.Timedelta(days=15)))).astype(int)

    out["target_inflation"] = g.shift(-1)
    return out


def columns(groups):
    return [c for grp in groups for c in FEATURE_GROUPS[grp]]
