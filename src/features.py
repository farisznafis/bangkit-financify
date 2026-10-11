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

FOOD = ("rice", "chicken", "egg", "shallot", "chili")
FOOD_EXTRA = ("beef", "garlic", "bird_chili", "cooking_oil", "sugar")

# The last column of each food group is its missing flag (see build_features).
FEATURE_GROUPS = {
    "lags": ["inflation_mtm"] + [f"inflation_lag_{k}" for k in range(1, LAGS)],
    "rolling": ["inflation_roll_3", "inflation_roll_6", "inflation_roll_12", "inflation_std_12"],
    "seasonality": ["month_sin", "month_cos", "year_end_flag"],
    "islamic_calendar": ["ramadan_flag", "eid_fitr_flag"],
    "food_prices": [f"{c}_price_mom" for c in FOOD] + ["food_prices_missing"],
    "food_prices_extra": [f"{c}_price_mom" for c in FOOD_EXTRA] + ["food_prices_extra_missing"],
    # first pihps.NOWCAST_DAYS trading days of the target month vs the mean of month t
    "food_nowcast": [f"{c}_nowcast" for c in FOOD + FOOD_EXTRA] + ["food_nowcast_missing"],
}
FOOD_GROUPS = ("food_prices", "food_prices_extra", "food_nowcast")


def _month_key(dates):
    return dates.dt.year * 12 + dates.dt.month


def build_features(panel, prices=None):
    """panel: contiguous monthly rows per city (see data.validate). Rows with gaps in the window get NaN.
    prices: optional PIHPS table (pihps.load_monthly); without it food features are 0 with the missing flag set."""
    out = panel[["city", "date", "inflation_mtm"]].sort_values(["city", "date"]).reset_index(drop=True)
    g = out.groupby("city")["inflation_mtm"]
    target_date = out["date"] + pd.offsets.MonthBegin(1)
    commodities = FOOD + FOOD_EXTRA
    price_cols = [*commodities, *(f"{c}_first" for c in commodities)]
    prices = (pd.DataFrame(columns=["city", "date"]) if prices is None else prices) \
        .reindex(columns=["city", "date", *price_cols]).astype({c: float for c in price_cols})
    prices["date"] = pd.to_datetime(prices["date"])
    priced = out[["city", "date"]].merge(prices, on=["city", "date"], how="left")
    nxt = out[["city"]].assign(date=target_date).merge(prices, on=["city", "date"], how="left")
    for c in commodities:
        # month t mean vs month t-1 mean, both complete before the t+1 target month starts
        out[f"{c}_price_mom"] = priced.groupby("city")[c].pct_change(fill_method=None) * 100
        out[f"{c}_nowcast"] = (nxt[f"{c}_first"] / priced[c] - 1) * 100
    # Missing price change -> 0 plus a flag, so rows before PIHPS starts (2017), or before the
    # nowcast days exist, still train and serve instead of being dropped.
    for grp in FOOD_GROUPS:
        *feats, flag = FEATURE_GROUPS[grp]
        out[flag] = out[feats].isna().any(axis=1).astype(int)
        out[feats] = out[feats].fillna(0.0)
    for k in range(1, LAGS):
        out[f"inflation_lag_{k}"] = g.shift(k)
    for w in (3, 6, 12):
        out[f"inflation_roll_{w}"] = g.transform(lambda s: s.rolling(w).mean())
    out["inflation_std_12"] = g.transform(lambda s: s.rolling(12).std())

    # Calendar features describe the target month; they are known in advance.
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
