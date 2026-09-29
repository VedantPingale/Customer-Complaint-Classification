"""Model Training Pipeline.

Trains a TF-IDF + Logistic Regression classifier on preprocessed CFPB data.

The training pipeline:
1. Loads preprocessed train/val data
2. Builds a TF-IDF vectorizer
3. Trains a Logistic Regression classifier for category prediction
4. Optionally trains a subcategory classifier
5. Saves the trained model, vectorizer, and label encoders
6. Records model metadata (version, training date, performance)
"""

import os
import json
import logging
import datetime
import numpy as np
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, classification_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "processed")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


def load_training_data(data_dir=None):
    """Load preprocessed training and validation data.

    Returns:
        train_df, val_df
    """
    data_dir = data_dir or DATA_DIR

    train_path = os.path.join(data_dir, "train.csv")
    val_path = os.path.join(data_dir, "val.csv")

    if not os.path.exists(train_path):
        raise FileNotFoundError(
            f"Training data not found at {train_path}. "
            f"Run 'python -m ml.data_pipeline process' first."
        )

    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path) if os.path.exists(val_path) else None

    logger.info("Loaded training data: %d samples", len(train_df))
    if val_df is not None:
        logger.info("Loaded validation data: %d samples", len(val_df))

    return train_df, val_df


def build_vectorizer(texts, max_features=50000, ngram_range=(1, 2)):
    """Build and fit a TF-IDF vectorizer.

    Args:
        texts: Series or list of text documents
        max_features: Maximum number of features
        ngram_range: N-gram range for feature extraction

    Returns:
        Fitted TfidfVectorizer
    """
    logger.info("Building TF-IDF vectorizer (max_features=%d, ngrams=%s)...",
                max_features, ngram_range)

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        strip_accents="unicode",
        lowercase=True,
        stop_words="english",
        min_df=3,
        max_df=0.95,
        sublinear_tf=True,
    )

    vectorizer.fit(texts)
    logger.info("Vectorizer built with %d features", len(vectorizer.vocabulary_))

    return vectorizer


def train_category_classifier(X_train, y_train, X_val=None, y_val=None):
    """Train a Logistic Regression classifier for category prediction.

    Args:
        X_train: TF-IDF features for training
        y_train: Encoded category labels for training
        X_val: TF-IDF features for validation
        y_val: Encoded category labels for validation

    Returns:
        Trained LogisticRegression model
    """
    logger.info("Training category classifier...")

    model = LogisticRegression(
        C=1.0,
        max_iter=1000,
        solver="lbfgs",
        n_jobs=-1,
        random_state=42,
    )

    model.fit(X_train, y_train)

    # Training accuracy
    train_pred = model.predict(X_train)
    train_acc = accuracy_score(y_train, train_pred)
    train_f1 = f1_score(y_train, train_pred, average="weighted")
    logger.info("Training accuracy: %.4f, F1: %.4f", train_acc, train_f1)

    # Validation accuracy
    if X_val is not None and y_val is not None:
        val_pred = model.predict(X_val)
        val_acc = accuracy_score(y_val, val_pred)
        val_f1 = f1_score(y_val, val_pred, average="weighted")
        logger.info("Validation accuracy: %.4f, F1: %.4f", val_acc, val_f1)

    return model


def train_subcategory_classifier(X_train, y_train_sub):
    """Train a subcategory classifier (optional, simpler model).

    Args:
        X_train: TF-IDF features
        y_train_sub: Encoded subcategory labels

    Returns:
        Trained model and label encoder, or (None, None) if too few classes
    """
    # Filter out very rare subcategories
    unique_subs = np.unique(y_train_sub)
    if len(unique_subs) < 2:
        logger.warning("Too few subcategory classes, skipping subcategory training")
        return None, None

    logger.info("Training subcategory classifier (%d classes)...", len(unique_subs))

    model = LogisticRegression(
        C=0.5,
        max_iter=500,
        solver="lbfgs",
        n_jobs=-1,
        random_state=42,
    )

    try:
        model.fit(X_train, y_train_sub)
        train_pred = model.predict(X_train)
        train_acc = accuracy_score(y_train_sub, train_pred)
        logger.info("Subcategory training accuracy: %.4f", train_acc)
        return model, None
    except Exception as e:
        logger.warning("Subcategory training failed: %s", e)
        return None, None


def save_model(model, vectorizer, label_encoder, model_dir=None,
               subcategory_model=None, subcategory_encoder=None,
               metrics=None):
    """Save trained model artifacts to disk.

    Saves:
    - classifier.joblib: The trained Logistic Regression model
    - vectorizer.joblib: The fitted TF-IDF vectorizer
    - label_encoder.joblib: The category label encoder
    - subcategory_classifier.joblib: Optional subcategory model
    - subcategory_label_encoder.joblib: Optional subcategory encoder
    - model_metadata.json: Version, training info, and metrics
    """
    model_dir = model_dir or MODEL_DIR
    os.makedirs(model_dir, exist_ok=True)

    joblib.dump(model, os.path.join(model_dir, "classifier.joblib"))
    joblib.dump(vectorizer, os.path.join(model_dir, "vectorizer.joblib"))
    joblib.dump(label_encoder, os.path.join(model_dir, "label_encoder.joblib"))

    if subcategory_model is not None:
        joblib.dump(subcategory_model, os.path.join(model_dir, "subcategory_classifier.joblib"))
    if subcategory_encoder is not None:
        joblib.dump(subcategory_encoder, os.path.join(model_dir, "subcategory_label_encoder.joblib"))

    # Save metadata
    now = datetime.datetime.now(datetime.timezone.utc)
    version = f"tfidf_lr_v1_{now.strftime('%Y%m%d_%H%M%S')}"

    metadata = {
        "version": version,
        "model_type": "tfidf_logistic_regression",
        "trained_at": now.isoformat(),
        "num_categories": len(label_encoder.classes_),
        "categories": label_encoder.classes_.tolist(),
        "vectorizer_features": len(vectorizer.vocabulary_),
        "metrics": metrics or {},
    }

    with open(os.path.join(model_dir, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Model saved to %s (version: %s)", model_dir, version)


def train(data_dir=None, model_dir=None, train_subcategory=True):
    """Run the complete training pipeline.

    Args:
        data_dir: Directory containing preprocessed data
        model_dir: Directory to save model artifacts
        train_subcategory: Whether to train subcategory classifier

    Returns:
        dict with training metrics
    """
    logger.info("=" * 60)
    logger.info("Model Training Pipeline")
    logger.info("=" * 60)

    # Load data
    train_df, val_df = load_training_data(data_dir)

    # Encode labels
    label_encoder = LabelEncoder()
    y_train = label_encoder.fit_transform(train_df["category"])
    y_val = label_encoder.transform(val_df["category"]) if val_df is not None else None

    logger.info("Categories: %s", list(label_encoder.classes_))

    # Build vectorizer
    vectorizer = build_vectorizer(train_df["text"])

    # Transform text
    X_train = vectorizer.transform(train_df["text"])
    X_val = vectorizer.transform(val_df["text"]) if val_df is not None else None

    # Train category classifier
    model = train_category_classifier(X_train, y_train, X_val, y_val)

    # Calculate metrics
    metrics = {}
    if X_val is not None and y_val is not None:
        val_pred = model.predict(X_val)
        metrics["val_accuracy"] = float(accuracy_score(y_val, val_pred))
        metrics["val_f1_weighted"] = float(f1_score(y_val, val_pred, average="weighted"))
        metrics["val_f1_macro"] = float(f1_score(y_val, val_pred, average="macro"))

        report = classification_report(
            y_val, val_pred,
            target_names=label_encoder.classes_,
            output_dict=True
        )
        metrics["per_class"] = {
            cls: {
                "precision": round(report[cls]["precision"], 4),
                "recall": round(report[cls]["recall"], 4),
                "f1": round(report[cls]["f1-score"], 4),
                "support": int(report[cls]["support"]),
            }
            for cls in label_encoder.classes_
        }

    # Train subcategory classifier (optional)
    subcategory_model = None
    subcategory_encoder = None
    if train_subcategory:
        subcategory_encoder = LabelEncoder()
        # Handle NaN subcategories
        train_df["subcategory"] = train_df["subcategory"].fillna("General")
        y_train_sub = subcategory_encoder.fit_transform(train_df["subcategory"])
        subcategory_model, _ = train_subcategory_classifier(X_train, y_train_sub)
        if subcategory_model is not None:
            subcategory_encoder_to_save = subcategory_encoder
        else:
            subcategory_encoder_to_save = None
    else:
        subcategory_encoder_to_save = None

    # Save model
    save_model(
        model, vectorizer, label_encoder,
        model_dir=model_dir,
        subcategory_model=subcategory_model,
        subcategory_encoder=subcategory_encoder_to_save,
        metrics=metrics,
    )

    logger.info("=" * 60)
    logger.info("Training complete!")
    if metrics:
        logger.info("Validation accuracy: %.4f", metrics.get("val_accuracy", 0))
        logger.info("Validation F1 (weighted): %.4f", metrics.get("val_f1_weighted", 0))
    logger.info("=" * 60)

    return metrics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train complaint classifier")
    parser.add_argument("--data-dir", default=None, help="Processed data directory")
    parser.add_argument("--model-dir", default=None, help="Model output directory")
    parser.add_argument("--no-subcategory", action="store_true",
                        help="Skip subcategory training")

    args = parser.parse_args()
    train(args.data_dir, args.model_dir, not args.no_subcategory)
