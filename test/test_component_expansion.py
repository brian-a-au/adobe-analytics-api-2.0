"""Offline tests for the expansion argument of getDimensions and getMetrics (no network, no credentials needed)."""
import os
import sys
import inspect

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from aanalytics2.aanalytics2 import Analytics

DIMENSIONS = [{"id": "variables/page", "name": "Page", "allowedForReporting": True, "tags": []}]
METRICS = [{"id": "metrics/visits", "name": "Visits", "allowedForReporting": True, "tags": []}]


class RecordingConnector:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def getData(self, url, params=None, headers=None, **kwargs):
        self.calls.append(dict(params or {}))
        return self.response


def make_analytics(response) -> Analytics:
    """Builds an Analytics instance without running __init__ (which would need a real token)."""
    ags = Analytics.__new__(Analytics)
    ags.endpoint_company = "https://analytics.adobe.io/api/comp1"
    ags.header = {}
    ags.loggingEnabled = False
    ags.connector = RecordingConnector(response)
    return ags


def test_getDimensions_sends_the_expansion():
    ags = make_analytics(DIMENSIONS)
    ags.getDimensions("rs1", expansion="allowedForReporting,dataType", format="raw")
    assert ags.connector.calls[0]["expansion"] == "allowedForReporting,dataType"


def test_getDimensions_combines_tags_and_an_expansion_list():
    ags = make_analytics(DIMENSIONS)
    ags.getDimensions("rs1", tags=True, expansion=["allowedForReporting", "tags"], format="raw")
    assert ags.connector.calls[0]["expansion"] == "tags,allowedForReporting"


def test_getDimensions_keeps_expanded_fields_in_the_dataframe():
    df = make_analytics(DIMENSIONS).getDimensions("rs1", expansion="allowedForReporting,dataType")
    assert list(df.columns)[-2:] == ["allowedForReporting", "dataType"]
    assert df["allowedForReporting"].tolist() == [True]
    assert df["dataType"].tolist() == [""]


def test_getDimensions_with_tags_keeps_the_tags_column():
    df = make_analytics(DIMENSIONS).getDimensions("rs1", tags=True)
    assert "tags" in df.columns


def test_getDimensions_without_expansion_sends_none():
    ags = make_analytics(DIMENSIONS)
    ags.getDimensions("rs1", format="raw")
    assert "expansion" not in ags.connector.calls[0]


def test_getMetrics_sends_the_expansion():
    ags = make_analytics(METRICS)
    ags.getMetrics("rs1", tags=True, expansion="allowedForReporting", format="raw")
    assert ags.connector.calls[0]["expansion"] == "tags,allowedForReporting"


def test_getMetrics_keeps_expanded_fields_in_the_dataframe():
    df = make_analytics(METRICS).getMetrics("rs1", expansion=["allowedForReporting", "categories"])
    assert list(df.columns)[-2:] == ["allowedForReporting", "categories"]
    assert df["allowedForReporting"].tolist() == [True]


def test_expansion_list_items_are_split_on_commas_and_empty_items_skipped():
    ags = make_analytics(DIMENSIONS)
    ags.getDimensions("rs1", tags=True, expansion=["attributionModel,allowedForReporting", None, "", "tags"],
                      format="raw")
    assert ags.connector.calls[0]["expansion"] == "tags,attributionModel,allowedForReporting"
