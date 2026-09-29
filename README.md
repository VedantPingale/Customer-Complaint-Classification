# Customer Complaint Classification & Prioritization System

A full-stack web application for submitting, classifying, prioritizing, routing, tracking, and resolving customer complaints using NLP and rule-based priority assessment.

## Architecture

```
┌──────────────────────┐     ┌──────────────────────┐
│   Customer Portal    │     │   Support Portal     │
│   /customer/*        │     │   /support/*         │
│                      │     │                      │
│  Submit Complaint    │     │  Dashboard           │
│  Track Complaint     │     │  Complaint Queue     │
│  View Updates        │     │  Complaint Detail    │
│                      │     │  Analytics           │
└──────────┬───────────┘     │  Assignment          │
           │                 │  Resolution          │
           │                 └──────────┬───────────┘
           └──────────┬────────────────┘
                      ▼
           ┌──────────────────────┐
           │     Flask API        │
           │                      │
           │  Authentication      │
           │  Complaint CRUD      │
           │  Classification      │
           │  Priority Engine     │
           │  Analytics           │
           └──────────┬───────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌───────────────┐         ┌───────────────┐
│ NLP Classifier│         │Priority Engine│
│               │         │               │
│ TF-IDF + LR  │         │ Rule-based    │
│ CFPB trained  │         │ Configurable  │
│               │         │ Deterministic │
└───────────────┘         └───────────────┘
```

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

## Directory Structure

```
customer complaint/
├── README.md
├── requirements.txt
├── .env.example              # Environment variable template
├── .env                      # Local environment (not committed)
├── run.py                    # Application entry point
├── config/
│   ├── priority_rules.json   # Configurable priority rules
│   └── categories.json       # Category taxonomy & team mapping
├── backend/
│   ├── app.py                # Flask application factory
│   ├── config.py             # Configuration classes
│   ├── models.py             # SQLAlchemy database models
│   ├── auth.py               # JWT authentication & RBAC
│   ├── routes/
│   │   ├── customer.py       # Customer API endpoints
│   │   ├── support.py        # Support API endpoints
│   │   └── analytics.py      # Analytics API endpoints
│   ├── services/
│   │   ├── classifier.py     # NLP classifier service
│   │   ├── priority_engine.py # Rule-based priority engine
│   │   └── complaint_service.py # Complaint business logic
│   ├── utils/
│   │   ├── reference_generator.py
│   │   └── sanitizer.py
│   └── seed_data.py          # Demo/development data
├── ml/
│   ├── data_pipeline.py      # CFPB data import & preprocessing
│   ├── train.py              # Model training pipeline
│   ├── evaluate.py           # Model evaluation pipeline
│   ├── data/                 # Raw & processed data (not committed)
│   └── models/               # Trained model artifacts
├── frontend/
│   ├── index.html            # SPA shell
│   ├── css/styles.css        # Design system
│   └── js/
│       ├── app.js            # Route registration
│       ├── router.js         # Client-side router
│       ├── api.js            # API client
│       ├── utils.js          # Utility functions
│       ├── customer.js       # Customer portal
│       └── support.js        # Support portal
└── tests/
    ├── conftest.py           # Shared test fixtures
    ├── test_api.py           # API endpoint tests
    ├── test_priority.py      # Priority engine tests
    └── test_classifier.py    # Classifier tests
```

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

## Environment Variables

| Variable               | Default               | Description                    |
|------------------------|-----------------------|--------------------------------|
| `FLASK_ENV`            | `development`         | Environment mode               |
| `SECRET_KEY`           | (dev default)         | Flask secret key               |
| `JWT_SECRET_KEY`       | (dev default)         | JWT signing key                |
| `JWT_EXPIRATION_HOURS` | `8`                   | Token expiration time          |
| `DATABASE_URL`         | `sqlite:///complaints.db` | Database connection string |
| `MODEL_PATH`           | `ml/models/classifier.joblib` | Trained model path      |
| `VECTORIZER_PATH`      | `ml/models/vectorizer.joblib` | Vectorizer path         |
| `CONFIDENCE_THRESHOLD` | `0.60`                | Human review threshold         |
| `CFPB_DATA_PATH`       | `ml/data/cfpb_complaints.csv` | CFPB data path          |

## Database Schema

The database includes these models:

| Model            | Purpose                                       |
|------------------|-----------------------------------------------|
| `Customer`       | Customer records                              |
| `SupportUser`    | Support staff with roles                      |
| `Complaint`      | Core complaint with dual classification fields|
| `Classification` | History of all classifications                |
| `PriorityDecision` | History of all priority calculations       |
| `StatusHistory`  | Audit trail for status changes                |
| `Assignment`     | Assignment history                            |
| `InternalNote`   | Internal notes (never exposed to customers)   |
| `AuditLog`       | General audit log for all changes             |
| `Notification`   | Customer-facing notifications                 |

### Dual Classification/Priority Fields

Each complaint stores both system-generated and manual override values:

```
system_category     ← AI classifier output
manual_category     ← Human override (if any)
current_category    ← Effective value (manual if set, else system)

system_priority     ← Priority engine output
manual_priority     ← Human override (if any)
current_priority    ← Effective value
```

All overrides are auditable via `AuditLog`.

## Priority Engine

Priority is **entirely rule-based** — no ML is used. The engine:

1. Checks for fraud/security keywords (weight: 3.0)
2. Checks for urgency phrases (weight: 2.0)
3. Checks for financial loss indicators (weight: 2.5)
4. Checks for medium-level issue keywords (weight: 1.5)
5. Checks for informational/low-priority language (penalty: -1.5)
6. Adds category weight
7. Resolves conflicts (security signals override informational language)
8. Maps total score to priority level

### Signal Precedence

**Key design decision**: Security and fraud indicators always override informational language. For example:

> "How do I stop someone who has accessed my account immediately?"

This contains "how do i" (informational) but also "someone accessed my account" (security) and "immediately" (urgency). The security signals take precedence, resulting in **HIGH** or **CRITICAL** priority.

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

## Roles & Permissions

| Action               | Admin | Manager | Agent |
|----------------------|-------|---------|-------|
| View all complaints  | ✓     | ✓       | ✗ *   |
| View assigned only   | —     | —       | ✓     |
| Assign complaints    | ✓     | ✓       | ✗     |
| Override priority    | ✓     | ✓       | ✗     |
| Override category    | ✓     | ✓       | ✓     |
| Change status        | ✓     | ✓       | ✓ **  |
| Add notes            | ✓     | ✓       | ✓ **  |
| Resolve complaints   | ✓     | ✓       | ✓ **  |
| Reopen complaints    | ✓     | ✓       | ✗     |
| Manage users         | ✓     | ✗       | ✗     |
| View analytics       | ✓     | ✓       | ✓     |

\* Agents see only their assigned complaints
\** Only for assigned complaints

## API Endpoints

### Customer API

```
POST   /api/customer/complaints           Submit a complaint
GET    /api/customer/complaints/{ref}      Track by reference number
```

### Support API

```
POST   /api/support/login                 Authenticate
GET    /api/support/me                    Current user profile
GET    /api/support/complaints            List complaints (filtered/sorted)
GET    /api/support/complaints/{id}       Complaint details
PATCH  /api/support/complaints/{id}       Update complaint
POST   /api/support/complaints/{id}/notes  Add internal note
POST   /api/support/complaints/{id}/assign Assign complaint
POST   /api/support/complaints/{id}/resolve Resolve complaint
POST   /api/support/complaints/{id}/reopen  Reopen complaint
GET    /api/support/agents                List agents
GET    /api/support/users                 List users (admin)
POST   /api/support/users                 Create user (admin)
```

### Analytics API

```
GET    /api/support/analytics/overview    Dashboard statistics
GET    /api/support/analytics/categories  Category distribution
GET    /api/support/analytics/priorities  Priority distribution
```

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

## Security Considerations

- **JWT authentication** for all support endpoints
- **Role-based access control** enforced at the API level
- **Customer data isolation**: Customer API never exposes internal data
- **Input sanitization**: All user inputs are sanitized
- **Sensitive data masking**: Account/card numbers masked where detected
- **Password hashing**: bcrypt with auto-generated salts
- **Token expiration**: Configurable JWT expiration (default: 8 hours)
- **No stack traces**: Error responses never expose internals

## Deployment

### Production Checklist

1. Set `FLASK_ENV=production`
2. Generate secure random `SECRET_KEY` and `JWT_SECRET_KEY`
3. Use PostgreSQL instead of SQLite: `DATABASE_URL=postgresql://...`
4. Remove demo credentials or disable demo seeding
5. Train the classifier on full CFPB dataset
6. Configure HTTPS (use a reverse proxy like nginx)
7. Set appropriate `JWT_EXPIRATION_HOURS`
8. Review and tighten CORS settings in `app.py`

### Docker (Example)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "run.py"]
```

## Modifying Categories

Edit `config/categories.json` to add/remove/rename categories and subcategories. The category taxonomy maps to CFPB product types. After modifying categories, retrain the classifier to include the new category mappings.

## Known Limitations

- **Email notifications**: Backend is designed to support notifications but no email provider is connected. Add SMTP or a service like SendGrid by extending the notification creation points.
- **Transformer model**: The advanced transformer-based classifier is architecturally supported but not implemented. The TF-IDF + LR baseline is used.
- **Real-time updates**: The frontend polls on page load rather than using WebSockets. Add WebSocket support for real-time dashboard updates.
- **File attachments**: Not implemented. Can be added by extending the Complaint model and adding file upload endpoints.

## License

This project is provided for educational and demonstration purposes.
The CFPB Consumer Complaint Database is public domain.
