"""Offline tests for getCloudLocations and getCloudAccounts paging (no network, no credentials needed)."""
import os
import sys
import inspect

import pytest

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from aanalytics2.aanalytics2 import Analytics


class PagedConnector:
    """Serves pages that use the export locations shape ('first' and 'last'), and records each request."""

    def __init__(self, total_pages):
        self.total_pages = total_pages
        self.calls = []

    def getData(self, url, params=None, headers=None, **kwargs):
        self.calls.append(dict(params or {}))
        if len(self.calls) > 10:
            pytest.fail("Too many requests: the paging loop does not stop")
        if ("limit" in (params or {})) != ("page" in (params or {})):
            # The live API answers this way when only one of the two is sent.
            return {"status": "BAD_REQUEST", "message": 'Query parameter "limit", "page" both required if used.'}
        number = int((params or {}).get("page", 0))
        return {"content": [{"id": f"item{number}"}], "number": number,
                "first": number == 0, "last": number == self.total_pages - 1}


def make_analytics(total_pages) -> Analytics:
    """Builds an Analytics instance without running __init__ (which would need a real token)."""
    ags = Analytics.__new__(Analytics)
    ags.endpoint_company = "https://analytics.adobe.io/api/comp1"
    ags.header = {}
    ags.loggingEnabled = False
    ags.connector = PagedConnector(total_pages)
    return ags


def test_getCloudLocations_sends_its_filters():
    ags = make_analytics(1)
    ags.getCloudLocations(accountUuid="acc-1", application="DATA_FEED", limit=50)
    # The API answers BAD_REQUEST when "limit" is sent without "page".
    assert ags.connector.calls[0] == {"accountUuid": "acc-1", "application": "DATA_FEED", "limit": 50, "page": 0}


def test_getCloudLocations_reads_every_page_once_and_keeps_the_filters():
    ags = make_analytics(3)
    data = ags.getCloudLocations(application="DATA_FEED")
    assert [item["id"] for item in data] == ["item0", "item1", "item2"]
    assert [call.get("page", 0) for call in ags.connector.calls] == [0, 1, 2]
    assert all(call["application"] == "DATA_FEED" for call in ags.connector.calls)


def test_getCloudAccounts_sends_its_filter():
    ags = make_analytics(1)
    ags.getCloudAccounts(accountType="s3")
    assert ags.connector.calls[0] == {"type": "s3", "limit": 1000, "page": 0}


def test_getCloudAccounts_reads_every_page_once_and_keeps_the_filter():
    ags = make_analytics(3)
    data = ags.getCloudAccounts(accountType="GCS")
    assert [item["id"] for item in data] == ["item0", "item1", "item2"]
    assert [call.get("page", 0) for call in ags.connector.calls] == [0, 1, 2]
    assert all(call["type"] == "GCS" for call in ags.connector.calls)
