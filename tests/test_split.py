from src.data import load_panel
from src.features import build_features
from src.split import TRAIN_END, VAL_END, split


def test_chronological_no_future_rows_in_train():
    train, val, test = split(build_features(load_panel()))
    assert train["target_date"].max() <= TRAIN_END < val["target_date"].min()
    assert val["target_date"].max() <= VAL_END < test["target_date"].min()
    # features of a training row never come from after its own target month
    assert (train["date"] < train["target_date"]).all()
    assert not set(train.index) & set(val.index) and not set(val.index) & set(test.index)
