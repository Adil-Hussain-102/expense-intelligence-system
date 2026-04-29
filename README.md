# 💰 Expense Intelligence System for SMBs

> An end-to-end AI-powered financial analytics platform that automatically 
> categorizes bank transactions, detects anomalies, and forecasts spending 
> using machine learning.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28-red)
![Tests](https://img.shields.io/badge/Tests-40%20passing-brightgreen)

---

## 🎯 Problem Statement

Small businesses in Pakistan spend hours manually sorting bank statements 
in Excel spreadsheets, with no automated way to:
- Understand where their money is going
- Detect suspicious or fraudulent transactions  
- Forecast future spending to plan budgets

This system solves all three problems using AI and machine learning.

---

## ✨ Features

| Feature | Technology | Description |
|---------|-----------|-------------|
| Auto-categorization | Logistic Regression + TF-IDF | Classifies transactions into 11 categories with confidence scores |
| Anomaly Detection | Z-score + Isolation Forest | Flags suspicious transactions with severity levels |
| Spending Forecast | Linear Regression | Predicts next month's expenses per category |
| Interactive Dashboard | Streamlit + Plotly | 4-page UI with live charts and CSV upload |
| Data Pipeline | pandas + SQLAlchemy | Handles messy real-world bank CSV exports |
| Database | PostgreSQL | Stores all data with proper relationships |

---

## 🏗️ System Architecture

---

## 📁 Project Structure


---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/expense-intelligence-system.git
cd expense-intelligence-system

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure database
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### Database Setup

```bash
# Create tables and seed sample data
python run.py setup-db
python run.py seed
```

### Train the ML Model

```bash
python -c "from app.ml.classifier import train; train('data/training_labels.csv')"
```

### Run the Dashboard

```bash
python run_dashboard.py
# Opens at http://localhost:8501
```

### Run Tests

```bash
pytest tests/ -v
# 40 tests should pass
```

---

## 📊 Dashboard Pages

**1. Upload** — Upload any bank CSV → full AI pipeline runs automatically
**2. Dashboard** — Spending by category, monthly trends, key metrics  
**3. Anomalies** — Flagged transactions with severity badges and reasons  
**4. Forecast** — Next month's predicted spending per category  

---

## 🤖 ML Pipeline Details

### Transaction Categorization
- **Algorithm:** Logistic Regression with TF-IDF vectorization
- **Features:** TF-IDF vectors from transaction descriptions (unigrams + bigrams + trigrams)
- **Training data:** 215+ labeled Pakistani bank transactions
- **Accuracy:** 81.4% on held-out test set
- **Categories:** Food & Dining, Transport, Utilities, Rent & Housing, Shopping, Healthcare, Entertainment, Education, Salary & Income, Transfer, Other

### Anomaly Detection
- **Method 1:** Z-score per category (threshold: 2.5 std deviations)
- **Method 2:** Isolation Forest (contamination: 5%)
- **Severity levels:** Low, Medium, High
- **Confirmed anomaly:** Both methods agree → automatically upgraded to High

### Spending Forecast
- **Algorithm:** Linear Regression per category
- **Input:** Historical monthly spending data
- **Output:** Next month prediction + trend direction
- **Metric:** R² score reported per category

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| Database | PostgreSQL 16 + SQLAlchemy ORM |
| ML | scikit-learn (Logistic Regression, Isolation Forest, Linear Regression) |
| NLP | TF-IDF Vectorizer |
| Data | pandas, numpy, scipy |
| Dashboard | Streamlit |
| Charts | Plotly |
| Testing | pytest (40 tests) |
| Config | python-dotenv |

---

## 📈 Results

- **300+ transactions** processed in under 3 seconds
- **81.4% ML accuracy** on transaction categorization
- **Anomalies detected** with Low/Medium/High severity ratings
- **9 categories forecast** for next month with trend analysis
- **40 unit tests** passing with full module coverage

---


## 👨‍💻 Author

**Adil Hussain**  
BS Artificial Intelligence
Aror University of Art, Architecture, Design, and Heritage, Sukkur  
Pakistan

[![GitHub](https://img.shields.io/badge/GitHub-Adil--Hussain--102-black)](https://github.com/Adil-Hussain-102)

---

## 📄 License

MIT License — free to use and modify with attribution.