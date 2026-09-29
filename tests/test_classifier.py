"""Classifier tests.

Tests for:
- Text preprocessing
- Classification output format
- Keyword fallback classifier
- Confidence thresholds
- Model loading/inference
"""

import pytest
from backend.services.classifier import ComplaintClassifier


@pytest.fixture
def classifier():
    """Create a classifier instance (uses keyword fallback since no model is trained)."""
    return ComplaintClassifier(categories_path="config/categories.json")


class TestPreprocessing:
    """Tests for text preprocessing."""

    def test_preprocess_basic(self, classifier):
        """Test basic text preprocessing."""
        result = classifier.preprocess_text("Hello, World! 123")
        assert result == "hello world"

    def test_preprocess_empty(self, classifier):
        """Test preprocessing empty text."""
        assert classifier.preprocess_text("") == ""
        assert classifier.preprocess_text(None) == ""

    def test_preprocess_special_chars(self, classifier):
        """Test preprocessing with special characters."""
        result = classifier.preprocess_text("Account #12345 was charged $500!")
        assert "$" not in result
        assert "#" not in result

    def test_preprocess_whitespace(self, classifier):
        """Test preprocessing normalizes whitespace."""
        result = classifier.preprocess_text("  too   much    space  ")
        assert "  " not in result.strip()


class TestClassification:
    """Tests for complaint classification."""

    def test_classify_returns_required_fields(self, classifier):
        """Classification result must contain category, subcategory, confidence."""
        result = classifier.classify(
            "I have an unauthorized charge on my credit card statement."
        )
        assert "category" in result
        assert "subcategory" in result
        assert "confidence" in result
        assert isinstance(result["confidence"], float)
        assert 0 <= result["confidence"] <= 1

    def test_classify_credit_card(self, classifier):
        """Credit card complaint should be classified to credit card category."""
        result = classifier.classify(
            "My credit card was charged $500 for a purchase I didn't make. "
            "I need this billing dispute resolved."
        )
        assert "credit" in result["category"].lower() or "card" in result["category"].lower()

    def test_classify_mortgage(self, classifier):
        """Mortgage complaint should be classified to mortgage category."""
        result = classifier.classify(
            "My mortgage company is threatening foreclosure even though I've been "
            "making payments. I need help with my home loan and escrow account."
        )
        assert "mortgage" in result["category"].lower()

    def test_classify_debt_collection(self, classifier):
        """Debt collection complaint should be classified correctly."""
        result = classifier.classify(
            "A debt collector keeps calling me about a debt I don't owe. "
            "They're harassing me with cease and desist violations."
        )
        assert "debt" in result["category"].lower()

    def test_classify_empty_text(self, classifier):
        """Empty text should return a default result."""
        result = classifier.classify("")
        assert result["confidence"] == 0.0

    def test_classify_none_text(self, classifier):
        """None text should return a default result."""
        result = classifier.classify(None)
        assert result["confidence"] == 0.0

    def test_fallback_confidence_is_low(self, classifier):
        """Keyword fallback classifier should have lower confidence."""
        result = classifier.classify(
            "This is a random text that doesn't clearly match any category."
        )
        # Fallback confidence should be below the threshold
        assert result["confidence"] <= 0.60

    def test_model_version_is_set(self, classifier):
        """Model version should be set in the result."""
        result = classifier.classify("Some complaint about my bank account.")
        assert "model_version" in result
        assert result["model_version"] is not None


class TestClassifierLoading:
    """Tests for model loading."""

    def test_not_loaded_without_model(self):
        """Classifier should not be 'loaded' without model files."""
        classifier = ComplaintClassifier()
        assert not classifier.is_loaded

    def test_fallback_when_not_loaded(self):
        """Classifier should use fallback when model is not loaded."""
        classifier = ComplaintClassifier(categories_path="config/categories.json")
        result = classifier.classify("I have a problem with my credit card.")
        assert result is not None
        assert result["model_version"] == "fallback_keywords"
