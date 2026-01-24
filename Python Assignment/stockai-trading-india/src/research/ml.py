from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TrainResult:
    model: object
    feature_cols: list[str]
    prob_col: str = "prob_up"


def train_baseline_classifier(
    df: pd.DataFrame,
    feature_cols: list[str],
    label_col: str = "label_up",
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[TrainResult, pd.DataFrame]:
    """
    Time-respecting split (no shuffle): last `test_size` is test.
    Returns (TrainResult, predictions_df) where predictions_df contains prob_up aligned to index.
    """
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be between 0 and 1.")

    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    n = len(df)
    split = int(n * (1.0 - test_size))
    train_df = df.iloc[:split].copy()
    test_df = df.iloc[split:].copy()

    X_train = train_df[feature_cols].values
    y_train = train_df[label_col].values
    X_test = test_df[feature_cols].values

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, random_state=random_state)),
        ]
    )
    model.fit(X_train, y_train)

    prob_up = model.predict_proba(X_test)[:, 1]
    pred = pd.DataFrame(index=test_df.index, data={"prob_up": prob_up, "y_true": test_df[label_col].values})

    return TrainResult(model=model, feature_cols=feature_cols), pred


def predict_proba(model: object, X: np.ndarray) -> np.ndarray:
    return model.predict_proba(X)[:, 1]


def save_model(model: object, path: str) -> None:
    import joblib

    joblib.dump(model, path)


def load_model(path: str) -> object:
    import joblib

    return joblib.load(path)

