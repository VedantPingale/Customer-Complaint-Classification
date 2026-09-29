"""NLP Complaint Classifier Service.

Uses a TF-IDF + Logistic Regression pipeline trained on CFPB data
to classify complaint text into categories and subcategories.
"""

import os
import re
import logging
import joblib
import json

logger = logging.getLogger(__name__)


class ComplaintClassifier:
    """Complaint classification using a trained TF-IDF + Logistic Regression model."""

    def __init__(self, model_path=None, vectorizer_path=None, categories_path=None):
        self.model = None
        self.vectorizer = None
        self.label_encoder = None
        self.subcategory_model = None
        self.subcategory_label_encoder = None
        self.categories_config = None
        self.model_version = "unknown"
        self._loaded = False

        if categories_path and os.path.exists(categories_path):
            with open(categories_path, "r", encoding="utf-8") as f:
                self.categories_config = json.load(f)

        if model_path and vectorizer_path:
            self.load(model_path, vectorizer_path)

    def load(self, model_path, vectorizer_path):
        """Load the trained model and vectorizer from disk."""
        try:
            model_dir = os.path.dirname(model_path)

            if os.path.exists(model_path) and os.path.exists(vectorizer_path):
                self.model = joblib.load(model_path)
                self.vectorizer = joblib.load(vectorizer_path)

                label_encoder_path = os.path.join(model_dir, "label_encoder.joblib")
                if os.path.exists(label_encoder_path):
                    self.label_encoder = joblib.load(label_encoder_path)

                sub_model_path = os.path.join(model_dir, "subcategory_classifier.joblib")
                sub_encoder_path = os.path.join(model_dir, "subcategory_label_encoder.joblib")
                if os.path.exists(sub_model_path) and os.path.exists(sub_encoder_path):
                    self.subcategory_model = joblib.load(sub_model_path)
                    self.subcategory_label_encoder = joblib.load(sub_encoder_path)

                metadata_path = os.path.join(model_dir, "model_metadata.json")
                if os.path.exists(metadata_path):
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        self.model_version = metadata.get("version", "unknown")

                self._loaded = True
                logger.info("Classifier loaded successfully (version: %s)", self.model_version)
            else:
                logger.warning("Model files not found at %s. Using fallback classifier.", model_path)
                self._loaded = False
        except Exception as e:
            logger.error("Failed to load classifier: %s", str(e))
            self._loaded = False

    @property
    def is_loaded(self):
        """Check if the model is loaded and ready for inference."""
        return self._loaded

    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess complaint text for classification."""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def classify(self, text: str) -> dict:
        """Classify a complaint text into category and subcategory.

        Returns:
            dict with keys: category, subcategory, confidence
        """
        if not text or not text.strip():
            return self._fallback_result()

        if not self._loaded:
            return self._keyword_fallback(text)

        try:
            processed = self.preprocess_text(text)
            features = self.vectorizer.transform([processed])

            # Get category prediction with probability
            probabilities = self.model.predict_proba(features)[0]
            predicted_idx = probabilities.argmax()
            confidence = float(probabilities[predicted_idx])

            if self.label_encoder:
                category = self.label_encoder.inverse_transform([predicted_idx])[0]
            else:
                category = self.model.classes_[predicted_idx]

            # Get subcategory prediction if model is available
            subcategory = None
            if self.subcategory_model and self.subcategory_label_encoder:
                try:
                    sub_pred = self.subcategory_model.predict(features)[0]
                    subcategory = self.subcategory_label_encoder.inverse_transform([sub_pred])[0]
                except Exception:
                    subcategory = self._infer_subcategory(category, text)
            else:
                subcategory = self._infer_subcategory(category, text)

            return {
                "category": category,
                "subcategory": subcategory,
                "confidence": round(confidence, 4),
                "model_version": self.model_version,
            }
        except Exception as e:
            logger.error("Classification error: %s", str(e))
            return self._keyword_fallback(text)

    def _infer_subcategory(self, category: str, text: str) -> str:
        """Infer subcategory using keyword matching when no subcategory model is available."""
        if not self.categories_config:
            return "General"

        text_lower = text.lower()
        categories = self.categories_config.get("categories", [])

        for cat in categories:
            if cat["name"] == category:
                subcategories = cat.get("subcategories", [])
                if not subcategories:
                    return "General"

                # Simple keyword matching for subcategory
                best_sub = subcategories[0]
                best_score = 0
                for sub in subcategories:
                    keywords = sub.lower().split()
                    score = sum(1 for kw in keywords if kw in text_lower)
                    if score > best_score:
                        best_score = score
                        best_sub = sub
                return best_sub

        return "General"

    def _keyword_fallback(self, text: str) -> dict:
        """Fallback classification using keyword matching when model is not available."""
        text_lower = text.lower()

        keyword_map = {
            "Credit reporting, credit repair services, or other personal consumer reports": [
                "credit report", "credit score", "credit bureau", "equifax", "experian",
                "transunion", "credit repair", "identity theft", "credit monitoring"
            ],
            "Debt collection": [
                "debt collector", "collection agency", "debt collection", "collections",
                "owe money", "pay debt", "harassment", "cease and desist"
            ],
            "Mortgage": [
                "mortgage", "home loan", "foreclosure", "escrow", "refinance",
                "loan modification", "property tax", "home equity"
            ],
            "Credit card or prepaid card": [
                "credit card", "prepaid card", "visa", "mastercard", "charge",
                "billing", "statement", "annual fee", "interest rate", "apr"
            ],
            "Checking or savings account": [
                "checking account", "savings account", "bank account", "overdraft",
                "atm", "debit card", "direct deposit", "wire transfer"
            ],
            "Student loan": [
                "student loan", "student debt", "tuition", "financial aid",
                "loan servicer", "forbearance", "deferment", "repayment plan"
            ],
            "Vehicle loan or lease": [
                "car loan", "auto loan", "vehicle loan", "car lease",
                "auto lease", "vehicle lease", "repossession", "car payment"
            ],
            "Money transfer, virtual currency, or money service": [
                "money transfer", "wire transfer", "cryptocurrency", "bitcoin",
                "paypal", "venmo", "zelle", "western union", "money order"
            ],
            "Payday loan, title loan, or personal loan": [
                "payday loan", "title loan", "personal loan", "cash advance",
                "installment loan", "high interest"
            ],
        }

        best_category = "Credit card or prepaid card"  # Default
        best_score = 0

        for category, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_category = category

        confidence = min(0.55, 0.20 + (best_score * 0.10))
        subcategory = self._infer_subcategory(best_category, text)

        return {
            "category": best_category,
            "subcategory": subcategory,
            "confidence": round(confidence, 4),
            "model_version": "fallback_keywords",
        }

    def _fallback_result(self):
        """Return a default result when classification cannot be performed."""
        return {
            "category": "General",
            "subcategory": "General",
            "confidence": 0.0,
            "model_version": "none",
        }


# Singleton instance
_classifier_instance = None


def get_classifier(app_config=None) -> ComplaintClassifier:
    """Get or create the singleton classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        if app_config:
            _classifier_instance = ComplaintClassifier(
                model_path=app_config.get("MODEL_PATH", "ml/models/classifier.joblib"),
                vectorizer_path=app_config.get("VECTORIZER_PATH", "ml/models/vectorizer.joblib"),
                categories_path=app_config.get("CATEGORIES_PATH", "config/categories.json"),
            )
        else:
            _classifier_instance = ComplaintClassifier(
                categories_path="config/categories.json"
            )
    return _classifier_instance


def reset_classifier():
    """Reset the singleton (useful for testing or model reloading)."""
    global _classifier_instance
    _classifier_instance = None
