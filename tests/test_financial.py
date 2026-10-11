import pytest

from src.financial import PlannerError, plan


def test_zero_inflation_is_plain_division():
    r = plan(15_000_000, 10_000_000, 6_000_000, 100_000_000, 0)
    assert r["months_to_goal"] == 22 and r["inflation_adjusted_goal"] == 100_000_000  # ceil(85M / 4M)


def test_positive_inflation_takes_longer_and_converges():
    r = plan(15_000_000, 10_000_000, 6_000_000, 100_000_000, 3.0)
    n = r["months_to_goal"]
    assert n > 22
    goal = lambda m: 100_000_000 * 1.03 ** (m / 12)
    assert 15_000_000 + 4_000_000 * n >= goal(n)
    assert 15_000_000 + 4_000_000 * (n - 1) < goal(n - 1)  # n is the first month that works


def test_savings_already_cover_goal():
    assert plan(200, 10, 10, 100, 5)["months_to_goal"] == 0


def test_expenses_ge_income():
    with pytest.raises(PlannerError) as e:
        plan(0, 5, 5, 100, 3)
    assert e.value.code == "no_saving_capacity"


@pytest.mark.parametrize("args,code", [
    ((-1, 10, 5, 100, 3), "negative_input"),
    ((0, 10, 5, 0, 3), "invalid_goal"),
    ((0, "10", 5, 100, 3), "invalid_input"),
    ((0, 10, 5, 100, float("nan")), "invalid_input"),
])
def test_invalid_inputs(args, code):
    with pytest.raises(PlannerError) as e:
        plan(*args)
    assert e.value.code == code


def test_unreachable_goal():
    with pytest.raises(PlannerError) as e:
        plan(0, 101, 100, 1_000_000, 50)
    assert e.value.code == "goal_unreachable"
