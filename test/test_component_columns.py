"""Offline tests for the DataFrame columns of getDimensions and getMetrics (no network, no credentials needed)."""
import os
import sys
import inspect

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from aanalytics2.aanalytics2 import Analytics

DIMENSIONS = [{"id": "variables/page", "name": "Page", "category": "Content", "type": "string"}]
METRICS = [{"id": "metrics/visits", "name": "Visits", "category": "Traffic", "type": "int"}]


class FakeConnector:
    def __init__(self, response):
        self.response = response

    def getData(self, url, params=None, headers=None, **kwargs):
        return self.response


def make_analytics(response) -> Analytics:
    """Builds an Analytics instance without running __init__ (which would need a real token)."""
    ags = Analytics.__new__(Analytics)
    ags.endpoint_company = "https://analytics.adobe.io/api/comp1"
    ags.header = {}
    ags.loggingEnabled = False
    ags.connector = FakeConnector(response)
    return ags


def test_getDimensions_adds_a_missing_description_column():
    df = make_analytics(DIMENSIONS).getDimensions("rs1", description=True)
    assert list(df.columns) == ["id", "name", "category", "type", "parent", "pathable", "description"]
    assert df["description"].tolist() == [""]


def test_getMetrics_adds_missing_default_columns():
    df = make_analytics(METRICS).getMetrics("rs1")
    assert list(df.columns) == ["id", "name", "category", "type", "precision", "segmentable"]
    assert df["precision"].tolist() == [""]


def test_getMetrics_adds_missing_dataGroup_and_description_columns():
    df = make_analytics(METRICS).getMetrics("rs1", dataGroup=True, description=True)
    assert list(df.columns)[-2:] == ["dataGroup", "description"]
    assert df["dataGroup"].tolist() == [""]


def test_getMetrics_keeps_values_that_are_present():
    metrics = [{**METRICS[0], "precision": 0, "segmentable": True, "dataGroup": "Traffic"}]
    df = make_analytics(metrics).getMetrics("rs1", dataGroup=True)
    assert df["precision"].tolist() == [0]
    assert df["dataGroup"].tolist() == ["Traffic"]
