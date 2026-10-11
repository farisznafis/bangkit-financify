import numpy as np
import pandas as pd
import pytest

from src.data import clean, coverage_report, load_panel, validate


def raw(rows):
    return pd.DataFrame(rows, columns=["City", "Month", "Year", "Inflation", "CPI"])


def test_placeholder_zeros_become_missing():
    df = clean(raw([
        ["KOTA A", "januari", 2010, 0, 0],          # not in sample yet
        ["KOTA A", "februari", 2010, 0, 100.0],     # first CPI month, inflation unknown
        ["KOTA A", "maret", 2010, 0, 101.0],        # CPI moved but inflation says 0
        ["KOTA A", "april", 2010, 0, 101.0],        # CPI flat: a real 0%
    ]))
    assert df["placeholder"].tolist() == [True, False, True, False]
    assert np.isnan(df["inflation_mtm"].iloc[0]) and df["inflation_mtm"].iloc[3] == 0


def test_duplicate_city_month_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        clean(raw([["KOTA A", "januari", 2010, 1, 100], ["A", "januari", 2010, 1, 100]]))


def test_date_parsing_and_city_normalization():
    df = clean(raw([["KOTA YOGYAKARTA", "Desember", 2020, "0,5", "100,1"]]))
    assert df["date"].iloc[0] == pd.Timestamp("2020-12-01") and df["city"].iloc[0] == "YOGYAKARTA"


def test_bad_month_rejected():
    with pytest.raises(ValueError, match="month"):
        clean(raw([["A", "smarch", 2010, 1, 100]]))


def test_real_dataset_validates_and_coverage_threshold():
    panel = load_panel()
    report = validate(panel)
    assert report["cities_below_min_history"] == []
    assert (coverage_report(panel)["observation_count"] >= 96).all()
    assert panel.loc[~panel["placeholder"], "inflation_mtm"].notna().all()


def test_combine_uses_bps_from_2017_and_fills_gaps():
    from src.data import combine
    legacy = clean(raw([["KOTA A", "november", 2016, 0.1, 100], ["KOTA A", "desember", 2016, 0.2, 100.2],
                        ["KOTA A", "januari", 2017, 9.9, 100.3]]))
    bps = pd.DataFrame({"city": ["A", "A"], "date": pd.to_datetime(["2017-01-01", "2017-03-01"]),
                        "inflation_mtm": [0.3, 0.5]})
    out = combine(legacy, bps).set_index("date")
    assert out.loc["2017-01-01", "inflation_mtm"] == 0.3 and out.loc["2017-01-01", "source"] == "bps_api"
    assert np.isnan(out.loc["2017-02-01", "inflation_mtm"]) and out.loc["2017-02-01", "source"] == "missing"
    validate(out.reset_index())


def test_pihps_monthly_mean_mapping_and_sparse_months(tmp_path):
    import json
    from src.pihps import load_monthly
    (tmp_path / "regencies.json").write_text(json.dumps([
        {"regency_id": 1, "regency": "Kab. Cirebon"}, {"regency_id": 2, "regency": "Kota Cirebon"},
        {"regency_id": 3, "regency": "Kab. Banyumas"}]))
    days = {f"{d:02d}/01/2025": "10,000" for d in range(1, 12)} | {"01/02/2025": "12,000"}
    for reg in (1, 2, 3):
        (tmp_path / f"{reg}_2025-01.json").write_text(json.dumps({"data": [
            {"no": "I", "name": "Cabai Merah", "level": 1, **{k: str(reg) + v for k, v in days.items()}},
            {"no": 1, "name": "Cabai Merah Besar", "level": 2, **days}]}))
    m = load_monthly(["CIREBON", "PURWOKERTO", "NOWHERE"], tmp_path).set_index(["city", "date"])["chili"]
    assert m[("CIREBON", pd.Timestamp("2025-01-01"))] == 210_000  # Kota, not Kab., level-1 row
    assert m[("PURWOKERTO", pd.Timestamp("2025-01-01"))] == 310_000
    assert np.isnan(m[("CIREBON", pd.Timestamp("2025-02-01"))])  # 1 trading day < MIN_DAYS
    first = load_monthly(["CIREBON"], tmp_path).set_index("date")["chili_first"]
    assert first[pd.Timestamp("2025-01-01")] == 210_000  # mean of the first NOWCAST_DAYS days
    assert np.isnan(first[pd.Timestamp("2025-02-01")])  # 1 day < NOWCAST_DAYS
