"""Audit data, run baselines + feature-group ablation on validation, fit the selected model, score it once on test."""
import json

import joblib
import pandas as pd

from src.data import (ROOT, MIN_VALID_MONTHS, clean, combine, coverage_report, load_bps, load_raw,
                      overlap_check, validate)
from src.features import FEATURE_GROUPS, build_features, columns
from src.models import BASELINES, CANDIDATES, metrics
from src.pihps import load_monthly
from src.split import TRAIN_END, VAL_END, split

METRICS_DIR = ROOT / "artifacts" / "metrics"
MODEL_PATH = ROOT / "artifacts" / "model.joblib"
PANEL_PATH = ROOT / "data" / "processed" / "panel.csv"
PRICES_PATH = ROOT / "data" / "processed" / "food_prices.csv"


def fit(name, cols, rows):
    # each config trains on every row it has data for (food prices only exist from 2017)
    rows = rows.dropna(subset=cols)
    return CANDIDATES[name]().fit(rows[cols], rows["target_inflation"]), len(rows)


def fit_score(name, cols, fit_rows, eval_rows):
    model, n_train = fit(name, cols, fit_rows)
    return model, {**metrics(eval_rows["target_inflation"], model.predict(eval_rows[cols])), "n_train": n_train}


def main():
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Phase 1: audit
    legacy, bps = clean(load_raw()), load_bps()
    full = combine(legacy, bps)
    quality = validate(full)
    quality["legacy_vs_bps_overlap"] = overlap_check(legacy, bps)
    cov = coverage_report(full)
    cov.to_csv(METRICS_DIR / "coverage.csv", index=False)
    (METRICS_DIR / "data_quality.json").write_text(json.dumps(quality, indent=2))
    keep = cov.loc[cov["observation_count"] >= MIN_VALID_MONTHS, "city"]
    panel = full[full["city"].isin(keep)]
    panel.to_csv(PANEL_PATH, index=False, date_format="%Y-%m-%d")
    print(f"panel: {quality['rows']} rows, {len(keep)}/{quality['cities']} cities kept, "
          f"{quality['placeholder_rows_set_to_missing']} placeholders -> NaN")

    prices = load_monthly(keep)
    prices.to_csv(PRICES_PATH, index=False, date_format="%Y-%m-%d")

    # Phase 3-6: val/test rows have every candidate feature, so all configs are scored on the same rows
    feats = build_features(panel, prices)
    all_cols = columns(FEATURE_GROUPS)
    train, val, test = split(feats.dropna(subset=columns([g for g in FEATURE_GROUPS if g != "food_prices"])))
    val, test = val.dropna(subset=all_cols), test.dropna(subset=all_cols)
    assert train["target_date"].max() < val["target_date"].min() <= val["target_date"].max() < test["target_date"].min()
    print(f"train {len(train)} | val {len(val)} | test {len(test)} rows")

    results = {"split": {"train_end": TRAIN_END.strftime("%Y-%m"), "val_end": VAL_END.strftime("%Y-%m"),
                         "test_end": test["target_date"].max().strftime("%Y-%m"),
                         "rows": {"train": len(train), "val": len(val), "test": len(test)}},
               "validation": {name: metrics(val["target_inflation"], f(val)) for name, f in BASELINES.items()},
               "ablation": [], "selected_groups": {}}

    # Greedy forward selection: a feature group stays only if it lowers validation MAE.
    for name in CANDIDATES:
        groups = ["lags"]
        best = fit_score(name, columns(groups), train, val)[1]
        results["ablation"].append({"model": name, "groups": list(groups), **best, "kept": True})
        for grp in [g for g in FEATURE_GROUPS if g != "lags"]:
            score = fit_score(name, columns(groups + [grp]), train, val)[1]
            kept = score["mae"] < best["mae"]
            results["ablation"].append({"model": name, "groups": groups + [grp], **score, "kept": kept})
            if kept:
                groups, best = groups + [grp], score
        results["selected_groups"][name] = groups
        results["validation"][name] = best

    selected = min(CANDIDATES, key=lambda n: results["validation"][n]["mae"])
    results["selected_model"] = selected

    # Phase 8: refit on train+val, score once on the untouched test period
    train_val = pd.concat([train, val])
    preds = test[["city", "date", "target_date", "target_inflation"]].copy()
    for name, f in BASELINES.items():
        preds[name] = f(test)
    for name in CANDIDATES:
        cols = columns(results["selected_groups"][name])
        model = fit(name, cols, train_val)[0]
        preds[name] = model.predict(test[cols])
    results["test"] = {n: metrics(preds["target_inflation"], preds[n]) for n in [*BASELINES, *CANDIDATES]}
    preds.to_csv(METRICS_DIR / "test_predictions.csv", index=False, date_format="%Y-%m")
    (METRICS_DIR / "metrics.json").write_text(json.dumps(results, indent=2))

    # Phase 9: same model + feature config refitted on every labeled row; this fitted pipeline
    # (scaler included) is what the API serves. Test metrics above describe this procedure.
    cols = columns(results["selected_groups"][selected])
    everything = pd.concat([train_val, test])
    model = fit(selected, cols, everything)[0]
    joblib.dump({"model": model, "features": cols, "model_name": selected,
                 "trained_on_targets_through": everything["target_date"].max().strftime("%Y-%m"),
                 "cities": sorted(panel["city"].unique())}, MODEL_PATH)

    print(json.dumps({k: results[k] for k in ["selected_model", "selected_groups", "validation", "test"]}, indent=2))


if __name__ == "__main__":
    main()
