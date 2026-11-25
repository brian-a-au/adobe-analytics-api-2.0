"""Offline tests for the interactive company picker in the CLI (no network, no credentials needed)."""
import os
import sys
import inspect

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from aanalytics2.cli.__main__ import AnalyticsShell


class FailingLogin:
    def getCompanyId(self):
        raise ValueError("getCompanyId did not return the list of IMS orgs. The API returned: 403003: Api Key is invalid")


def test_pick_company_id_shows_the_getCompanyId_error(capsys):
    shell = AnalyticsShell.__new__(AnalyticsShell)
    shell.login_obj = FailingLogin()
    assert shell._pick_company_id() is None
    assert "403003: Api Key is invalid" in capsys.readouterr().out
