"""Accounts Receivable tools — all SAP calls go through MCP servers."""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _call_mcp(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Synchronous wrapper: find the named tool in the MCP catalogue and call it."""
    import mcp_tools  # late import so tests can patch before first call

    tools = mcp_tools.get_mcp_tools()
    for t in tools:
        if t.name == tool_name:
            result = t.run(json.dumps(params))
            if isinstance(result, str):
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return {"raw": result}
            return result if isinstance(result, dict) else {"raw": result}
    raise ValueError(f"MCP tool '{tool_name}' not found in catalogue")


@tool
def get_customer_open_items(customer_id: str, company_code: str = "") -> str:
    """Retrieve open (unpaid) invoice items for a customer from SAP S/4HANA.

    Args:
        customer_id: SAP customer / business-partner number (e.g. '1000123')
        company_code: Optional SAP company code filter (e.g. '1000')

    Returns:
        JSON string with a list of open items, each containing InvoiceID,
        Amount, Currency, DueDate, DaysOverdue.
    """
    params: dict[str, Any] = {"top": 100, "CustomerID": customer_id}
    if company_code:
        params["CompanyCode"] = company_code
    try:
        result = _call_mcp("get_customer_open_items", params)
        return json.dumps(result)
    except Exception as exc:
        logger.exception("get_customer_open_items failed for %s", customer_id)
        return json.dumps({"error": str(exc), "customer_id": customer_id})


@tool
def get_payment_history(customer_id: str, months: int = 12) -> str:
    """Retrieve recent payment history for a customer from SAP S/4HANA.

    Args:
        customer_id: SAP customer / business-partner number
        months: How many months of history to retrieve (default 12)

    Returns:
        JSON string with a list of payment records, each containing InvoiceID,
        PaidAmount, Currency, PaymentDate, DaysLate.
    """
    params: dict[str, Any] = {"top": 100, "CustomerID": customer_id, "Months": months}
    try:
        result = _call_mcp("get_payment_history", params)
        return json.dumps(result)
    except Exception as exc:
        logger.exception("get_payment_history failed for %s", customer_id)
        return json.dumps({"error": str(exc), "customer_id": customer_id})


@tool
def get_dunning_status(customer_id: str, company_code: str = "") -> str:
    """Retrieve current dunning (collections escalation) status for a customer.

    Args:
        customer_id: SAP customer / business-partner number
        company_code: Optional SAP company code filter

    Returns:
        JSON string with DunningLevel (0–4), LastDunningDate, NextDunningDate,
        BlockedForDunning flag.
    """
    params: dict[str, Any] = {"CustomerID": customer_id}
    if company_code:
        params["CompanyCode"] = company_code
    try:
        result = _call_mcp("get_dunning_status", params)
        return json.dumps(result)
    except Exception as exc:
        logger.exception("get_dunning_status failed for %s", customer_id)
        return json.dumps({"error": str(exc), "customer_id": customer_id})
