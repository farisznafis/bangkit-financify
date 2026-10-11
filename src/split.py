"""Chronological split on the target month (features only look backwards from it)."""
import pandas as pd

VAL_YEARS = (2021, 2022, 2023, 2024)  # rolling origin: each year is scored by a model fitted on all earlier targets
VAL_END = pd.Timestamp("2024-12-01")  # test = 2025-01 onwards, never used for selection


def split(features):
    """(dev, test): dev holds every labeled target up to VAL_END."""
    labeled = features.dropna(subset=["target_inflation"])
    t = labeled["target_date"]
    return labeled[t <= VAL_END], labeled[t > VAL_END]


def folds(dev):
    """[(year, train, val)] expanding-window folds over VAL_YEARS."""
    y = dev["target_date"].dt.year
    return [(year, dev[y < year], dev[y == year]) for year in VAL_YEARS]
