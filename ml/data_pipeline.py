"""CFPB Data Import and Preprocessing Pipeline.

Downloads and preprocesses the CFPB Consumer Complaint Database for
training the complaint classification model.

Data source: https://www.consumerfinance.gov/data-research/consumer-complaints/
Direct CSV download: https://files.consumerfinance.gov/ccdb/complaints.csv.zip

The pipeline:
1. Downloads or loads the CFPB complaint data
2. Validates required fields
3. Cleans text
4. Handles missing values
5. Prepares training labels (Product → category, Sub-product/Issue → subcategory)
6. Balances classes
7. Splits into train/validation/test sets
8. Saves processed data
"""

import os
import re
import sys
import logging
import zipfile
import requests
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CFPB_URL = "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAW_FILE = os.path.join(DATA_DIR, "cfpb_complaints.csv")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# CFPB Product values that map to our categories
CATEGORY_MAPPING = {
    "Credit reporting, credit repair services, or other personal consumer reports": "Credit reporting, credit repair services, or other personal consumer reports",
    "Credit reporting": "Credit reporting, credit repair services, or other personal consumer reports",
    "Debt collection": "Debt collection",
    "Mortgage": "Mortgage",
    "Credit card or prepaid card": "Credit card or prepaid card",
    "Credit card": "Credit card or prepaid card",
    "Prepaid card": "Credit card or prepaid card",
    "Checking or savings account": "Checking or savings account",
    "Bank account or service": "Checking or savings account",
    "Student loan": "Student loan",
    "Vehicle loan or lease": "Vehicle loan or lease",
    "Consumer Loan": "Vehicle loan or lease",
    "Money transfer, virtual currency, or money service": "Money transfer, virtual currency, or money service",
    "Money transfers": "Money transfer, virtual currency, or money service",
    "Virtual currency": "Money transfer, virtual currency, or money service",
    "Payday loan, title loan, or personal loan": "Payday loan, title loan, or personal loan",
    "Payday loan": "Payday loan, title loan, or personal loan",
    "Title loan": "Payday loan, title loan, or personal loan",
}


def download_cfpb_data(output_path=None):
    """Download the CFPB complaint database.

    Args:
        output_path: Path to save the CSV file. Defaults to DATA_DIR.

    Returns:
        Path to the downloaded CSV file.
    """
    output_path = output_path or RAW_FILE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if os.path.exists(output_path):
        logger.info("CFPB data already exists at %s", output_path)
        return output_path

    logger.info("Downloading CFPB complaint database from %s ...", CFPB_URL)
    logger.info("This file is approximately 2GB and may take several minutes.")

    zip_path = output_path + ".zip"
    try:
        response = requests.get(CFPB_URL, stream=True, timeout=300)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = (downloaded / total_size) * 100
                    print(f"\rDownloading: {pct:.1f}%", end="", flush=True)

        print()
        logger.info("Download complete. Extracting...")

        with zipfile.ZipFile(zip_path, "r") as zf:
            # Find the CSV file in the archive
            csv_files = [f for f in zf.namelist() if f.endswith(".csv")]
            if not csv_files:
                raise ValueError("No CSV file found in the archive")

            zf.extract(csv_files[0], os.path.dirname(output_path))
            extracted = os.path.join(os.path.dirname(output_path), csv_files[0])
            if extracted != output_path:
                os.rename(extracted, output_path)

        os.remove(zip_path)
        logger.info("CFPB data saved to %s", output_path)
        return output_path

    except requests.RequestException as e:
        logger.error("Failed to download CFPB data: %s", e)
        if os.path.exists(zip_path):
            os.remove(zip_path)
        raise


def load_cfpb_data(path=None, sample_size=None):
    """Load CFPB complaint data from CSV.

    Args:
        path: Path to the CSV file
        sample_size: Number of rows to sample (for faster development)

    Returns:
        pandas DataFrame
    """
    path = path or RAW_FILE
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"CFPB data not found at {path}. "
            f"Run 'python -m ml.data_pipeline download' first."
        )

    logger.info("Loading CFPB data from %s ...", path)

    # The CFPB CSV has these relevant columns:
    # - Product: The product category
    # - Sub-product: More specific product type
    # - Issue: The issue type
    # - Sub-issue: More specific issue
    # - Consumer complaint narrative: The complaint text
    # - Company response to consumer
    # - State
    # - Date received

    usecols = [
        "Product", "Sub-product", "Issue", "Sub-issue",
        "Consumer complaint narrative", "Date received",
        "Company", "State",
    ]

    try:
        df = pd.read_csv(path, usecols=usecols, low_memory=False)
    except ValueError:
        # If some columns don't exist, load all and filter
        df = pd.read_csv(path, low_memory=False)
        available = [c for c in usecols if c in df.columns]
        df = df[available]
        
    if "Consumer complaint narrative" not in df.columns:
        logger.warning("Consumer complaint narrative column missing, using Issue as text")
        df["Consumer complaint narrative"] = df["Issue"]

    logger.info("Loaded %d rows", len(df))

    if sample_size and sample_size < len(df):
        df = df.sample(n=sample_size, random_state=42)
        logger.info("Sampled %d rows", len(df))

    return df


def clean_text(text):
    """Clean complaint narrative text."""
    if pd.isna(text) or not isinstance(text, str):
        return ""

    # Remove the CFPB redaction markers
    text = re.sub(r'XX+', '', text)
    text = re.sub(r'XXXX', '', text)

    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?;:\'-]', ' ', text)

    # Trim
    text = text.strip()

    return text


def preprocess_cfpb_data(df):
    """Preprocess the CFPB data for model training.

    Steps:
    1. Filter to rows with complaint narratives
    2. Map product names to our category taxonomy
    3. Clean text
    4. Handle missing values
    5. Create category and subcategory labels

    Args:
        df: Raw CFPB DataFrame

    Returns:
        Preprocessed DataFrame with columns: text, category, subcategory
    """
    logger.info("Preprocessing CFPB data...")

    # Step 1: Filter to rows with narratives
    narrative_col = "Consumer complaint narrative"
    if narrative_col not in df.columns:
        raise ValueError(f"Column '{narrative_col}' not found in data")

    df = df.dropna(subset=[narrative_col])
    df = df[df[narrative_col].str.strip().str.len() > 20]
    logger.info("After filtering for narratives: %d rows", len(df))

    # Step 2: Map product names to our categories
    df["category"] = df["Product"].map(CATEGORY_MAPPING)
    df = df.dropna(subset=["category"])
    logger.info("After category mapping: %d rows", len(df))

    # Step 3: Create subcategory from Issue or Sub-product
    df["subcategory"] = df["Issue"].fillna(df.get("Sub-product", pd.Series(["General"] * len(df))))
    df["subcategory"] = df["subcategory"].fillna("General")

    # Step 4: Clean text
    df["text"] = df[narrative_col].apply(clean_text)
    df = df[df["text"].str.len() > 20]
    logger.info("After text cleaning: %d rows", len(df))

    # Step 5: Remove rare categories (less than 100 samples)
    category_counts = df["category"].value_counts()
    valid_categories = category_counts[category_counts >= 100].index
    df = df[df["category"].isin(valid_categories)]
    logger.info("Categories with >= 100 samples: %d", len(valid_categories))

    # Step 6: Select final columns
    result = df[["text", "category", "subcategory"]].copy()
    result = result.reset_index(drop=True)

    logger.info("Preprocessing complete: %d rows, %d categories",
                len(result), result["category"].nunique())
    logger.info("Category distribution:\n%s", result["category"].value_counts().to_string())

    return result


def split_data(df, test_size=0.15, val_size=0.15, random_state=42):
    """Split data into train, validation, and test sets.

    Uses stratified splitting to maintain category distribution.

    Args:
        df: Preprocessed DataFrame
        test_size: Fraction for test set
        val_size: Fraction for validation set
        random_state: Random seed for reproducibility

    Returns:
        train_df, val_df, test_df
    """
    logger.info("Splitting data (test=%.0f%%, val=%.0f%%) ...",
                test_size * 100, val_size * 100)

    # First split off test set
    train_val, test = train_test_split(
        df, test_size=test_size, random_state=random_state,
        stratify=df["category"]
    )

    # Then split train_val into train and validation
    adjusted_val_size = val_size / (1 - test_size)
    train, val = train_test_split(
        train_val, test_size=adjusted_val_size, random_state=random_state,
        stratify=train_val["category"]
    )

    logger.info("Split sizes - Train: %d, Validation: %d, Test: %d",
                len(train), len(val), len(test))

    return train, val, test


def save_processed_data(train, val, test, output_dir=None):
    """Save processed data splits to disk."""
    output_dir = output_dir or PROCESSED_DIR
    os.makedirs(output_dir, exist_ok=True)

    train.to_csv(os.path.join(output_dir, "train.csv"), index=False)
    val.to_csv(os.path.join(output_dir, "val.csv"), index=False)
    test.to_csv(os.path.join(output_dir, "test.csv"), index=False)

    # Save metadata
    import json
    metadata = {
        "total_samples": len(train) + len(val) + len(test),
        "train_size": len(train),
        "val_size": len(val),
        "test_size": len(test),
        "num_categories": train["category"].nunique(),
        "categories": sorted(train["category"].unique().tolist()),
        "split_ratios": {"train": 0.70, "val": 0.15, "test": 0.15},
    }
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Processed data saved to %s", output_dir)


def run_pipeline(data_path=None, sample_size=None, output_dir=None):
    """Run the complete data preprocessing pipeline.

    Args:
        data_path: Path to raw CFPB CSV
        sample_size: Number of rows to sample
        output_dir: Output directory for processed data

    Returns:
        tuple of (train_df, val_df, test_df)
    """
    logger.info("=" * 60)
    logger.info("CFPB Data Preprocessing Pipeline")
    logger.info("=" * 60)

    # Load
    df = load_cfpb_data(data_path, sample_size)

    # Preprocess
    processed = preprocess_cfpb_data(df)

    # Split
    train, val, test = split_data(processed)

    # Save
    save_processed_data(train, val, test, output_dir)

    logger.info("=" * 60)
    logger.info("Pipeline complete!")
    logger.info("=" * 60)

    return train, val, test


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CFPB Data Pipeline")
    parser.add_argument("command", choices=["download", "process", "all"],
                        help="Command to run")
    parser.add_argument("--data-path", default=None, help="Path to CFPB CSV")
    parser.add_argument("--sample-size", type=int, default=None,
                        help="Number of samples (for development)")
    parser.add_argument("--output-dir", default=None, help="Output directory")

    args = parser.parse_args()

    if args.command == "download":
        download_cfpb_data(args.data_path)
    elif args.command == "process":
        run_pipeline(args.data_path, args.sample_size, args.output_dir)
    elif args.command == "all":
        download_cfpb_data(args.data_path)
        run_pipeline(args.data_path, args.sample_size, args.output_dir)
