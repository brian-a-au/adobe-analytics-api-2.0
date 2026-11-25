"""Offline tests for Login.getCompanyId (no network, no credentials needed)."""
import os
import sys
import inspect

import pytest

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from aanalytics2.aanalytics2 import Login

OTHER_ORG = {"imsOrgId": "OTHER@AdobeOrg", "companies": [{"globalCompanyId": "other0"}]}
MY_ORG = {"imsOrgId": "MINE@AdobeOrg", "companies": [{"globalCompanyId": "mine0"}, {"globalCompanyId": "mine1"}]}


class FakeConnector:
    def __init__(self, response, org_id="MINE@AdobeOrg"):
        self.response = response
        self.config = {"org_id": org_id}

    def getData(self, url, params=None, headers=None, **kwargs):
        return self.response


def make_login(response, org_id="MINE@AdobeOrg") -> Login:
    """Builds a Login instance without running __init__ (which would need a real token)."""
    login = Login.__new__(Login)
    login.header = {}
    login.COMPANY_IDS = {}
    login.connector = FakeConnector(response, org_id)
    return login


def test_returns_the_companies_of_the_configured_org():
    login = make_login({"imsOrgs": [OTHER_ORG, MY_ORG]})
    companies = login.getCompanyId()
    assert [c["globalCompanyId"] for c in companies] == ["mine0", "mine1"]
    assert login.COMPANY_IDS == companies


def test_falls_back_to_the_first_org_when_none_matches():
    login = make_login({"imsOrgs": [OTHER_ORG]})
    assert [c["globalCompanyId"] for c in login.getCompanyId()] == ["other0"]


def test_error_body_raises_a_clear_error():
    body = {"error_code": "403003", "message": "Api Key is invalid"}
    with pytest.raises(ValueError, match="getCompanyId.*403003: Api Key is invalid"):
        make_login(body).getCompanyId()


def test_connector_error_body_raises_a_clear_error():
    with pytest.raises(ValueError, match="getCompanyId.*Request Error"):
        make_login({"error": "Request Error"}).getCompanyId()


def test_no_ims_org_raises_a_clear_error():
    with pytest.raises(ValueError, match="getCompanyId.*no IMS org"):
        make_login({"imsOrgs": []}).getCompanyId()


def test_an_org_without_companies_returns_an_empty_list():
    login = make_login({"imsOrgs": [{"imsOrgId": "MINE@AdobeOrg", "companies": []}]})
    assert login.getCompanyId() == []
