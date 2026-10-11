"""Audit data, run baselines + feature-group ablation on rolling-origin validation, fit the selected model, score it once on test."""
import json

import joblib
import numpy as np
import pandas as pd

from src.data import (ROOT, MIN_VALID_MONTHS, clean, combine, coverage_report, load_bps, load_raw,
                      overlap_check, validate)
from src.features import FEATURE_GROUPS, build_features, columns
from src.models import BASELINES, CANDIDATES, metrics
from src.pihps import load_monthly
from src.split import VAL_END, VAL_YEARS, folds, split

METRICS_DIR = ROOT / "artifacts" / "metrics"
MODEL_PATH = ROOT / "artifacts" / "model.joblib"
PANEL_PATH = ROOT / "data" / "processed" / "panel.csv"
PRICES_PATH = ROOT / "data" / "processed" / "food_prices.csv"


def fit(name, cols, rows):
    return CANDIDATES[name]().fit(rows[cols], rows["target_inflation"]), len(rows)


def fit_score(name, cols, fit_rows, eval_rows):
    model, n_train = fit(name, cols, fit_rows)
    return model, {**metrics(eval_rows["target_inflation"], model.predict(eval_rows[cols])), "n_train": n_train}


def cv_score(name, cols, cv):
    """Metrics pooled over every fold's predictions, plus MAE per validation year."""
    preds = [(va["target_inflation"], fit(name, cols, tr)[0].predict(va[cols])) for _, tr, va in cv]
    return {**metrics(pd.concat([y for y, _ in preds]), np.concatenate([p for _, p in preds])),
            "mae_by_year": {year: metrics(y, p)["mae"] for (year, _, _), (y, p) in zip(cv, preds)}}


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

    # Phase 3-6: every row has every candidate feature (missing food prices are 0 + flag),
    # so all configs train and score on the same rows.
    feats = build_features(panel, prices).dropna(subset=columns(FEATURE_GROUPS))
    dev, test = split(feats)
    cv = folds(dev)
    assert all(tr["target_date"].max() < va["target_date"].min() for _, tr, va in cv)
    assert dev["target_date"].max() < test["target_date"].min()
    cv_val = pd.concat([va for _, _, va in cv])
    print(f"dev {len(dev)} | cv val {len(cv_val)} ({VAL_YEARS[0]}-{VAL_YEARS[-1]}) | test {len(test)} rows")

    results = {"split": {"val_years": list(VAL_YEARS), "val_end": VAL_END.strftime("%Y-%m"),
                         "test_end": test["target_date"].max().strftime("%Y-%m"),
                         "rows": {"dev": len(dev), "cv_val": len(cv_val), "test": len(test)}},
               "validation": {name: metrics(cv_val["target_inflation"], f(cv_val)) for name, f in BASELINES.items()},
               "ablation": [], "selected_groups": {}}

    # Greedy forward selection: a feature group stays only if it lowers pooled rolling-origin MAE.
    for name in CANDIDATES:
        groups = ["lags"]
        best = cv_score(name, columns(groups), cv)
        results["ablation"].append({"model": name, "groups": list(groups), **best, "kept": True})
        for grp in [g for g in FEATURE_GROUPS if g != "lags"]:
            score = cv_score(name, columns(groups + [grp]), cv)
            kept = score["mae"] < best["mae"]
            results["ablation"].append({"model": name, "groups": groups + [grp], **score, "kept": kept})
            if kept:
                groups, best = groups + [grp], score
        results["selected_groups"][name] = groups
        results["validation"][name] = best

    selected = min(CANDIDATES, key=lambda n: results["validation"][n]["mae"])
    results["selected_model"] = selected

    # Phase 8: refit on all dev rows, score once on the untouched test period
    preds = test[["city", "date", "target_date", "target_inflation"]].copy()
    for name, f in BASELINES.items():
        preds[name] = f(test)
    for name in CANDIDATES:
        cols = columns(results["selected_groups"][name])
        model = fit(name, cols, dev)[0]
        preds[name] = model.predict(test[cols])
    results["test"] = {n: metrics(preds["target_inflation"], preds[n]) for n in [*BASELINES, *CANDIDATES]}
    # Diagnostic only (selection above never sees test): how each kept ablation step of the selected model does on test.
    results["test_ablation_diagnostic"] = [
        {"model": selected, "groups": a["groups"], **fit_score(selected, columns(a["groups"]), dev, test)[1]}
        for a in results["ablation"] if a["model"] == selected and a["kept"]]
    preds.to_csv(METRICS_DIR / "test_predictions.csv", index=False, date_format="%Y-%m")
    (METRICS_DIR / "metrics.json").write_text(json.dumps(results, indent=2))

    # Phase 9: same model + feature config refitted on every labeled row; this fitted pipeline
    # (scaler included) is what the API serves. Test metrics above describe this procedure.
    cols = columns(results["selected_groups"][selected])
    everything = pd.concat([dev, test])
    model = fit(selected, cols, everything)[0]
    joblib.dump({"model": model, "features": cols, "model_name": selected,
                 "trained_on_targets_through": everything["target_date"].max().strftime("%Y-%m"),
                 "cities": sorted(panel["city"].unique())}, MODEL_PATH)

    print(json.dumps({k: results[k] for k in ["selected_model", "selected_groups", "validation", "test"]}, indent=2))


if __name__ == "__main__":
    main()
