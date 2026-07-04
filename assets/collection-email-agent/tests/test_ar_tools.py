"""Tests for AR MCP-backed tools — all MCP calls are mocked."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure app is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

# Import mcp_tools now so we can monkeypatch it
import mcp_tools  # noqa: E402


def _make_mock_tool(name: str, return_value: dict) -> MagicMock:
    t = MagicMock()
    t.name = name
    t.run = MagicMock(return_value=json.dumps(return_value))
    return t


OPEN_ITEMS_PAYLOAD = {
    "value": [
        {"InvoiceID": "INV-001", "Amount": 1000.0, "Currency": "USD", "DueDate": "2024-11-01", "DaysOverdue": 30},
        {"InvoiceID": "INV-002", "Amount": 2500.0, "Currency": "USD", "DueDate": "2024-10-15", "DaysOverdue": 45},
    ]
}

PAYMENT_HISTORY_PAYLOAD = {
    "value": [
        {"InvoiceID": "INV-OLD-001", "PaidAmount": 500.0, "Currency": "USD", "PaymentDate": "2024-09-01", "DaysLate": 0},
        {"InvoiceID": "INV-OLD-002", "PaidAmount": 800.0, "Currency": "USD", "PaymentDate": "2024-08-01", "DaysLate": 5},
    ]
}

DUNNING_PAYLOAD = {
    "DunningLevel": 1,
    "LastDunningDate": "2024-11-01",
    "NextDunningDate": "2024-12-01",
    "BlockedForDunning": False,
}


# ---- helpers that call the underlying function directly (no @tool coroutine wrapping) ----

def _open_items(customer_id: str, company_code: str = "") -> dict:
    from tools.ar_tools import get_customer_open_items
    raw = get_customer_open_items.func(customer_id, company_code)
    return json.loads(raw)


def _payment_history(customer_id: str, months: int = 12) -> dict:
    from tools.ar_tools import get_payment_history
    raw = get_payment_history.func(customer_id, months)
    return json.loads(raw)


def _dunning(customer_id: str, company_code: str = "") -> dict:
    from tools.ar_tools import get_dunning_status
    raw = get_dunning_status.func(customer_id, company_code)
    return json.loads(raw)


class TestGetCustomerOpenItems:

    def test_returns_expected_invoices(self, monkeypatch):
        mock_tool = _make_mock_tool("get_customer_open_items", OPEN_ITEMS_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        result = _open_items("CUST001")
        assert "value" in result
        assert len(result["value"]) == 2

    def test_passes_customer_id_to_mcp(self, monkeypatch):
        mock_tool = _make_mock_tool("get_customer_open_items", OPEN_ITEMS_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        _open_items("CUST123")
        call_args = json.loads(mock_tool.run.call_args[0][0])
        assert call_args["CustomerID"] == "CUST123"

    def test_passes_company_code_when_provided(self, monkeypatch):
        mock_tool = _make_mock_tool("get_customer_open_items", OPEN_ITEMS_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        _open_items("CUST001", company_code="1000")
        call_args = json.loads(mock_tool.run.call_args[0][0])
        assert call_args["CompanyCode"] == "1000"

    def test_includes_top_100(self, monkeypatch):
        mock_tool = _make_mock_tool("get_customer_open_items", OPEN_ITEMS_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        _open_items("CUST001")
        call_args = json.loads(mock_tool.run.call_args[0][0])
        assert call_args["top"] == 100

    def test_omits_company_code_when_empty(self, monkeypatch):
        mock_tool = _make_mock_tool("get_customer_open_items", OPEN_ITEMS_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        _open_items("CUST001")
        call_args = json.loads(mock_tool.run.call_args[0][0])
        assert "CompanyCode" not in call_args

    def test_returns_error_json_on_exception(self, monkeypatch):
        bad_tool = MagicMock()
        bad_tool.name = "get_customer_open_items"
        bad_tool.run = MagicMock(side_effect=RuntimeError("MCP timeout"))
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [bad_tool])
        result = _open_items("CUST001")
        assert "error" in result
        assert result["customer_id"] == "CUST001"

    def test_tool_not_found_returns_error(self, monkeypatch):
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [])
        result = _open_items("X")
        assert "error" in result


class TestGetPaymentHistory:

    def test_returns_payment_records(self, monkeypatch):
        mock_tool = _make_mock_tool("get_payment_history", PAYMENT_HISTORY_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        result = _payment_history("CUST001")
        assert "value" in result

    def test_passes_months_param(self, monkeypatch):
        mock_tool = _make_mock_tool("get_payment_history", PAYMENT_HISTORY_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        _payment_history("CUST001", months=6)
        call_args = json.loads(mock_tool.run.call_args[0][0])
        assert call_args["Months"] == 6

    def test_default_months_is_12(self, monkeypatch):
        mock_tool = _make_mock_tool("get_payment_history", PAYMENT_HISTORY_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        _payment_history("CUST001")
        call_args = json.loads(mock_tool.run.call_args[0][0])
        assert call_args["Months"] == 12

    def test_passes_customer_id(self, monkeypatch):
        mock_tool = _make_mock_tool("get_payment_history", PAYMENT_HISTORY_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        _payment_history("CUST999")
        call_args = json.loads(mock_tool.run.call_args[0][0])
        assert call_args["CustomerID"] == "CUST999"

    def test_error_returns_error_json(self, monkeypatch):
        bad_tool = MagicMock()
        bad_tool.name = "get_payment_history"
        bad_tool.run = MagicMock(side_effect=ConnectionError("SAP unreachable"))
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [bad_tool])
        result = _payment_history("C1")
        assert "error" in result


class TestGetDunningStatus:

    def test_returns_dunning_level(self, monkeypatch):
        mock_tool = _make_mock_tool("get_dunning_status", DUNNING_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        result = _dunning("CUST001")
        assert "DunningLevel" in result
        assert result["DunningLevel"] == 1

    def test_passes_company_code(self, monkeypatch):
        mock_tool = _make_mock_tool("get_dunning_status", DUNNING_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        _dunning("CUST001", company_code="2000")
        call_args = json.loads(mock_tool.run.call_args[0][0])
        assert call_args["CompanyCode"] == "2000"

    def test_no_company_code_omits_field(self, monkeypatch):
        mock_tool = _make_mock_tool("get_dunning_status", DUNNING_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        _dunning("CUST001")
        call_args = json.loads(mock_tool.run.call_args[0][0])
        assert "CompanyCode" not in call_args

    def test_passes_customer_id(self, monkeypatch):
        mock_tool = _make_mock_tool("get_dunning_status", DUNNING_PAYLOAD)
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [mock_tool])
        _dunning("CUST555")
        call_args = json.loads(mock_tool.run.call_args[0][0])
        assert call_args["CustomerID"] == "CUST555"

    def test_error_returns_error_json(self, monkeypatch):
        bad_tool = MagicMock()
        bad_tool.name = "get_dunning_status"
        bad_tool.run = MagicMock(side_effect=ValueError("not found"))
        monkeypatch.setattr(mcp_tools, "get_mcp_tools", lambda: [bad_tool])
        result = _dunning("C2")
        assert "error" in result
