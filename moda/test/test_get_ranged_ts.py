import os

import pandas as pd
import pytest

from moda.dataprep.raw_to_ts import raw_to_ts

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def test_raw_to_ts():
    path = os.path.join(THIS_DIR, os.pardir, 'test/sample-raw.csv')
    raw = pd.read_csv(path)
    ts = raw_to_ts(raw)
    assert isinstance(ts.index,pd.DatetimeIndex)


def test_raw_to_ts_no_date():
    path = os.path.join(THIS_DIR, os.pardir, 'test/sample-raw.csv')
    raw = pd.read_csv(path)
    ts = raw_to_ts(raw)
    ts = ts.drop(columns='date')
    with pytest.raises(ValueError):
        raw_to_ts(ts)



def test_ts_to_range():
    path = os.path.join(THIS_DIR, os.pardir, 'test/sample-raw.csv')
    raw = pd.read_csv(path)
    ts = raw_to_ts(raw)




