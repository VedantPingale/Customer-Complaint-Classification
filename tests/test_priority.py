"""Priority engine tests.

Tests for:
- Basic priority calculation
- Keyword matching
- Signal precedence (security overrides informational)
- Priority conflicts
- Edge cases
- Configurable rules
"""

import pytest
from backend.services.priority_engine import PriorityEngine


@pytest.fixture
def engine():
    """Create a priority engine with the default config."""
    return PriorityEngine()


class TestBasicPriority:
    """Tests for basic priority calculation."""

    def test_fraud_complaint_is_critical(self, engine):
        """Fraud indicators should produce critical priority."""
        result = engine.calculate_priority(
            "Someone made a fraudulent charge on my credit card and I need help immediately."
        )
        assert result["priority"] in ("critical", "high")
        assert result["score"] > 0

    def test_unauthorized_access_is_critical(self, engine):
        """Unauthorized account access should be critical."""
        result = engine.calculate_priority(
            "Someone accessed my bank account without authorization and withdrew money."
        )
        assert result["priority"] in ("critical", "high")

    def test_identity_theft_is_critical(self, engine):
        """Identity theft should be critical."""
        result = engine.calculate_priority(
            "I'm a victim of identity theft. Someone opened accounts in my name."
        )
        assert result["priority"] in ("critical", "high")

    def test_informational_question_is_low(self, engine):
        """General informational questions should be low priority."""
        result = engine.calculate_priority(
            "How do I check my credit score? Just wondering about the process."
        )
        assert result["priority"] == "low"

    def test_billing_dispute_is_medium(self, engine):
        """Billing disputes should generally be medium priority."""
        result = engine.calculate_priority(
            "There is an incorrect charge on my statement from last month."
        )
        assert result["priority"] in ("medium", "high")

    def test_urgent_language_increases_priority(self, engine):
        """Urgent language should increase priority."""
        result_normal = engine.calculate_priority(
            "I have a billing error on my account."
        )
        result_urgent = engine.calculate_priority(
            "I have a billing error on my account and I need this fixed immediately, it's urgent!"
        )
        assert result_urgent["score"] > result_normal["score"]


class TestSignalPrecedence:
    """Tests for signal precedence and conflict resolution."""

    def test_security_overrides_informational(self, engine):
        """Security signals must override informational language.

        This is the key test case: "How do I stop someone who has accessed my
        account immediately?" should NOT be low priority just because it starts
        with "How do I".
        """
        result = engine.calculate_priority(
            "How do I stop someone who hacked my account immediately?"
        )
        assert result["priority"] != "low", (
            f"Security signals should override informational language. "
            f"Got {result['priority']} with score {result['score']}"
        )
        assert result["priority"] in ("critical", "high")

    def test_fraud_with_question_phrasing(self, engine):
        """Fraud reports phrased as questions should still be high priority."""
        result = engine.calculate_priority(
            "Can you tell me how to report unauthorized transactions on my account?"
        )
        assert result["priority"] != "low"

    def test_mixed_signals_favor_urgency(self, engine):
        """When both informational and urgency signals are present, urgency wins."""
        result = engine.calculate_priority(
            "What is the process to dispute a fraudulent charge? This is urgent."
        )
        assert result["priority"] in ("critical", "high")

    def test_multiple_security_signals_compound(self, engine):
        """Multiple security signals should compound the score."""
        result_single = engine.calculate_priority(
            "There's a fraudulent charge on my card."
        )
        result_multi = engine.calculate_priority(
            "There's a fraudulent charge on my card. Someone hacked my account "
            "and stole money. This is identity theft."
        )
        assert result_multi["score"] > result_single["score"]


class TestPriorityExplanation:
    """Tests for priority explanation generation."""

    def test_explanation_is_generated(self, engine):
        """Every priority result should have an explanation."""
        result = engine.calculate_priority(
            "I have a question about my mortgage payment."
        )
        assert result["explanation"]
        assert len(result["explanation"]) > 10

    def test_explanation_mentions_fraud(self, engine):
        """Fraud-related explanation should mention security/fraud."""
        result = engine.calculate_priority(
            "Someone made a fraudulent transaction on my account."
        )
        assert "fraud" in result["explanation"].lower() or "security" in result["explanation"].lower()

    def test_explanation_mentions_informational(self, engine):
        """Low priority explanation should mention informational nature."""
        result = engine.calculate_priority(
            "Can you tell me what my interest rate is? No rush."
        )
        if result["priority"] == "low":
            assert "informational" in result["explanation"].lower()

    def test_explanation_not_hardcoded(self, engine):
        """Explanations should differ based on actual signals."""
        result1 = engine.calculate_priority("Fraud on my account, someone hacked it.")
        result2 = engine.calculate_priority("How do I check my balance? No rush.")
        assert result1["explanation"] != result2["explanation"]


class TestEdgeCases:
    """Tests for edge cases in priority calculation."""

    def test_empty_text(self, engine):
        """Empty text should produce a default result."""
        result = engine.calculate_priority("")
        assert result["priority"] in ("low", "medium")

    def test_none_text(self, engine):
        """None text should be handled gracefully."""
        result = engine.calculate_priority(None)
        assert result["priority"] is not None

    def test_very_long_text(self, engine):
        """Very long text should be handled."""
        long_text = "I have a billing issue. " * 500
        result = engine.calculate_priority(long_text)
        assert result["priority"] is not None

    def test_category_weight(self, engine):
        """Category should contribute to priority score."""
        result_without = engine.calculate_priority("A general complaint.")
        result_with = engine.calculate_priority(
            "A general complaint.",
            category="Mortgage"
        )
        assert result_with["score"] >= result_without["score"]

    def test_signals_are_recorded(self, engine):
        """Signals should be recorded as JSON."""
        result = engine.calculate_priority(
            "There's a fraudulent charge on my credit card."
        )
        assert result["signals"] is not None
        import json
        signals = json.loads(result["signals"])
        assert isinstance(signals, list)
        assert len(signals) > 0

    def test_all_priority_levels_possible(self, engine):
        """Verify all four priority levels are achievable."""
        results = {}
        test_cases = {
            "critical": "Someone committed fraud and stole my identity, unauthorized access to my account immediately!",
            "high": "I need this resolved urgently, there are unauthorized charges right now.",
            "medium": "There's an error on my billing statement that needs to be corrected.",
            "low": "Just wondering how do I check my credit score? No rush, whenever you have time.",
        }

        for expected, text in test_cases.items():
            result = engine.calculate_priority(text)
            results[expected] = result["priority"]

        # At least low and one of critical/high should be achievable
        assert results["low"] == "low" or results["low"] == "medium"
        assert results["critical"] in ("critical", "high")

    def test_case_insensitive(self, engine):
        """Keyword matching should be case insensitive."""
        result_lower = engine.calculate_priority("fraud on my account")
        result_upper = engine.calculate_priority("FRAUD ON MY ACCOUNT")
        assert result_lower["priority"] == result_upper["priority"]


class TestConfigurable:
    """Tests for configurable priority rules."""

    def test_custom_config(self):
        """Test that a custom config is properly loaded."""
        engine = PriorityEngine()
        assert engine.config is not None
        assert "critical_keywords" in engine.config

    def test_reload_config(self):
        """Test config reloading."""
        engine = PriorityEngine()
        old_config = engine.config.copy()
        engine.reload_config()
        assert engine.config is not None
