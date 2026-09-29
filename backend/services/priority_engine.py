"""Rule-based Priority Engine.

Calculates complaint priority using configurable rules, keyword matching,
category weights, and signal precedence. Does NOT use machine learning.

Priority levels: critical, high, medium, low

The engine considers:
- Predicted category and its weight
- Urgency phrases
- Fraud/security indicators
- Financial loss indicators
- Informational/non-urgent language
- Signal conflicts and precedence
"""

import json
import os
import re
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config/priority_rules.json"


class PriorityEngine:
    """Rule-based priority scoring engine."""

    def __init__(self, config_path=None):
        self.config = self._load_config(config_path or DEFAULT_CONFIG_PATH)
        self._validate_config()

    def _load_config(self, path: str) -> dict:
        """Load priority rules from JSON config file."""
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info("Priority rules loaded from %s", path)
                return config
            except (json.JSONDecodeError, IOError) as e:
                logger.error("Failed to load priority rules: %s. Using defaults.", e)

        return self._default_config()

    def _default_config(self) -> dict:
        """Return default priority configuration."""
        return {
            "critical_keywords": [
                "fraud", "fraudulent", "unauthorized", "unauthorised",
                "identity theft", "account takeover", "account hacked",
                "stolen money", "money stolen", "someone accessed my account",
                "security breach",
            ],
            "high_keywords": [
                "urgent", "immediately", "right now", "emergency", "critical",
                "i don't recognize this transaction", "i do not recognize this transaction",
                "overcharged", "double charged", "foreclosure", "threatening",
            ],
            "medium_keywords": [
                "dispute", "incorrect", "error", "mistake",
                "late fee", "penalty", "billing issue", "refund",
            ],
            "low_keywords": [
                "how do i", "how can i", "can you tell me",
                "what is", "information about", "general question",
                "just wondering", "no rush", "not urgent",
            ],
            "category_weights": {},
            "fraud_weight": 3.0,
            "urgency_weight": 2.0,
            "financial_loss_weight": 2.5,
            "informational_penalty": -1.5,
            "priority_thresholds": {
                "critical": 5.0,
                "high": 3.0,
                "medium": 1.0,
                "low": -999,
            },
            "confidence_threshold": 0.60,
            "financial_loss_phrases": [
                "lost money", "lost funds", "charged me", "took money",
                "missing funds", "missing money", "overdraft", "negative balance",
            ],
            "security_phrases": [
                "someone accessed", "someone logged in", "not my transaction",
                "didn't authorize", "did not authorize", "don't recognize",
                "do not recognize", "compromised", "hacked", "stolen",
            ],
        }

    def _validate_config(self):
        """Validate the priority configuration at startup."""
        required_keys = [
            "critical_keywords", "high_keywords", "medium_keywords", "low_keywords",
            "fraud_weight", "urgency_weight", "financial_loss_weight",
            "informational_penalty", "priority_thresholds",
        ]
        for key in required_keys:
            if key not in self.config:
                logger.warning("Missing priority config key: %s. Using default.", key)

        thresholds = self.config.get("priority_thresholds", {})
        if thresholds:
            if thresholds.get("critical", 0) <= thresholds.get("high", 0):
                logger.warning("Critical threshold should be higher than high threshold.")

    def calculate_priority(self, text: str, category: str = None,
                           subcategory: str = None, confidence: float = None) -> dict:
        """Calculate the priority for a complaint.

        Args:
            text: The complaint text
            category: Predicted category from the classifier
            subcategory: Predicted subcategory
            confidence: Classification confidence score

        Returns:
            dict with: priority, score, explanation, signals
        """
        text_lower = text.lower() if text else ""
        signals = []
        score = 0.0

        # 1. Check fraud/security signals (highest precedence)
        fraud_signals = self._check_phrases(text_lower, "critical_keywords")
        security_signals = self._check_phrases(
            text_lower,
            "security_phrases",
            fallback=self.config.get("security_phrases", [])
        )

        if fraud_signals or security_signals:
            fraud_weight = self.config.get("fraud_weight", 3.0)
            fraud_count = len(fraud_signals) + len(security_signals)
            # Scale by number of signals but cap the multiplier
            fraud_score = fraud_weight * min(fraud_count, 3)
            score += fraud_score
            for s in fraud_signals:
                signals.append({"type": "fraud", "keyword": s, "weight": fraud_weight})
            for s in security_signals:
                signals.append({"type": "security", "keyword": s, "weight": fraud_weight})

        # 2. Check urgency signals
        urgency_signals = self._check_phrases(text_lower, "high_keywords")
        if urgency_signals:
            urgency_weight = self.config.get("urgency_weight", 2.0)
            urgency_score = urgency_weight * min(len(urgency_signals), 3)
            score += urgency_score
            for s in urgency_signals:
                signals.append({"type": "urgency", "keyword": s, "weight": urgency_weight})

        # 3. Check financial loss signals
        financial_signals = self._check_phrases(
            text_lower,
            "financial_loss_phrases",
            fallback=self.config.get("financial_loss_phrases", [])
        )
        if financial_signals:
            fin_weight = self.config.get("financial_loss_weight", 2.5)
            fin_score = fin_weight * min(len(financial_signals), 2)
            score += fin_score
            for s in financial_signals:
                signals.append({"type": "financial_loss", "keyword": s, "weight": fin_weight})

        # 4. Check medium signals
        medium_signals = self._check_phrases(text_lower, "medium_keywords")
        if medium_signals and not fraud_signals and not security_signals:
            # Medium keywords only contribute if no higher signals
            medium_score = 1.5 * min(len(medium_signals), 2)
            score += medium_score
            for s in medium_signals:
                signals.append({"type": "medium_indicator", "keyword": s, "weight": 1.5})

        # 5. Check informational/low-priority signals
        info_signals = self._check_phrases(text_lower, "low_keywords")
        if info_signals:
            info_penalty = self.config.get("informational_penalty", -1.5)
            # IMPORTANT: If fraud/security signals are present, override informational penalty
            if fraud_signals or security_signals or financial_signals:
                # Security/fraud signals take precedence over informational language
                effective_penalty = 0
                signals.append({
                    "type": "info_overridden",
                    "keyword": info_signals[0],
                    "weight": 0,
                    "reason": "Informational language overridden by security/fraud signals"
                })
            else:
                effective_penalty = info_penalty * min(len(info_signals), 2)
                score += effective_penalty
                for s in info_signals:
                    signals.append({"type": "informational", "keyword": s, "weight": info_penalty})

        # 6. Apply category weight
        if category:
            cat_weights = self.config.get("category_weights", {})
            cat_weight = cat_weights.get(category, 0.3)
            score += cat_weight
            signals.append({"type": "category", "keyword": category, "weight": cat_weight})

        # 7. Determine priority level from score
        thresholds = self.config.get("priority_thresholds", {
            "critical": 5.0, "high": 3.0, "medium": 1.0, "low": -999
        })

        if score >= thresholds.get("critical", 5.0):
            priority = "critical"
        elif score >= thresholds.get("high", 3.0):
            priority = "high"
        elif score >= thresholds.get("medium", 1.0):
            priority = "medium"
        else:
            priority = "low"

        # 8. Generate explanation
        explanation = self._generate_explanation(priority, signals, category, subcategory)

        return {
            "priority": priority,
            "score": round(score, 2),
            "explanation": explanation,
            "signals": json.dumps(signals),
        }

    def _check_phrases(self, text_lower: str, config_key: str,
                       fallback: list = None) -> list:
        """Check for phrase matches in text against a keyword list.

        Uses word-boundary-aware matching to reduce false positives.
        """
        keywords = self.config.get(config_key, fallback or [])
        found = []
        for keyword in keywords:
            # Use word boundary for single words, substring for phrases
            if " " in keyword:
                if keyword in text_lower:
                    found.append(keyword)
            else:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, text_lower):
                    found.append(keyword)
        return found

    def _generate_explanation(self, priority: str, signals: list,
                              category: str = None, subcategory: str = None) -> str:
        """Generate a human-readable explanation of the priority decision."""
        if not signals:
            return f"Priority set to {priority.upper()} based on default scoring."

        parts = []

        # Collect signal types
        signal_types = set(s["type"] for s in signals)

        if "fraud" in signal_types or "security" in signal_types:
            fraud_keywords = [s["keyword"] for s in signals
                              if s["type"] in ("fraud", "security")]
            if len(fraud_keywords) == 1:
                parts.append(f"contains a security/fraud indicator (\"{fraud_keywords[0]}\")")
            else:
                parts.append(f"contains security/fraud indicators")

        if "urgency" in signal_types:
            urgency_keywords = [s["keyword"] for s in signals if s["type"] == "urgency"]
            parts.append(f"contains urgent language")

        if "financial_loss" in signal_types:
            parts.append("indicates potential financial loss")

        if "medium_indicator" in signal_types and priority in ("medium", "high"):
            parts.append("describes a specific issue requiring attention")

        if "informational" in signal_types and priority == "low":
            parts.append("appears to be an informational request")

        if "info_overridden" in signal_types:
            parts.append("informational language was overridden by security/fraud concerns")

        if category:
            parts.append(f"was classified under \"{category}\"")

        if not parts:
            return f"Priority set to {priority.upper()} based on scoring analysis."

        explanation = f"This complaint received {priority.upper()} priority because it "
        if len(parts) == 1:
            explanation += parts[0] + "."
        elif len(parts) == 2:
            explanation += parts[0] + " and " + parts[1] + "."
        else:
            explanation += ", ".join(parts[:-1]) + ", and " + parts[-1] + "."

        return explanation

    def reload_config(self, config_path: str = None):
        """Reload the priority rules configuration."""
        self.config = self._load_config(config_path or DEFAULT_CONFIG_PATH)
        self._validate_config()
        logger.info("Priority rules reloaded.")


# Singleton instance
_engine_instance = None


def get_priority_engine(config_path=None) -> PriorityEngine:
    """Get or create the singleton priority engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PriorityEngine(config_path)
    return _engine_instance


def reset_priority_engine():
    """Reset the singleton (useful for testing or config reloading)."""
    global _engine_instance
    _engine_instance = None
