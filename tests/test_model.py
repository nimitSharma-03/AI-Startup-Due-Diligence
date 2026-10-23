import json

import numpy as np
import pandas as pd
import pytest

from diligence.ml.features import StartupFeatureBuilder
from diligence.ml.model import ModelService
from diligence.ml.train import CLASSES, MODEL_DIR, balanced_decision


def test_artifacts_are_consistent(model: ModelService):
    metadata = json.loads((MODEL_DIR / "metadata.json").read_text())
    assert model.classes == CLASSES == metadata["classes"]
    assert metadata["input_columns"] == ["year", "session", "total_funding", "city", "markets"]
    for leaky in ("Company", "Website", "Logo", "Unnamed: 0"):
        assert leaky in metadata["excluded_columns"]
    assert not any(name.startswith(("company", "website", "logo")) for name in metadata["engineered_features"])


def test_saved_metrics_beat_majority_baseline(model: ModelService):
    holdout = model.metrics["holdout_comparison"]
    assert holdout["random_forest_calibrated"]["balanced_accuracy"] > holdout["majority_class"]["balanced_accuracy"] + 0.2
    assert holdout["random_forest_calibrated"]["roc_auc_ovr_macro"] > 0.75
    matrix = np.array(model.metrics["holdout"]["confusion_matrix"]["matrix"])
    assert matrix.sum() == model.metadata["test_rows"]


def test_predictions_are_deterministic_and_valid(model: ModelService):
    inputs = [
        {"year": 2008, "session": "Summer", "total_funding": 0.0, "city": None, "markets": ["Games"]},
        {"year": 2014, "session": "Winter", "total_funding": 5e6, "city": "San Francisco", "markets": ["SaaS"]},
    ]
    first, second = model.predict(inputs), model.predict(inputs)
    assert first == second
    for result in first:
        assert result["predicted_outcome"] in CLASSES
        assert abs(sum(result["probabilities"].values()) - 1) < 1e-3
    # An older, unfunded company without a city should look riskier than a
    # recent, well-funded San Francisco company.
    assert first[0]["probabilities"]["Dead"] > first[1]["probabilities"]["Dead"]
    assert first[0]["failure_signal"]["level"] == "Elevated"


def test_unseen_categories_and_missing_values_are_handled(model: ModelService):
    result = model.predict([
        {"year": 2011, "session": None, "total_funding": None, "city": "Atlantis", "markets": ["Quantum Basket Weaving"]}
    ])[0]
    assert result["predicted_outcome"] in CLASSES


def test_feature_builder_learns_only_from_fit_data():
    frame = pd.DataFrame({
        "year": [2010, 2011, 2012],
        "session": ["Winter", "Summer", None],
        "total_funding": [0, 1e6, None],
        "city": ["A", "A", None],
        "markets": [["x"], ["x", "y"], []],
    })
    builder = StartupFeatureBuilder(min_city_count=2, min_market_count=2).fit(frame)
    assert builder.cities_ == ["a"] and builder.markets_ == ["x"]
    out = builder.transform(frame)
    names = list(builder.get_feature_names_out())
    assert out.shape == (3, len(names))
    assert out[2, names.index("funding_missing")] == 1
    assert out[2, names.index("city_unknown")] == 1
    assert out[2, names.index("session_unknown")] == 1


def test_balanced_decision_prefers_largest_lift():
    priors = np.array([0.1, 0.1, 0.8])
    assert balanced_decision(np.array([[0.2, 0.05, 0.75]]), priors)[0] == 0
    assert balanced_decision(np.array([[0.05, 0.05, 0.9]]), priors)[0] == 2


def test_explanation_covers_every_input(model: ModelService, store):
    record = store.reference.index["3"]
    explanation = model.explain(record["model_input"])
    assert {item["field"] for item in explanation} == {"year", "session", "total_funding", "city", "markets"}
    for item in explanation:
        assert set(item["contributions"]) == set(CLASSES)


@pytest.mark.parametrize("bad", [{"year": 2010}])
def test_feature_builder_rejects_missing_columns(bad):
    with pytest.raises(ValueError):
        StartupFeatureBuilder().fit(pd.DataFrame([bad]))
