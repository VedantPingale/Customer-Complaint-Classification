# Customer Complaint Classification & Prioritization System

A full-stack web application for submitting, classifying, prioritizing, routing, tracking, and resolving customer complaints using NLP and rule-based priority assessment.


## Technology Stack

| Component       | Technology                           |
|-----------------|--------------------------------------|
| Backend API     | Python 3.10+, Flask                  |
| Database        | SQLite (dev), PostgreSQL (prod)       |
| ORM             | SQLAlchemy                           |
| Authentication  | JWT (PyJWT) + bcrypt                 |
| NLP Classifier  | scikit-learn (TF-IDF + Logistic Regression) |
| ML Dataset      | CFPB Consumer Complaint Database     |
| Frontend        | Vanilla HTML/CSS/JavaScript (SPA)    |
| Testing         | pytest                               |


## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings (defaults work for development)
```

### 3. Run the Application

```bash
python run.py
```

The application starts at `http://localhost:5000` with:
- Demo support users auto-created
- Sample complaints auto-generated
- Keyword fallback classifier (works without training)

### 4. Access the Portals

| Portal          | URL                           |
|-----------------|-------------------------------|
| Landing         | http://localhost:5000/         |
| Customer Portal | http://localhost:5000/customer |
| Support Login   | http://localhost:5000/support/login |

### 5. Demo Credentials

| Username | Password       | Role    |
|----------|----------------|---------|
| admin    | admin123dev    | Admin   |
| manager  | manager123dev  | Manager |
| agent1   | agent123dev    | Agent   |
| agent2   | agent123dev    | Agent   |

> **Note**: These are development credentials only. Change them in `.env` for production.

## CFPB Data & Model Training

### Acquire CFPB Data

```bash
# Download the CFPB Consumer Complaint Database (~2GB)
python -m ml.data_pipeline download
```

Data source: [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/)

### Preprocess Data

```bash
# Full dataset
python -m ml.data_pipeline process

# Smaller sample for development
python -m ml.data_pipeline process --sample-size 50000
```

The pipeline:
1. Loads raw CFPB CSV data
2. Filters for rows with complaint narratives
3. Maps CFPB `Product` field to our category taxonomy
4. Creates subcategory labels from `Issue`/`Sub-product`
5. Cleans text (removes redaction markers, special characters)
6. Removes categories with fewer than 100 samples
7. Stratified split into train (70%), validation (15%), test (15%)
8. Saves to `ml/data/processed/`

### Train the Classifier

```bash
python -m ml.train
```

This trains a TF-IDF + Logistic Regression pipeline:
- **Vectorizer**: TF-IDF with 50,000 features, (1,2)-grams, sublinear TF
- **Classifier**: Multinomial Logistic Regression (lbfgs solver)
- Saves model artifacts to `ml/models/`

### Evaluate the Model

```bash
python -m ml.evaluate
```

Produces:
- Overall accuracy, precision, recall, F1
- Per-class metrics
- Confusion matrix
- Confidence threshold analysis
- Results saved to `ml/models/evaluation_results.json`

### Without Training

The application works without a trained model using a **keyword fallback classifier**. This provides basic category detection but with lower confidence scores. The keyword fallback always marks complaints as needing human review.

### Modifying Priority Rules

Edit `config/priority_rules.json`:

```json
{
  "critical_keywords": ["fraud", "unauthorized", ...],
  "high_keywords": ["urgent", "immediately", ...],
  "fraud_weight": 3.0,
  "urgency_weight": 2.0,
  "priority_thresholds": {
    "critical": 5.0,
    "high": 3.0,
    "medium": 1.0,
    "low": -999
  }
}
```

Restart the server after changes.

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=backend --cov=ml -v

# Specific test file
pytest tests/test_priority.py -v

# Specific test
pytest tests/test_api.py::TestCustomerAPI::test_submit_complaint_success -v
```
## License

This project is provided for educational and demonstration purposes.
The CFPB Consumer Complaint Database is public domain.
