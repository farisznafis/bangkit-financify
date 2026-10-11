import math

import joblib
import pandas as pd
import pytest

from src.inference import MODEL_PATH, ForecastError, Forecaster

pytestmark = pytest.mark.skipif(not MODEL_PATH.exists(), reason="run train.py first")


@pytest.fixture(scope="module")
def fc():
    return Forecaster()


def test_forecast_shape_and_finite(fc):
    r = fc.forecast("Kota Yogyakarta")
    last = fc.feats.loc[fc.feats["city"] == "YOGYAKARTA", "date"].max()
    assert r["city"] == "YOGYAKARTA" and r["forecast_period"] == (last + pd.offsets.MonthBegin(1)).strftime("%Y-%m")
    assert math.isfinite(r["predicted_inflation"])
    assert r["trend"] in {"up", "down", "unchanged"}
    assert fc.model.n_features_in_ == len(fc.features)


def test_unsupported_city(fc):
    with pytest.raises(ForecastError) as e:
        fc.forecast("Atlantis")
    assert e.value.code == "unsupported_city"


def test_stored_preprocessing_reused(fc):
    # The served model is the exact object saved by train.py, not refitted at load time.
    stored = joblib.load(MODEL_PATH)["model"]
    x = fc.feats.dropna(subset=fc.features).tail(5)[fc.features]
    assert (stored.predict(x) == fc.model.predict(x)).all()


def test_api_errors_are_structured():
    from app import app
    client = app.test_client()
    r = client.post("/api/forecast", json={"city": "Atlantis"})
    assert r.status_code == 400 and r.json["error"]["code"] == "unsupported_city"
    r = client.post("/api/financial-impact", json={"city": "Yogyakarta", "current_savings": 0,
                                                   "monthly_income": 5, "monthly_expenses": 9, "goal_amount": 100})
    assert r.json["error"]["code"] == "no_saving_capacity"
    r = client.post("/api/financial-impact", json={"city": "Yogyakarta", "current_savings": 15_000_000,
                                                   "monthly_income": 10_000_000, "monthly_expenses": 6_000_000,
                                                   "goal_amount": 100_000_000})
    assert r.status_code == 200 and r.json["inflation_adjusted_goal"] > 100_000_000
