from src.data import load_panel
from src.features import build_features
from src.split import VAL_END, VAL_YEARS, folds, split


def test_chronological_no_future_rows_in_train():
    dev, test = split(build_features(load_panel()))
    assert dev["target_date"].max() <= VAL_END < test["target_date"].min()
    # features of a row never come from after its own target month
    assert (dev["date"] < dev["target_date"]).all()
    cv = folds(dev)
    assert [y for y, _, _ in cv] == list(VAL_YEARS)
    for year, train, val in cv:
        assert train["target_date"].dt.year.max() < year == val["target_date"].dt.year.min() == val["target_date"].dt.year.max()
        assert not set(train.index) & set(val.index)
