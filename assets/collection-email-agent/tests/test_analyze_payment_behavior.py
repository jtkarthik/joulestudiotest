"""Unit tests for analyze_payment_behavior — pure Python, no mocking needed."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from tools.analysis import analyze_payment_behavior, _classify, _parse


class TestAnalyzePaymentBehavior:
    def _open_items(self, items: list) -> str:
        return json.dumps({"value": items})

    def _history(self, payments: list) -> str:
        return json.dumps({"value": payments})

    def _dunning(self, level: int = 0) -> str:
        return json.dumps({"DunningLevel": level, "BlockedForDunning": False})

    def test_returns_expected_keys(self):
        result = analyze_payment_behavior(
            self._open_items([]),
            self._history([]),
            self._dunning(0),
        )
        expected_keys = {
            "total_open_amount", "currency", "overdue_count", "max_days_overdue",
            "avg_days_late_historical", "on_time_payment_rate", "dunning_level",
            "risk_tier", "recommended_tone", "summary",
        }
        assert expected_keys == set(result.keys())

    def test_totals_open_items_correctly(self):
        items = [
            {"InvoiceID": "I1", "Amount": "1000", "Currency": "USD", "DaysOverdue": "10"},
            {"InvoiceID": "I2", "Amount": "2500.50", "Currency": "USD", "DaysOverdue": "0"},
        ]
        result = analyze_payment_behavior(
            self._open_items(items),
            self._history([]),
            self._dunning(0),
        )
        assert result["total_open_amount"] == pytest.approx(3500.50, rel=1e-4)
        assert result["overdue_count"] == 1
        assert result["currency"] == "USD"

    def test_max_days_overdue(self):
        items = [
            {"Amount": "100", "Currency": "EUR", "DaysOverdue": "5"},
            {"Amount": "200", "Currency": "EUR", "DaysOverdue": "120"},
            {"Amount": "300", "Currency": "EUR", "DaysOverdue": "0"},
        ]
        result = analyze_payment_behavior(
            self._open_items(items), self._history([]), self._dunning(0)
        )
        assert result["max_days_overdue"] == 120

    def test_on_time_rate_all_on_time(self):
        payments = [
            {"DaysLate": "0"}, {"DaysLate": "-2"}, {"DaysLate": "0"},
        ]
        result = analyze_payment_behavior(
            self._open_items([]), self._history(payments), self._dunning(0)
        )
        assert result["on_time_payment_rate"] == pytest.approx(1.0)

    def test_on_time_rate_mixed(self):
        payments = [
            {"DaysLate": "0"}, {"DaysLate": "5"}, {"DaysLate": "0"}, {"DaysLate": "20"},
        ]
        result = analyze_payment_behavior(
            self._open_items([]), self._history(payments), self._dunning(0)
        )
        assert result["on_time_payment_rate"] == pytest.approx(0.5)

    def test_empty_history_defaults(self):
        result = analyze_payment_behavior(
            self._open_items([]), self._history([]), self._dunning(0)
        )
        assert result["on_time_payment_rate"] == 1.0
        assert result["avg_days_late_historical"] == 0.0

    def test_low_risk_friendly_tone(self):
        result = analyze_payment_behavior(
            self._open_items([{"Amount": "100", "Currency": "USD", "DaysOverdue": "5"}]),
            self._history([{"DaysLate": "0"}]),
            self._dunning(0),
        )
        assert result["risk_tier"] == "low"
        assert result["recommended_tone"] == "friendly"

    def test_medium_risk_firm_tone(self):
        items = [{"Amount": "500", "Currency": "USD", "DaysOverdue": "35"}]
        result = analyze_payment_behavior(
            self._open_items(items), self._history([{"DaysLate": "0"}]), self._dunning(1)
        )
        assert result["risk_tier"] == "medium"
        assert result["recommended_tone"] == "firm"

    def test_high_risk_urgent_tone(self):
        items = [{"Amount": "5000", "Currency": "USD", "DaysOverdue": "65"}]
        result = analyze_payment_behavior(
            self._open_items(items), self._history([{"DaysLate": "30"}]), self._dunning(2)
        )
        assert result["risk_tier"] == "high"
        assert result["recommended_tone"] == "urgent"

    def test_critical_risk_legal_tone_by_dunning(self):
        result = analyze_payment_behavior(
            self._open_items([{"Amount": "1000", "Currency": "USD", "DaysOverdue": "10"}]),
            self._history([{"DaysLate": "0"}]),
            self._dunning(3),
        )
        assert result["risk_tier"] == "critical"
        assert result["recommended_tone"] == "legal"

    def test_critical_risk_legal_tone_by_days(self):
        items = [{"Amount": "1000", "Currency": "USD", "DaysOverdue": "95"}]
        result = analyze_payment_behavior(
            self._open_items(items), self._history([{"DaysLate": "0"}]), self._dunning(0)
        )
        assert result["risk_tier"] == "critical"
        assert result["recommended_tone"] == "legal"

    def test_summary_contains_key_figures(self):
        items = [{"Amount": "1234.56", "Currency": "EUR", "DaysOverdue": "10"}]
        result = analyze_payment_behavior(
            self._open_items(items), self._history([]), self._dunning(0)
        )
        assert "EUR" in result["summary"]
        assert "1" in result["summary"]  # overdue_count

    def test_accepts_list_directly_for_open_items(self):
        items = [{"Amount": "500", "Currency": "GBP", "DaysOverdue": "20"}]
        result = analyze_payment_behavior(
            json.dumps(items), self._history([]), self._dunning(0)
        )
        assert result["total_open_amount"] == pytest.approx(500.0)

    def test_accepts_list_directly_for_history(self):
        payments = [{"DaysLate": "3"}]
        result = analyze_payment_behavior(
            self._open_items([]), json.dumps(payments), self._dunning(0)
        )
        assert result["avg_days_late_historical"] == pytest.approx(3.0)

    def test_dunning_level_captured(self):
        result = analyze_payment_behavior(
            self._open_items([]), self._history([]), self._dunning(2)
        )
        assert result["dunning_level"] == 2


class TestClassify:
    def test_low(self):
        assert _classify(0, 5, 2.0, 0.9, 0) == ("low", "friendly")

    def test_medium_by_dunning(self):
        tier, tone = _classify(1, 10, 5.0, 0.8, 1)
        assert tier == "medium"
        assert tone == "firm"

    def test_medium_by_days(self):
        tier, tone = _classify(1, 35, 5.0, 0.8, 0)
        assert tier == "medium"
        assert tone == "firm"

    def test_high_by_on_time_rate(self):
        tier, tone = _classify(1, 10, 5.0, 0.4, 0)
        assert tier == "high"
        assert tone == "urgent"

    def test_critical_by_dunning(self):
        tier, tone = _classify(1, 10, 5.0, 0.9, 4)
        assert tier == "critical"
        assert tone == "legal"

    def test_critical_by_days(self):
        tier, tone = _classify(1, 91, 5.0, 0.9, 0)
        assert tier == "critical"
        assert tone == "legal"


class TestParse:
    def test_dict_passthrough(self):
        d = {"key": "value"}
        assert _parse(d) is d

    def test_list_passthrough(self):
        lst = [1, 2, 3]
        assert _parse(lst) is lst

    def test_json_string(self):
        assert _parse('{"a": 1}') == {"a": 1}

    def test_invalid_json_returns_empty_dict(self):
        assert _parse("not json") == {}

    def test_none_returns_empty_dict(self):
        assert _parse(None) == {}
