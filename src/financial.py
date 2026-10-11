"""Inflation-adjusted time-to-goal. Inflation grows the goal's cost; it is never treated as money."""
import math

MAX_MONTHS = 1200  # 100 years


class PlannerError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def plan(current_savings, monthly_income, monthly_expenses, goal_amount, annual_inflation_pct):
    """Smallest n (months) with savings + n*monthly_saving >= goal * (1+annual)^(n/12).

    Savings are assumed to earn no return; the annual rate is a long-term planning assumption,
    not the one-month model forecast.
    """
    values = {"current_savings": current_savings, "monthly_income": monthly_income,
              "monthly_expenses": monthly_expenses, "goal_amount": goal_amount,
              "annual_inflation_pct": annual_inflation_pct}
    for k, v in values.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise PlannerError("invalid_input", f"{k} must be a finite number")
        if v < 0 and k != "annual_inflation_pct":
            raise PlannerError("negative_input", f"{k} must not be negative")
    if goal_amount <= 0:
        raise PlannerError("invalid_goal", "goal_amount must be greater than 0")
    if not -50 < annual_inflation_pct < 100:
        raise PlannerError("invalid_input", "annual_inflation_pct must be between -50 and 100")
    monthly_saving = monthly_income - monthly_expenses
    if monthly_saving <= 0 and current_savings < goal_amount:
        raise PlannerError("no_saving_capacity", "monthly_expenses must be lower than monthly_income")

    r = annual_inflation_pct / 100
    for n in range(MAX_MONTHS + 1):
        adjusted_goal = goal_amount * (1 + r) ** (n / 12)
        if current_savings + monthly_saving * n >= adjusted_goal:
            break
    else:
        raise PlannerError("goal_unreachable", "goal is not reachable within 100 years under this inflation assumption")

    return {
        "goal_today": round(goal_amount),
        "inflation_adjusted_goal": round(adjusted_goal),
        "monthly_saving_capacity": round(monthly_saving),
        "months_to_goal": n,
        "time_to_goal": {"years": n // 12, "months": n % 12},
        "annual_inflation_assumption_pct": annual_inflation_pct,
        "note": "Planning estimate, not financial advice. Assumes constant income, expenses and inflation, and no investment return.",
    }
