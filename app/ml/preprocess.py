# app/ml/preprocess.py

import re
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "for",
    "ltd", "pvt",
}


def clean_text(text: str) -> str:
    """
    Cleans a single transaction description for ML processing.
    
    Steps:
    1. Lowercase
    2. Remove numbers
    3. Remove special characters
    4. Collapse multiple spaces
    5. Remove stopwords
    6. Strip whitespace
    """
    if not isinstance(text, str):
        return ""

    text = text.lower()
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    words = text.split()
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]

    return " ".join(words).strip()


def preprocess_series(descriptions: pd.Series) -> pd.Series:
    """
    Applies clean_text() to an entire pandas Series at once.
    Used for both training data and new transactions before prediction.
    """
    return descriptions.apply(clean_text)


def build_tfidf_vectorizer() -> TfidfVectorizer:
    """
    Creates and returns a configured TF-IDF vectorizer.
    
    ngram_range=(1,2): uses single words AND two-word pairs
    max_features=3000: keeps only 3000 most important features
    min_df=1: word must appear in at least 1 document
    max_df=0.95: ignore words appearing in 95%+ of documents
    sublinear_tf=True: apply log scaling to term frequency
    """
    return TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=3000,
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
        strip_accents="unicode",
    )