"""Offline tests for the OAuth token request (no network, no credentials needed)."""
import os
import sys
import inspect

import pytest

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from aanalytics2 import connector

CONFIG = {
    "org_id": "test-org",
    "client_id": "test-client",
    "secret": "test-secret",
    "scopes": "test-scopes",
    "oauthTokenEndpointV2": "https://ims.example/ims/token/v3",
    "token": "",
    "date_limit": 0,
}

ERROR_BODY = {"error": "invalid_client", "error_description": "invalid client_secret parameter"}


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


def fake_post(body):
    def post(url, data=None, proxies=None, **kwargs):
        return FakeResponse(body)
    return post


def test_token_error_raises_a_clear_error(monkeypatch):
    monkeypatch.setattr(connector.requests, "post", fake_post(ERROR_BODY))
    with pytest.raises(Exception, match="invalid_client: invalid client_secret parameter"):
        connector.get_oauth_token_and_expiry_for_config(dict(CONFIG))


def test_connector_raises_the_token_error_instead_of_a_TypeError(monkeypatch):
    monkeypatch.setattr(connector.requests, "post", fake_post(ERROR_BODY))
    with pytest.raises(Exception, match="invalid_client") as excinfo:
        connector.AdobeRequest(config_object=dict(CONFIG), header={})
    assert not isinstance(excinfo.value, TypeError)


def test_token_response_returns_the_token_and_expiry(monkeypatch):
    monkeypatch.setattr(
        connector.requests, "post",
        fake_post({"access_token": "abc", "token_type": "bearer", "expires_in": 86399}),
    )
    assert connector.get_oauth_token_and_expiry_for_config(dict(CONFIG)) == {"token": "abc", "expiry": 86399}
