import numpy as np
import pytest
import pandas as pd

from src.features import FEATURE_GROUPS, build_features


def panel():
    dates = pd.date_range("2015-01-01", periods=30, freq="MS")
    a = pd.DataFrame({"city": "A", "date": dates, "inflation_mtm": np.arange(30, dtype=float)})
    b = pd.DataFrame({"city": "B", "date": dates, "inflation_mtm": 1000 + np.arange(30, dtype=float)})
    return pd.concat([a, b])


def test_target_is_next_month():
    f = build_features(panel())
    a = f[f["city"] == "A"].dropna(subset=["target_inflation"])
    assert (a["target_inflation"] == a["inflation_mtm"] + 1).all()
    assert (a["target_date"] == a["date"] + pd.offsets.MonthBegin(1)).all()


def test_window_is_12_months_and_never_crosses_cities():
    f = build_features(panel())
    lags = FEATURE_GROUPS["lags"]
    assert len(lags) == 12
    complete = f.dropna(subset=lags)
    for city, g in complete.groupby("city"):
        base = 0 if city == "A" else 1000
        assert (g[lags].to_numpy() >= base).all() and (g[lags].to_numpy() < base + 30).all()
    # first complete window of each city starts at its 12th month
    assert complete.groupby("city")["date"].min().eq(pd.Timestamp("2015-12-01")).all()
    assert f.groupby("city")["target_inflation"].apply(lambda s: s.isna().iloc[-1]).all()


def test_gap_invalidates_windows():
    p = panel()
    p.loc[(p["city"] == "A") & (p["date"] == "2016-01-01"), "inflation_mtm"] = np.nan
    f = build_features(p)
    a = f[f["city"] == "A"].set_index("date")
    assert a.loc["2016-06-01", FEATURE_GROUPS["lags"]].isna().any()


def test_food_price_change_is_within_city():
    p = panel()
    prices = p[["city", "date"]].assign(rice=np.where(p["city"] == "A", 100.0, 200.0), chicken=1.0, egg=1.0,
                                        shallot=1.0, chili=1.0)
    prices.loc[(prices["city"] == "B") & (prices["date"] == "2015-02-01"), "rice"] = 210.0
    f = build_features(p, prices).set_index(["city", "date"])
    b0 = f.loc[("B", pd.Timestamp("2015-01-01"))]
    assert b0["rice_price_mom"] == 0 and b0["food_prices_missing"] == 1  # no cross-city diff; gap -> 0 + flag
    assert f.loc[("B", pd.Timestamp("2015-02-01")), "food_prices_missing"] == 0
    assert f.loc[("B", pd.Timestamp("2015-02-01")), "rice_price_mom"] == pytest.approx(5.0)
    assert f.loc[("A", pd.Timestamp("2015-02-01")), "rice_price_mom"] == 0


def test_nowcast_uses_first_days_of_target_month_only():
    p = panel()
    prices = p[["city", "date"]].assign(rice=100.0, rice_first=np.nan)
    prices.loc[prices["date"] == "2015-03-01", "rice_first"] = 103.0
    f = build_features(p, prices).set_index(["city", "date"])
    feb = f.loc[("A", pd.Timestamp("2015-02-01"))]  # origin Feb, target Mar
    assert feb["rice_nowcast"] == pytest.approx(3.0)  # flag stays 1: the other commodities are absent
    mar = f.loc[("A", pd.Timestamp("2015-03-01"))]  # target Apr has no first-days price yet
    assert mar["rice_nowcast"] == 0 and mar["food_nowcast_missing"] == 1
    # without any prices every food group is flagged missing and filled with 0
    bare = build_features(p)
    assert bare["food_prices_extra_missing"].eq(1).all() and bare["beef_price_mom"].eq(0).all()
