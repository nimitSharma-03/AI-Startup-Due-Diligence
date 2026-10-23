"""Feature engineering used inside the persisted scikit-learn pipeline.

The transformer is fitted on training rows only and pickled together with
the classifier, so serving cannot drift from training: vocabularies,
medians and column order all live inside the saved pipeline.
"""

from __future__ import annotations

import re
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from diligence.ml.schema import MODEL_COLUMNS


def slug(text: str) -> str:
    """Make a stable, column-name-safe token from a category value."""
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


def _market_list(value) -> list[str]:
    if isinstance(value, (list, tuple, np.ndarray)):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    return [part.strip() for part in re.split(r"[,;|]", str(value)) if part.strip()]


class StartupFeatureBuilder(BaseEstimator, TransformerMixin):
    """Turn canonical startup records into a numeric feature matrix.

    Features:
      * ``yc_year`` - batch year (median-imputed).
      * ``session_summer`` / ``session_unknown`` - batch session.
      * ``log_funding`` - log1p of total funding, median-imputed, plus
        ``funding_missing`` so the model can tell "unknown" from "zero".
      * ``city_*`` - one-hot of cities seen at least ``min_city_count`` times,
        with ``city_other`` and ``city_unknown`` buckets.
      * ``market_*`` - multi-hot of market tags seen at least
        ``min_market_count`` times across all market columns.
    """

    def __init__(self, min_city_count: int = 10, min_market_count: int = 10):
        self.min_city_count = min_city_count
        self.min_market_count = min_market_count

    def fit(self, X: pd.DataFrame, y=None):
        frame = self._check(X)
        years = pd.to_numeric(frame["year"], errors="coerce")
        self.year_median_ = float(years.median())
        funding = pd.to_numeric(frame["total_funding"], errors="coerce")
        self.log_funding_median_ = float(np.log1p(funding.dropna()).median())

        city_counts = Counter(str(city).strip().lower() for city in frame["city"].dropna())
        self.cities_ = sorted(city for city, count in city_counts.items() if count >= self.min_city_count)

        market_counts = Counter(
            tag.lower() for markets in frame["markets"] for tag in _market_list(markets)
        )
        self.markets_ = sorted(tag for tag, count in market_counts.items() if count >= self.min_market_count)
        self.feature_names_ = (
            ["yc_year", "session_summer", "session_unknown", "log_funding", "funding_missing"]
            + [f"city_{slug(city)}" for city in self.cities_]
            + ["city_other", "city_unknown"]
            + [f"market_{slug(tag)}" for tag in self.markets_]
        )
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        frame = self._check(X)
        rows = len(frame)
        out = np.zeros((rows, len(self.feature_names_)), dtype=float)

        years = pd.to_numeric(frame["year"], errors="coerce")
        out[:, 0] = years.fillna(self.year_median_).to_numpy()
        session = frame["session"].astype("string").str.lower()
        out[:, 1] = session.eq("summer").fillna(False).to_numpy(dtype=float)
        out[:, 2] = (~session.isin(["summer", "winter"]).fillna(False)).to_numpy(dtype=float)

        funding = pd.to_numeric(frame["total_funding"], errors="coerce")
        out[:, 3] = np.log1p(funding).fillna(self.log_funding_median_).to_numpy()
        out[:, 4] = funding.isna().to_numpy(dtype=float)

        offset = 5
        city_index = {city: offset + i for i, city in enumerate(self.cities_)}
        other_col = offset + len(self.cities_)
        unknown_col = other_col + 1
        market_offset = unknown_col + 1
        market_index = {tag: market_offset + i for i, tag in enumerate(self.markets_)}

        for row, (city, markets) in enumerate(zip(frame["city"], frame["markets"])):
            if city is None or (isinstance(city, float) and np.isnan(city)) or not str(city).strip():
                out[row, unknown_col] = 1.0
            else:
                out[row, city_index.get(str(city).strip().lower(), other_col)] = 1.0
            for tag in _market_list(markets):
                column = market_index.get(tag.lower())
                if column is not None:
                    out[row, column] = 1.0
        return out

    def get_feature_names_out(self, input_features=None) -> np.ndarray:
        return np.asarray(self.feature_names_, dtype=object)

    @staticmethod
    def _check(X) -> pd.DataFrame:
        if not isinstance(X, pd.DataFrame):
            raise TypeError("StartupFeatureBuilder expects a pandas DataFrame")
        missing = [column for column in MODEL_COLUMNS if column not in X.columns]
        if missing:
            raise ValueError(f"Missing model input columns: {', '.join(missing)}")
        return X
