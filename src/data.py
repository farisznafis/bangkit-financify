"""Build the clean city-month inflation panel (legacy BPS export + official BPS WebAPI) and audit it."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "inflasi_v3.csv"
BPS_DIR = ROOT / "data" / "raw" / "bps"
BPS_START = pd.Timestamp("2017-01-01")  # first month served by the BPS WebAPI (var 1)
MONTHS = ["januari", "februari", "maret", "april", "mei", "juni",
          "juli", "agustus", "september", "oktober", "november", "desember"]
MIN_VALID_MONTHS = 96


def load_raw(path=RAW_PATH):
    return pd.read_csv(path)


def clean(raw):
    """Raw export -> one row per city-month with `inflation_mtm` (NaN where the value is a placeholder)."""
    raw = raw.copy()
    for col in ["Inflation", "CPI"]:
        if not pd.api.types.is_numeric_dtype(raw[col]):
            raw[col] = pd.to_numeric(raw[col].astype(str).str.replace(",", "."))
    month = raw["Month"].str.lower().map({m: i + 1 for i, m in enumerate(MONTHS)})
    if month.isna().any():
        raise ValueError(f"unparseable month names: {raw.loc[month.isna(), 'Month'].unique()}")
    df = pd.DataFrame({
        "city": raw["City"].str.strip().str.upper().str.replace(r"^KOTA ", "", regex=True),
        "date": pd.to_datetime({"year": raw["Year"], "month": month, "day": 1}),
        "cpi": raw["CPI"].astype(float),
        "inflation_mtm": raw["Inflation"].astype(float),
    })
    dup = df.duplicated(["city", "date"])
    if dup.any():
        raise ValueError(f"duplicate city-month rows: {df.loc[dup, ['city', 'date']].head().to_dict('records')}")
    df = df.sort_values(["city", "date"]).reset_index(drop=True)

    # Placeholder rule 1: CPI == 0 means the city was not yet in the BPS sample.
    no_cpi = df["cpi"] <= 0
    # Placeholder rule 2: inflation exactly 0 while the CPI level moved (e.g. six cities throughout 2011).
    prev_cpi = df.groupby("city")["cpi"].shift()
    zero_but_moved = (df["inflation_mtm"] == 0) & prev_cpi.gt(0) & (df["cpi"].round(2) != prev_cpi.round(2))
    df["placeholder"] = no_cpi | zero_but_moved
    df.loc[df["placeholder"], ["cpi", "inflation_mtm"]] = np.nan
    return df


def load_bps(bps_dir=BPS_DIR):
    """BPS WebAPI var 1 (Inflasi Bulanan M-to-M) JSON files -> city, date, inflation_mtm."""
    rows = []
    for path in sorted(bps_dir.glob("var1_*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        var, turvar, th = d["var"][0]["val"], d["turvar"][0]["val"], d["tahun"][0]
        for v in d["vervar"]:
            if v["label"] == "INDONESIA":
                continue
            for m in range(1, 13):
                value = d["datacontent"].get(f"{v['val']}{var}{turvar}{th['val']}{m}")
                if value is not None:
                    rows.append((v["label"], pd.Timestamp(int(th["label"]), m, 1), float(value)))
    df = pd.DataFrame(rows, columns=["city", "date", "inflation_mtm"])
    df["city"] = df["city"].str.strip().str.upper().str.replace(r"^KOTA ", "", regex=True)
    if df.duplicated(["city", "date"]).any():
        raise ValueError("duplicate city-month rows in BPS data")
    return df


def overlap_check(legacy, bps):
    """How well the legacy file agrees with official BPS where both exist."""
    m = legacy.dropna(subset=["inflation_mtm"]).merge(bps, on=["city", "date"], suffixes=("_legacy", "_bps"))
    diff = (m["inflation_mtm_legacy"] - m["inflation_mtm_bps"]).abs()
    return {"rows": len(m), "share_equal": round(float((diff < 0.005).mean()), 4), "max_abs_diff": float(diff.max())}


def combine(legacy, bps):
    """Legacy rows before BPS_START, official BPS from then on. Months missing in both become NaN rows."""
    df = pd.concat([
        legacy.loc[legacy["date"] < BPS_START, ["city", "date", "inflation_mtm", "placeholder"]].assign(source="legacy"),
        bps.assign(placeholder=False, source="bps_api"),
    ])
    parts = []
    for city, g in df.groupby("city"):
        span = pd.date_range(g["date"].min(), g["date"].max(), freq="MS")
        parts.append(g.set_index("date").reindex(span).rename_axis("date").reset_index().assign(city=city))
    out = pd.concat(parts, ignore_index=True)
    out["placeholder"] = out["placeholder"].astype("boolean").fillna(False).astype(bool)
    out["source"] = out["source"].fillna("missing")
    return out[["city", "date", "inflation_mtm", "placeholder", "source"]]


def load_full():
    return combine(clean(load_raw()), load_bps())


def coverage_report(panel):
    def one(g):
        valid = g.dropna(subset=["inflation_mtm"])
        span = pd.date_range(valid["date"].min(), valid["date"].max(), freq="MS")
        return pd.Series({
            "first_valid_date": valid["date"].min().strftime("%Y-%m"),
            "last_valid_date": valid["date"].max().strftime("%Y-%m"),
            "observation_count": len(valid),
            "missing_months": len(span) - len(valid),
            "invalid_zero_count": int(g["placeholder"].sum()),
        })
    return panel.groupby("city")[["date", "inflation_mtm", "placeholder"]].apply(one).reset_index()


def validate(panel):
    """Return a data-quality dict; raise on hard failures."""
    assert not panel.duplicated(["city", "date"]).any(), "duplicate city-month"
    assert (panel["date"].dt.day == 1).all(), "dates must be month starts"
    assert pd.api.types.is_float_dtype(panel["inflation_mtm"]), "inflation must be numeric"
    for city, g in panel.groupby("city"):
        expected = pd.date_range(g["date"].min(), g["date"].max(), freq="MS")
        assert len(g) == len(expected) and (g["date"].values == expected.values).all(), f"{city}: gaps/unsorted months"

    # Robust within-city outliers (|robust z| > 5); reported, not removed.
    x = panel["inflation_mtm"]
    med = panel.groupby("city")["inflation_mtm"].transform("median")
    mad = (x - med).abs().groupby(panel["city"]).transform("median") * 1.4826
    outliers = panel[((x - med) / mad).abs() > 5]
    cov = coverage_report(panel)
    return {
        "rows": len(panel),
        "cities": panel["city"].nunique(),
        "date_range": [panel["date"].min().strftime("%Y-%m"), panel["date"].max().strftime("%Y-%m")],
        "placeholder_rows_set_to_missing": int(panel["placeholder"].sum()),
        "missing_inflation_rows": int(panel["inflation_mtm"].isna().sum()),
        "cities_below_min_history": cov.loc[cov["observation_count"] < MIN_VALID_MONTHS, "city"].tolist(),
        "outlier_rows": len(outliers),
        "outliers": outliers[["city", "date", "inflation_mtm"]].assign(date=outliers["date"].dt.strftime("%Y-%m")).to_dict("records"),
    }


def load_panel():
    """Clean panel restricted to cities meeting the minimum-history threshold."""
    panel = load_full()
    cov = coverage_report(panel)
    keep = cov.loc[cov["observation_count"] >= MIN_VALID_MONTHS, "city"]
    return panel[panel["city"].isin(keep)].reset_index(drop=True)
