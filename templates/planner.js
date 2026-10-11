// JS twin of src/financial.py so the static site needs no server; tests/test_planner_js.py keeps them in sync.
function plan(currentSavings, monthlyIncome, monthlyExpenses, goalAmount, annualInflationPct) {
  const fail = (code, message) => { const e = new Error(message); e.code = code; throw e; };
  const values = {current_savings: currentSavings, monthly_income: monthlyIncome, monthly_expenses: monthlyExpenses,
    goal_amount: goalAmount, annual_inflation_pct: annualInflationPct};
  for (const [k, v] of Object.entries(values)) {
    if (typeof v !== "number" || !Number.isFinite(v)) fail("invalid_input", `${k} must be a finite number`);
    if (v < 0 && k !== "annual_inflation_pct") fail("negative_input", `${k} must not be negative`);
  }
  if (goalAmount <= 0) fail("invalid_goal", "goal_amount must be greater than 0");
  if (!(annualInflationPct > -50 && annualInflationPct < 100)) fail("invalid_input", "annual_inflation_pct must be between -50 and 100");
  const monthlySaving = monthlyIncome - monthlyExpenses;
  if (monthlySaving <= 0 && currentSavings < goalAmount) fail("no_saving_capacity", "monthly_expenses must be lower than monthly_income");

  const r = annualInflationPct / 100;
  for (let n = 0; n <= 1200; n++) {
    const adjustedGoal = goalAmount * (1 + r) ** (n / 12);
    if (currentSavings + monthlySaving * n >= adjustedGoal) {
      return {goal_today: Math.round(goalAmount), inflation_adjusted_goal: Math.round(adjustedGoal),
        monthly_saving_capacity: Math.round(monthlySaving), months_to_goal: n,
        time_to_goal: {years: Math.floor(n / 12), months: n % 12}, annual_inflation_assumption_pct: annualInflationPct,
        note: "Planning estimate, not financial advice. Assumes constant income, expenses and inflation, and no investment return."};
    }
  }
  fail("goal_unreachable", "goal is not reachable within 100 years under this inflation assumption");
}
if (typeof module !== "undefined") module.exports = { plan };
