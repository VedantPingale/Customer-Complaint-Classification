"""Model Evaluation Pipeline.

Evaluates the trained classifier on a held-out test set and produces
comprehensive classification metrics.

Metrics:
- Overall accuracy
- Weighted precision, recall, F1
- Macro precision, recall, F1
- Per-class precision, recall, F1, support
- Confusion matrix
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "processed")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


def load_test_data(data_dir=None):
    """Load the held-out test set."""
    data_dir = data_dir or DATA_DIR
    test_path = os.path.join(data_dir, "test.csv")

    if not os.path.exists(test_path):
        raise FileNotFoundError(
            f"Test data not found at {test_path}. "
            f"Run 'python -m ml.data_pipeline process' first."
        )

    test_df = pd.read_csv(test_path)
    logger.info("Loaded test data: %d samples", len(test_df))
    return test_df


def load_model(model_dir=None):
    """Load the trained model artifacts."""
    model_dir = model_dir or MODEL_DIR

    classifier_path = os.path.join(model_dir, "classifier.joblib")
    vectorizer_path = os.path.join(model_dir, "vectorizer.joblib")
    encoder_path = os.path.join(model_dir, "label_encoder.joblib")

    if not all(os.path.exists(p) for p in [classifier_path, vectorizer_path, encoder_path]):
        raise FileNotFoundError(
            f"Model files not found in {model_dir}. "
            f"Run 'python -m ml.train' first."
        )

    model = joblib.load(classifier_path)
    vectorizer = joblib.load(vectorizer_path)
    label_encoder = joblib.load(encoder_path)

    logger.info("Model loaded from %s", model_dir)
    return model, vectorizer, label_encoder


def evaluate(data_dir=None, model_dir=None, output_dir=None):
    """Run the complete evaluation pipeline.

    Produces:
    - Overall metrics (accuracy, precision, recall, F1)
    - Per-class metrics
    - Confusion matrix
    - Saves results to evaluation_results.json

    Args:
        data_dir: Directory containing test data
        model_dir: Directory containing model artifacts
        output_dir: Directory to save evaluation results

    Returns:
        dict with all evaluation metrics
    """
    logger.info("=" * 60)
    logger.info("Model Evaluation Pipeline")
    logger.info("=" * 60)

    # Load test data
    test_df = load_test_data(data_dir)

    # Load model
    model, vectorizer, label_encoder = load_model(model_dir)

    # Transform test data
    X_test = vectorizer.transform(test_df["text"])
    y_true = label_encoder.transform(test_df["category"])

    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)

    # Overall metrics
    accuracy = accuracy_score(y_true, y_pred)
    precision_w = precision_score(y_true, y_pred, average="weighted", zero_division=0)
    recall_w = recall_score(y_true, y_pred, average="weighted", zero_division=0)
    f1_w = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    precision_m = precision_score(y_true, y_pred, average="macro", zero_division=0)
    recall_m = recall_score(y_true, y_pred, average="macro", zero_division=0)
    f1_m = f1_score(y_true, y_pred, average="macro", zero_division=0)

    logger.info("Overall Metrics:")
    logger.info("  Accuracy:           %.4f", accuracy)
    logger.info("  Precision (weighted): %.4f", precision_w)
    logger.info("  Recall (weighted):    %.4f", recall_w)
    logger.info("  F1 (weighted):        %.4f", f1_w)
    logger.info("  Precision (macro):    %.4f", precision_m)
    logger.info("  Recall (macro):       %.4f", recall_m)
    logger.info("  F1 (macro):           %.4f", f1_m)

    # Per-class metrics
    report = classification_report(
        y_true, y_pred,
        target_names=label_encoder.classes_,
        output_dict=True,
        zero_division=0,
    )

    logger.info("\nPer-Class Report:")
    logger.info(classification_report(
        y_true, y_pred,
        target_names=label_encoder.classes_,
        zero_division=0,
    ))

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)

    logger.info("Confusion Matrix:")
    logger.info(cm)

    # Confidence analysis
    max_proba = y_pred_proba.max(axis=1)
    confidence_bins = {
        "very_high (>0.9)": int((max_proba > 0.9).sum()),
        "high (0.7-0.9)": int(((max_proba > 0.7) & (max_proba <= 0.9)).sum()),
        "medium (0.5-0.7)": int(((max_proba > 0.5) & (max_proba <= 0.7)).sum()),
        "low (<0.5)": int((max_proba <= 0.5).sum()),
    }
    logger.info("\nConfidence Distribution: %s", confidence_bins)

    # Accuracy at different confidence thresholds
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
    threshold_metrics = {}
    for thresh in thresholds:
        mask = max_proba >= thresh
        if mask.sum() > 0:
            acc_at_thresh = accuracy_score(y_true[mask], y_pred[mask])
            coverage = mask.sum() / len(mask)
            threshold_metrics[str(thresh)] = {
                "accuracy": round(float(acc_at_thresh), 4),
                "coverage": round(float(coverage), 4),
                "samples": int(mask.sum()),
            }
            logger.info("  Threshold %.1f: accuracy=%.4f, coverage=%.1f%% (%d samples)",
                        thresh, acc_at_thresh, coverage * 100, mask.sum())

    # Build results dict
    results = {
        "overall": {
            "accuracy": round(float(accuracy), 4),
            "precision_weighted": round(float(precision_w), 4),
            "recall_weighted": round(float(recall_w), 4),
            "f1_weighted": round(float(f1_w), 4),
            "precision_macro": round(float(precision_m), 4),
            "recall_macro": round(float(recall_m), 4),
            "f1_macro": round(float(f1_m), 4),
        },
        "per_class": {
            cls: {
                "precision": round(report[cls]["precision"], 4),
                "recall": round(report[cls]["recall"], 4),
                "f1": round(report[cls]["f1-score"], 4),
                "support": int(report[cls]["support"]),
            }
            for cls in label_encoder.classes_
        },
        "confusion_matrix": cm.tolist(),
        "class_labels": label_encoder.classes_.tolist(),
        "confidence_distribution": confidence_bins,
        "threshold_analysis": threshold_metrics,
        "test_set_size": len(test_df),
        "num_categories": len(label_encoder.classes_),
    }

    # Save results
    output_dir = output_dir or MODEL_DIR
    os.makedirs(output_dir, exist_ok=True)
    results_path = os.path.join(output_dir, "evaluation_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("\nEvaluation results saved to %s", results_path)

    logger.info("=" * 60)
    logger.info("Evaluation complete!")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate complaint classifier")
    parser.add_argument("--data-dir", default=None, help="Test data directory")
    parser.add_argument("--model-dir", default=None, help="Model directory")
    parser.add_argument("--output-dir", default=None, help="Output directory for results")

    args = parser.parse_args()
    evaluate(args.data_dir, args.model_dir, args.output_dir)
