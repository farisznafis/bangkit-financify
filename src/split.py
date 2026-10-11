"""Chronological split on the target month (features only look backwards from it)."""
import pandas as pd

TRAIN_END = pd.Timestamp("2023-12-01")  # targets 2009..2023
VAL_END = pd.Timestamp("2024-12-01")    # targets 2024; test = 2025-01 onwards


def split(features):
    labeled = features.dropna(subset=["target_inflation"])
    t = labeled["target_date"]
    return (labeled[t <= TRAIN_END],
            labeled[(t > TRAIN_END) & (t <= VAL_END)],
            labeled[t > VAL_END])
