"""Offline tests for error bodies in paged listings (no network, no credentials needed)."""
import os
import sys
import inspect

import pandas as pd
import pytest

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from aanalytics2.aanalytics2 import Analytics

ERROR_BODY = {"errorCode": "server_error", "errorDescription": "Internal error", "errorId": "abc-123"}
GATEWAY_ERROR = {"error_code": "403025", "message": "Profile is not valid"}
CONNECTOR_ERROR = {"error": "Request Error"}


def page(items, number, total):
    return {"content": items, "number": number, "totalPages": total, "lastPage": number == total - 1}


class PagedConnector:
    """Returns the response for each page number. A missing page number means page 0."""

    def __init__(self, pages):
        self.pages = pages

    def getData(self, url, params=None, headers=None, **kwargs):
        return self.pages[int((params or {}).get("page", 0))]


def make_analytics(pages) -> Analytics:
    """Builds an Analytics instance without running __init__ (which would need a real token)."""
    ags = Analytics.__new__(Analytics)
    ags.endpoint_company = "https://analytics.adobe.io/api/comp1"
    ags.header = {}
    ags.loggingEnabled = False
    ags.connector = PagedConnector(pages)
    return ags


def rs(n):
    return {"rsid": f"rs{n}", "name": f"Suite {n}"}


def vrs(n):
    return {"id": f"vrs{n}", "name": f"Virtual {n}"}


# getReportSuites

def test_getReportSuites_first_page_error_raises_a_clear_error():
    with pytest.raises(ValueError, match="getReportSuites.*server_error: Internal error"):
        make_analytics({0: ERROR_BODY}).getReportSuites()


@pytest.mark.parametrize("error", [ERROR_BODY, GATEWAY_ERROR, CONNECTOR_ERROR])
def test_getReportSuites_later_page_error_raises_instead_of_dropping_the_page(error):
    pages = {0: page([rs(0)], 0, 3), 1: error, 2: page([rs(2)], 2, 3)}
    with pytest.raises(ValueError, match="getReportSuites"):
        make_analytics(pages).getReportSuites()


def test_getReportSuites_gateway_error_names_the_code_and_message():
    pages = {0: page([rs(0)], 0, 2), 1: GATEWAY_ERROR}
    with pytest.raises(ValueError, match="403025: Profile is not valid"):
        make_analytics(pages).getReportSuites()


def test_getReportSuites_still_combines_all_pages():
    pages = {0: page([rs(0)], 0, 3), 1: page([rs(1)], 1, 3), 2: page([rs(2)], 2, 3)}
    df = make_analytics(pages).getReportSuites()
    assert isinstance(df, pd.DataFrame)
    assert df["rsid"].tolist() == ["rs0", "rs1", "rs2"]


# getVirtualReportSuites

def test_getVirtualReportSuites_first_page_error_raises_a_clear_error():
    with pytest.raises(ValueError, match="getVirtualReportSuites.*server_error: Internal error"):
        make_analytics({0: ERROR_BODY}).getVirtualReportSuites()


def test_getVirtualReportSuites_later_page_error_raises_instead_of_dropping_the_page():
    pages = {0: page([vrs(0)], 0, 2), 1: ERROR_BODY}
    with pytest.raises(ValueError, match="getVirtualReportSuites"):
        make_analytics(pages).getVirtualReportSuites()


def test_getVirtualReportSuites_still_combines_all_pages():
    pages = {0: page([vrs(0)], 0, 2), 1: page([vrs(1)], 1, 2)}
    assert make_analytics(pages).getVirtualReportSuites()["vrsid"].tolist() == ["vrs0", "vrs1"]


# getSegments

def test_getSegments_first_page_error_raises_a_clear_error():
    with pytest.raises(ValueError, match="getSegments.*server_error: Internal error"):
        make_analytics({0: ERROR_BODY}).getSegments()


def test_getSegments_later_page_error_raises_a_clear_error():
    pages = {0: page([{"id": "s0"}], 0, 2), 1: GATEWAY_ERROR}
    with pytest.raises(ValueError, match="getSegments.*403025"):
        make_analytics(pages).getSegments(format="raw")


# getCalculatedMetrics

def test_getCalculatedMetrics_first_page_error_raises_a_clear_error():
    with pytest.raises(ValueError, match="getCalculatedMetrics.*server_error: Internal error"):
        make_analytics({0: ERROR_BODY}).getCalculatedMetrics()


def test_getCalculatedMetrics_later_page_error_raises_a_clear_error():
    pages = {0: page([{"id": "cm0"}], 0, 2), 1: CONNECTOR_ERROR}
    with pytest.raises(ValueError, match="getCalculatedMetrics.*Request Error"):
        make_analytics(pages).getCalculatedMetrics(format="raw")
