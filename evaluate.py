"""Diagnostics for the test period written by train.py: error by city/month, high-volatility months, plots."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.models import metrics
from train import METRICS_DIR


def main():
    preds = pd.read_csv(METRICS_DIR / "test_predictions.csv")
    selected = json.loads((METRICS_DIR / "metrics.json").read_text())["selected_model"]
    models = ["naive", "seasonal_naive", "ridge", "hist_gbr"]
    abs_err = preds[models].sub(preds["target_inflation"], axis=0).abs()

    abs_err.groupby(preds["city"]).mean().round(4).sort_values(selected).to_csv(METRICS_DIR / "mae_by_city.csv")
    abs_err.groupby(preds["target_date"]).mean().round(4).to_csv(METRICS_DIR / "mae_by_month.csv")

    # High volatility = target months whose cross-city mean |inflation| is in the top quartile of the test period.
    level = preds["target_inflation"].abs().groupby(preds["target_date"]).mean()
    hot = level[level >= level.quantile(0.75)].index
    mask = preds["target_date"].isin(hot)
    summary = {"high_volatility_months": list(hot),
               "high_volatility": {m: metrics(preds.loc[mask, "target_inflation"], preds.loc[mask, m]) for m in models},
               "other_months": {m: metrics(preds.loc[~mask, "target_inflation"], preds.loc[~mask, m]) for m in models}}
    (METRICS_DIR / "volatility.json").write_text(json.dumps(summary, indent=2))

    monthly = preds.groupby("target_date")[["target_inflation", selected, "naive"]].mean()
    fig, ax = plt.subplots(figsize=(10, 4))
    monthly.plot(ax=ax, marker="o")
    ax.set(title="Test period: mean across cities, actual vs predicted (m-t-m %)", xlabel="", ylabel="%")
    fig.tight_layout()
    fig.savefig(METRICS_DIR / "actual_vs_predicted.png", dpi=120)

    fig, ax = plt.subplots(figsize=(6, 4))
    (preds[selected] - preds["target_inflation"]).plot.hist(bins=60, ax=ax)
    ax.set(title=f"{selected} residuals (pred - actual), test", xlabel="pp")
    fig.tight_layout()
    fig.savefig(METRICS_DIR / "residuals.png", dpi=120)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
