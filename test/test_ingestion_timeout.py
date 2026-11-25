"""Offline tests for timeouts in the Data Insertion and Bulk ingestion APIs (no network, no credentials needed)."""
import os
import sys
import inspect

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from aanalytics2 import connector, ingestion


class FakeResponse:
    def json(self):
        return {}


def record_requests(monkeypatch) -> list:
    """Replaces requests.get and requests.post in the ingestion module and records each timeout."""
    seen = []

    def send(*args, timeout=None, **kwargs):
        seen.append(timeout)
        return FakeResponse()

    monkeypatch.setattr(ingestion.requests, "get", send)
    monkeypatch.setattr(ingestion.requests, "post", send)
    return seen


def test_diapi_get_and_post_use_the_default_timeout(monkeypatch):
    seen = record_requests(monkeypatch)
    diapi = ingestion.DIAPI(rsid="rs1", tracking_server="example.sc.omtrdc.net")
    diapi.getMethod(pageName="home")
    diapi.postMethod(pageName="home")
    assert seen == [connector.DEFAULT_TIMEOUT, connector.DEFAULT_TIMEOUT]


def test_diapi_timeout_argument_replaces_the_default(monkeypatch):
    seen = record_requests(monkeypatch)
    diapi = ingestion.DIAPI(rsid="rs1", tracking_server="example.sc.omtrdc.net", timeout=[5, 30])
    diapi.getMethod(pageName="home")
    assert seen == [(5, 30)]


def make_bulk(timeout) -> ingestion.Bulkapi:
    """Builds a Bulkapi instance without running __init__ (which would need a real token)."""
    bulk = ingestion.Bulkapi.__new__(ingestion.Bulkapi)
    bulk.endpoint = "https://analytics-collection.example"
    bulk.header = {}
    bulk._createdFiles = []
    bulk.connector = type("Connector", (), {"proxies": None, "timeout": timeout})()
    return bulk


def test_bulk_validation_uses_the_connector_timeout(monkeypatch, tmp_path):
    seen = record_requests(monkeypatch)
    data = tmp_path / "data.csv"
    data.write_text("timestamp,marketingCloudVisitorID\n")
    make_bulk((10, 120)).validation(str(data))
    assert seen == [(10, 120)]


def test_bulk_sendFiles_uses_the_connector_timeout(monkeypatch, tmp_path):
    seen = record_requests(monkeypatch)
    data = tmp_path / "data.csv.gz"
    data.write_bytes(b"not checked by this test")
    make_bulk((10, 120)).sendFiles(str(data))
    assert seen == [(10, 120)]


def test_bulk_sendFiles_removes_its_temp_files_when_an_upload_fails(monkeypatch, tmp_path):
    import pytest
    import requests

    def timed_out(*args, **kwargs):
        raise requests.exceptions.ReadTimeout("read timed out")

    monkeypatch.setattr(ingestion.requests, "post", timed_out)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("timestamp,marketingCloudVisitorID\n")
    bulk = make_bulk((10, 120))
    with pytest.raises(requests.exceptions.ReadTimeout):
        bulk.sendFiles("data.csv")
    assert not (tmp_path / "tmp").exists()
    assert bulk._createdFiles == []
