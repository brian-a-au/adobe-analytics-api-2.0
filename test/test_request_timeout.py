"""Offline tests for request timeouts (no network, no credentials needed)."""
import os
import sys
import time
import inspect

import requests
from requests.adapters import HTTPAdapter

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from aanalytics2 import config as config_module
from aanalytics2 import configs, connector


def make_config(**extra) -> dict:
    """A config with a valid token, so AdobeRequest does not request a new one."""
    return {
        "org_id": "test-org",
        "client_id": "test-client",
        "secret": "test-secret",
        "scopes": "test-scopes",
        "oauthTokenEndpointV2": "https://ims.example/ims/token/v3",
        "token": "test-token",
        "date_limit": time.time() + 3600,
        "proxy": None,
        **extra,
    }


def capture_adapter_timeouts(monkeypatch) -> list:
    """Replaces the network call in HTTPAdapter and records the timeout of each request."""
    seen = []

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        seen.append(timeout)
        response = requests.Response()
        response.status_code = 200
        response._content = b"{}"
        response.request = request
        response.url = request.url
        return response

    monkeypatch.setattr(HTTPAdapter, "send", send)
    return seen


def test_session_requests_use_the_default_timeout(monkeypatch):
    seen = capture_adapter_timeouts(monkeypatch)
    conn = connector.AdobeRequest(config_object=make_config(), header={})
    conn.getData("https://analytics.example/api/comp1/segments")
    assert seen == [connector.DEFAULT_TIMEOUT]


def test_config_timeout_replaces_the_default(monkeypatch):
    seen = capture_adapter_timeouts(monkeypatch)
    conn = connector.AdobeRequest(config_object=make_config(timeout=30), header={})
    conn.getData("https://analytics.example/api/comp1/segments")
    assert seen == [30]


def test_config_timeout_from_a_json_list_becomes_a_tuple(monkeypatch):
    seen = capture_adapter_timeouts(monkeypatch)
    conn = connector.AdobeRequest(config_object=make_config(timeout=[5, 60]), header={})
    conn.getData("https://analytics.example/api/comp1/segments")
    assert seen == [(5, 60)]


def test_a_timeout_passed_to_the_session_call_is_kept(monkeypatch):
    seen = capture_adapter_timeouts(monkeypatch)
    conn = connector.AdobeRequest(config_object=make_config(), header={})
    conn.session.get("https://analytics.example/api/comp1/segments", timeout=7)
    assert seen == [7]


def test_token_request_uses_the_timeout(monkeypatch):
    seen = {}

    class FakeResponse:
        def json(self):
            return {"access_token": "abc", "expires_in": 86399}

    def post(url, data=None, proxies=None, timeout=None, **kwargs):
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(connector.requests, "post", post)
    connector.get_oauth_token_and_expiry_for_config(make_config(timeout=20))
    assert seen["timeout"] == 20


def test_configure_stores_the_timeout(monkeypatch):
    monkeypatch.setattr(configs, "config_object", dict(config_module.config_object))
    monkeypatch.setattr(configs, "header", dict(config_module.header))
    configs.configure(org_id="o", client_id="c", secret="s", scopes="openid", timeout=45)
    assert configs.config_object["timeout"] == 45


def test_configure_return_object_keeps_the_timeout():
    bundle = configs.configure(org_id="o", client_id="c", secret="s", scopes="openid",
                               timeout=45, return_object=True)
    assert bundle.config["timeout"] == 45
    assert bundle.to_dict()["timeout"] == 45


def test_importConfigFile_reads_the_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr(configs, "config_object", dict(config_module.config_object))
    monkeypatch.setattr(configs, "header", dict(config_module.header))
    path = tmp_path / "config.json"
    path.write_text('{"org_id": "o", "client_id": "c", "secret": "s", "scopes": "openid", "timeout": [5, 60]}')
    configs.importConfigFile(str(path))
    assert configs.config_object["timeout"] == [5, 60]
