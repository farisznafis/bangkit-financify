import json
import os

import pandas as pd
from flask import Flask, jsonify, render_template, request

from src.data import ROOT
from src.financial import PlannerError, plan
from src.inference import ForecastError, Forecaster

app = Flask(__name__)
forecaster = Forecaster()
METRICS = json.loads((ROOT / "artifacts" / "metrics" / "metrics.json").read_text())


def snapshot():
    """Latest forecast for every servable city; the UI embeds this and needs no API calls."""
    data = {}
    for city in forecaster.cities:
        try:
            data[city] = {**forecaster.forecast(city), "annual_inflation_12m": forecaster.trailing_annual_inflation(city)[0]}
        except ForecastError:
            pass  # latest 12-month window incomplete; left out of the dropdown
    return data


SNAPSHOT = snapshot()


def error(code, message, status=400):
    return jsonify({"error": {"code": code, "message": message}}), status


@app.errorhandler(ForecastError)
@app.errorhandler(PlannerError)
def handle_domain_error(e):
    return error(e.code, str(e))


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data.get("city"):
        raise ForecastError("invalid_request", "JSON body with a 'city' field is required")
    return data


@app.get("/")
def index():
    test = METRICS["test"]
    return render_template("index.html", data=SNAPSHOT, model=forecaster.model_name,
                           mae=test[forecaster.model_name]["mae"], naive_mae=test["naive"]["mae"],
                           uses_food=any(f.endswith("_price_mom") for f in forecaster.features),
                           test_start=str(pd.Period(METRICS["split"]["val_end"], "M") + 1),
                           test_end=METRICS["split"]["test_end"])


@app.post("/api/forecast")
def api_forecast():
    city = body()["city"]
    annual, _ = forecaster.trailing_annual_inflation(city)
    return jsonify({**forecaster.forecast(city), "annual_inflation_12m": annual})


@app.post("/api/financial-impact")
def api_financial_impact():
    data = body()
    forecast = forecaster.forecast(data["city"])
    if "annual_inflation" in data:
        annual, source = data["annual_inflation"], "user-provided assumption"
    else:
        annual, as_of = forecaster.trailing_annual_inflation(data["city"])
        source = f"{forecast['city']} compounded month-to-month inflation, 12 months to {as_of}"
    result = plan(data.get("current_savings"), data.get("monthly_income"), data.get("monthly_expenses"),
                  data.get("goal_amount"), annual)
    return jsonify({"city": forecast["city"], "short_term_forecast": {k: forecast[k] for k in
                    ("forecast_period", "predicted_inflation", "trend")},
                    "assumption_source": source, **result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
