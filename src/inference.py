"""Serve forecasts from the artifact saved by train.py. Nothing is fitted here."""
import joblib
import numpy as np
import pandas as pd

from src.data import ROOT
from src.features import build_features

MODEL_PATH = ROOT / "artifacts" / "model.joblib"
PANEL_PATH = ROOT / "data" / "processed" / "panel.csv"
PRICES_PATH = ROOT / "data" / "processed" / "food_prices.csv"


class ForecastError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def normalize_city(name):
    name = str(name).strip().upper()
    return name[5:] if name.startswith("KOTA ") else name


class Forecaster:
    def __init__(self, model_path=MODEL_PATH, panel_path=PANEL_PATH, prices_path=PRICES_PATH):
        art = joblib.load(model_path)
        self.model, self.features, self.model_name = art["model"], art["features"], art["model_name"]
        self.cities = art["cities"]
        self.feats = build_features(pd.read_csv(panel_path, parse_dates=["date"]),
                                    pd.read_csv(prices_path, parse_dates=["date"]))

    def _rows(self, city):
        city = normalize_city(city)
        if city not in self.cities:
            raise ForecastError("unsupported_city", f"unsupported city: {city!r}")
        return city, self.feats[self.feats["city"] == city]

    def forecast(self, city):
        city, rows = self._rows(city)
        last = rows.iloc[-1]
        x = last[self.features].to_frame().T.astype(float)
        if x.isna().any(axis=None):
            raise ForecastError("missing_forecast_data", f"{city}: latest 12-month window is incomplete")
        pred = float(self.model.predict(x)[0])
        if not np.isfinite(pred):
            raise ForecastError("invalid_prediction", "model returned a non-finite value")
        prev = float(last["inflation_mtm"])
        change = round(pred - prev, 2)
        return {
            "city": city,
            "as_of": last["date"].strftime("%Y-%m"),
            "forecast_period": last["target_date"].strftime("%Y-%m"),
            "previous_inflation": round(prev, 2),
            "predicted_inflation": round(pred, 2),
            "change": change,
            "trend": "up" if change > 0 else "down" if change < 0 else "unchanged",
            "unit": "percent, month-to-month",
            "model": self.model_name,
            "history": [{"period": d.strftime("%Y-%m"), "inflation": None if np.isnan(v) else round(float(v), 2)}
                        for d, v in rows[["date", "inflation_mtm"]].tail(24).itertuples(index=False)],
        }

    def trailing_annual_inflation(self, city):
        """Compounded last-12-month inflation (%), the default long-term planning assumption."""
        city, rows = self._rows(city)
        last12 = rows["inflation_mtm"].tail(12)
        if last12.isna().any():
            raise ForecastError("missing_forecast_data", f"{city}: last 12 months incomplete")
        return round(float(((1 + last12 / 100).prod() - 1) * 100), 2), rows["date"].iloc[-1].strftime("%Y-%m")
