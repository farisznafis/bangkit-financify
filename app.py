import os

from flask import Flask, jsonify, render_template, request

from src.financial import PlannerError, plan
from src.inference import ForecastError, Forecaster

app = Flask(__name__)
forecaster = Forecaster()


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
    return render_template("index.html", cities=forecaster.cities)


@app.post("/api/forecast")
def api_forecast():
    return jsonify(forecaster.forecast(body()["city"]))


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
