"""Baselines, candidate models and metrics."""
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASELINES = {
    "naive": lambda X: X["inflation_mtm"].to_numpy(),           # y[t+1] = y[t]
    "seasonal_naive": lambda X: X["inflation_lag_11"].to_numpy(),  # y[t+1] = y[t-11]
}

# The scaler lives inside the pipeline, so it is fitted on training rows only and saved with the model.
CANDIDATES = {
    "ridge": lambda: make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hist_gbr": lambda: HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=0),
}


def metrics(y, pred):
    err = np.asarray(pred) - np.asarray(y)
    return {"mae": round(float(np.mean(np.abs(err))), 4), "rmse": round(float(np.sqrt(np.mean(err ** 2))), 4), "n": int(len(err))}
