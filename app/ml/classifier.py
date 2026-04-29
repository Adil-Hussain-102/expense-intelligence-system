# app/ml/classifier.py

import os
import joblib
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report
from app.ml.preprocess import preprocess_series, build_tfidf_vectorizer

MODEL_DIR   = os.path.join(os.path.dirname(__file__), "..", "..", "models")
MODEL_PATH  = os.path.join(MODEL_DIR, "transaction_classifier.joblib")
LABELS_PATH = os.path.join(MODEL_DIR, "category_labels.joblib")


def load_training_data(filepath: str) -> tuple[pd.Series, pd.Series]:
    """Loads labeled training data from CSV."""
    df = pd.read_csv(filepath)

    if "description" not in df.columns or "category" not in df.columns:
        raise ValueError(
            "Training CSV must have 'description' and 'category' columns"
        )

    df = df.dropna(subset=["description", "category"])
    df = df[df["description"].str.strip() != ""]

    print(f"  Loaded {len(df)} training examples")
    print(f"  Categories: {df['category'].nunique()} unique")
    print(f"  Distribution:\n{df['category'].value_counts().to_string()}")

    return df["description"], df["category"]


def build_pipeline() -> Pipeline:
    tfidf = build_tfidf_vectorizer()

    lr = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=42,
        C=5.0,
        solver="lbfgs",
    )

    pipeline = Pipeline([
        ("tfidf", tfidf),
        ("classifier", lr),
    ])

    return pipeline


def train(training_data_path: str, save: bool = True) -> dict:
    """
    Trains the transaction classifier and evaluates performance.
    """
    print(f"\n{'='*50}")
    print("  Training Transaction Classifier")
    print(f"{'='*50}\n")

    # Step 1: Load data
    print("[1/5] Loading training data...")
    X_raw, y = load_training_data(training_data_path)

    # Step 2: Preprocess
    print("\n[2/5] Preprocessing descriptions...")
    X = preprocess_series(X_raw)

    for original, cleaned in zip(X_raw[:3], X[:3]):
        print(f"  '{original}' → '{cleaned}'")

    # Step 3: Train/test split
    print("\n[3/5] Splitting data (80% train, 20% test)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
    print(f"  Training samples: {len(X_train)}")
    print(f"  Testing samples:  {len(X_test)}")

    # Step 4: Train
    print("\n[4/5] Training Random Forest pipeline...")
    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)
    print("  Training complete!")

    # Step 5: Evaluate
    print("\n[5/5] Evaluating performance...")
    y_pred   = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report   = classification_report(y_test, y_pred, zero_division=0)

    print(f"\n  Test Accuracy: {accuracy:.1%}")
    print(f"\n  Classification Report:\n{report}")

    cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring="accuracy")
    print(f"  5-Fold Cross-Validation:")
    print(f"  Scores: {[f'{s:.1%}' for s in cv_scores]}")
    print(f"  Mean: {cv_scores.mean():.1%} ± {cv_scores.std():.1%}")

    # Save model
    if save:
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(pipeline, MODEL_PATH)
        joblib.dump(list(pipeline.classes_), LABELS_PATH)
        print(f"\n  ✓ Model saved: {MODEL_PATH}")

    results = {
        "accuracy":      round(accuracy, 4),
        "cv_mean":       round(cv_scores.mean(), 4),
        "cv_std":        round(cv_scores.std(), 4),
        "report":        report,
        "model_path":    MODEL_PATH,
        "training_size": len(X_train),
        "test_size":     len(X_test),
        "categories":    list(pipeline.classes_),
    }

    print(f"\n{'='*50}")
    print(f"  Training Complete!")
    print(f"  Accuracy: {accuracy:.1%}")
    print(f"  CV Mean:  {cv_scores.mean():.1%}")
    print(f"{'='*50}\n")

    return results


def load_model() -> Pipeline:
    """Loads the saved trained pipeline from disk."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"No trained model found at {MODEL_PATH}.\n"
            f"Run train() first to train and save the model."
        )
    return joblib.load(MODEL_PATH)


def predict_single(description: str, pipeline: Pipeline = None) -> dict:
    """Predicts the category of ONE transaction description."""
    if pipeline is None:
        pipeline = load_model()

    cleaned       = preprocess_series(pd.Series([description]))[0]
    probabilities = pipeline.predict_proba([cleaned])[0]
    categories    = pipeline.classes_

    top_idx    = np.argmax(probabilities)
    predicted  = categories[top_idx]
    confidence = probabilities[top_idx]

    top3_indices = np.argsort(probabilities)[::-1][:3]
    top3 = [
        {
            "category":    categories[i],
            "probability": round(float(probabilities[i]), 4),
        }
        for i in top3_indices
    ]

    return {
        "category":   predicted,
        "confidence": round(float(confidence), 4),
        "top3":       top3,
    }


def predict_batch(descriptions: pd.Series, pipeline: Pipeline = None) -> pd.DataFrame:
    """Predicts categories for MANY transactions at once."""
    if pipeline is None:
        pipeline = load_model()

    cleaned       = preprocess_series(descriptions)
    predictions   = pipeline.predict(cleaned)
    probabilities = pipeline.predict_proba(cleaned)
    confidences   = probabilities.max(axis=1)

    return pd.DataFrame({
        "description":        descriptions.values,
        "predicted_category": predictions,
        "confidence":         np.round(confidences, 4),
    })


def update_transactions_in_db(pipeline: Pipeline = None) -> dict:
    """
    Runs classifier on ALL uncategorized transactions
    and updates their category_id and confidence in the database.
    """
    from app.database.db import get_session
    from app.database.models import Transaction, Category

    if pipeline is None:
        pipeline = load_model()

    session = get_session()
    updated = 0

    try:
        uncategorized = session.query(Transaction).filter(
            Transaction.category_id == None  # noqa
        ).all()

        if not uncategorized:
            print("No uncategorized transactions found.")
            return {"updated": 0}

        print(f"Categorizing {len(uncategorized)} transactions...")

        categories = session.query(Category).all()
        cat_lookup = {c.name: c.id for c in categories}

        descriptions = pd.Series([t.description for t in uncategorized])
        results      = predict_batch(descriptions, pipeline)

        for txn, (_, row) in zip(uncategorized, results.iterrows()):
            predicted_name  = row["predicted_category"]
            category_id     = cat_lookup.get(predicted_name)
            txn.category_id = category_id
            txn.confidence  = float(row["confidence"])
            updated += 1

        session.commit()
        print(f"✓ Updated {updated} transactions with ML predictions")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

    return {"updated": updated}