"""Pure-Python payment behaviour analysis — no LLM, no I/O, fully testable."""
from __future__ import annotations

import json
from typing import Any


def analyze_payment_behavior(
    open_items_json: str,
    payment_history_json: str,
    dunning_status_json: str,
) -> dict[str, Any]:
    """Analyse SAP AR data and return a structured behaviour summary.

    Args:
        open_items_json: JSON string returned by get_customer_open_items
        payment_history_json: JSON string returned by get_payment_history
        dunning_status_json: JSON string returned by get_dunning_status

    Returns:
        dict with keys:
          - total_open_amount: float
          - currency: str (most common currency of open items)
          - overdue_count: int
          - max_days_overdue: int
          - avg_days_late_historical: float
          - on_time_payment_rate: float  (0.0–1.0)
          - dunning_level: int (0–4)
          - risk_tier: str ('low' | 'medium' | 'high' | 'critical')
          - recommended_tone: str ('friendly' | 'firm' | 'urgent' | 'legal')
          - summary: str  (one-sentence narrative)
    """
    open_items = _parse(open_items_json)
    history = _parse(payment_history_json)
    dunning = _parse(dunning_status_json)

    # --- open items ---
    items = open_items if isinstance(open_items, list) else open_items.get("value", [])
    total_open = sum(float(i.get("Amount", 0)) for i in items)
    overdue = [i for i in items if int(i.get("DaysOverdue", 0)) > 0]
    overdue_count = len(overdue)
    max_days_overdue = max((int(i.get("DaysOverdue", 0)) for i in overdue), default=0)
    currencies = [i.get("Currency", "USD") for i in items]
    currency = max(set(currencies), key=currencies.count) if currencies else "USD"

    # --- payment history ---
    payments = history if isinstance(history, list) else history.get("value", [])
    days_late_list = [int(p.get("DaysLate", 0)) for p in payments]
    avg_days_late = sum(days_late_list) / len(days_late_list) if days_late_list else 0.0
    on_time = sum(1 for d in days_late_list if d <= 0)
    on_time_rate = on_time / len(days_late_list) if days_late_list else 1.0

    # --- dunning ---
    dunning_level = int(dunning.get("DunningLevel", 0)) if isinstance(dunning, dict) else 0

    # --- risk tier ---
    risk_tier, recommended_tone = _classify(
        overdue_count, max_days_overdue, avg_days_late, on_time_rate, dunning_level
    )

    summary = (
        f"Customer has {overdue_count} overdue item(s) totalling "
        f"{currency} {total_open:,.2f}; max {max_days_overdue} days overdue; "
        f"dunning level {dunning_level}; historical on-time rate "
        f"{on_time_rate * 100:.0f}%."
    )

    return {
        "total_open_amount": round(total_open, 2),
        "currency": currency,
        "overdue_count": overdue_count,
        "max_days_overdue": max_days_overdue,
        "avg_days_late_historical": round(avg_days_late, 1),
        "on_time_payment_rate": round(on_time_rate, 4),
        "dunning_level": dunning_level,
        "risk_tier": risk_tier,
        "recommended_tone": recommended_tone,
        "summary": summary,
    }


def _parse(raw: str | dict | list) -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _classify(
    overdue_count: int,
    max_days_overdue: int,
    avg_days_late: float,
    on_time_rate: float,
    dunning_level: int,
) -> tuple[str, str]:
    """Return (risk_tier, recommended_tone)."""
    if dunning_level >= 3 or max_days_overdue > 90:
        return "critical", "legal"
    if dunning_level == 2 or max_days_overdue > 60 or on_time_rate < 0.5:
        return "high", "urgent"
    if dunning_level == 1 or max_days_overdue > 30 or avg_days_late > 15:
        return "medium", "firm"
    return "low", "friendly"
