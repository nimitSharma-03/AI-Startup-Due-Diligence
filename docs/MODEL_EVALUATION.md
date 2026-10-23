# Model evaluation

All figures below come from `model/metrics.json` and `model/metadata.json`, written by
`python -m diligence.ml.train` (random_state 42, scikit-learn 1.9.1, Python 3.13). Re-running the
script reproduces them exactly.

## Data

`data/CleanStartups.csv`: 617 Y Combinator companies, batches 2005–2014, 24 columns from public
SeedDB/CrunchBase listings.

| Recorded status (`Fate`) | Companies | Share |
|---|---|---|
| Operating | 452 | 73.3% |
| Dead | 85 | 13.8% |
| Exited (acquired / IPO) | 80 | 13.0% |

Data-quality checks: 0 duplicate rows and 0 duplicate company names. 43 companies share identical
model inputs with another company. Total funding is missing for 47 rows and $0 for 253 rows.

**Batch-year confound.** The 2014 batch is 107/107 Operating and the 2013 batch 82/85 Operating.
Young companies had not had time to exit or fail when the listings were collected.

## Target and what the output means

The model predicts the recorded status, a snapshot taken around 2014–2015. It does not forecast a
time horizon or an investment return. The application therefore shows:

- **Calibrated class probabilities** P(Operating), P(Exited), P(Dead).
- **Model-assigned class**: argmax of P(class) / base rate(class). This is the Bayes decision for
  balanced accuracy, so minority outcomes are not hidden by the 73% majority.
- **Failure-pattern signal**: P(Dead) relative to the 13.8% base rate. It is *Lower* below 1×,
  *Moderate* from 1× to 2×, and *Elevated* at 2× or more. This is a ratio to a historical base rate,
  not a calibrated investment-risk probability.

The previous version mapped Exited to "Medium risk". That was wrong: an exit is usually a good
outcome. The mapping has been removed.

## Features

| Input | Engineering |
|---|---|
| Batch year | numeric, median-imputed |
| Batch session | `session_summer`, `session_unknown` |
| Total funding | `log1p`, median-imputed, plus `funding_missing` flag |
| City | one-hot for cities with ≥10 training companies; `city_other`, `city_unknown` |
| Market tags (Market1–5) | multi-hot for tags with ≥10 training companies |

28 engineered features in total. All vocabularies and imputation values are learned on the training
split inside `StartupFeatureBuilder` and saved within the pipeline, so serving cannot drift from training.

**Excluded columns** (they were all used by the previous model):

- **Row index**: correlated with outcome through export order.
- **Company name, description, profile URLs**: identifiers.
- **Logo, Website**: these URLs tend to disappear when a company dies, so they leak the outcome.
- **Founders1–4, Investors1–4**: how complete these listings are depends on documentation after the fact.

## Model selection

- **Split.** Stratified 80/20 train/test split: 493 training rows, 124 test rows (Dead 17, Exited 16, Operating 91).
- **Tuning.** Random Forest with 300 trees and `class_weight='balanced_subsample'`, grid-searched
  over `max_depth ∈ {4, 6, 10, None}` × `min_samples_leaf ∈ {1, 3, 5}`. Scoring was 5-fold CV
  macro one-vs-rest ROC-AUC on the training split. Best: depth 6, min leaf 3 (CV AUC 0.830).
- **Calibration.** Wrapped in `CalibratedClassifierCV(method='sigmoid', cv=5)`, fitted on the
  training split only.

## Results

Each cell shows the repeated stratified CV mean ± sd (5 folds × 3 repeats on the training split),
then the hold-out value on the 124 test companies.

| Model | Decision | Balanced acc. | Macro F1 | Accuracy | ROC-AUC (macro) | Log-loss |
|---|---|---|---|---|---|---|
| Majority class | argmax | 0.333 ± 0.000 / 0.333 | 0.282 / 0.282 | 0.732 / 0.734 | 0.500 / 0.500 | 0.766 / 0.764 |
| Stratified random | argmax | 0.343 ± 0.067 / 0.319 | 0.341 / 0.319 | 0.575 / 0.556 | 0.508 / 0.487 | 5.875 / 6.128 |
| Logistic regression | balanced | 0.608 ± 0.062 / 0.605 | 0.546 / 0.547 | 0.667 / 0.677 | 0.826 / 0.868 | 0.594 / 0.522 |
| Random Forest, uncalibrated | argmax | 0.613 ± 0.069 / 0.756 | 0.569 / 0.671 | 0.702 / 0.758 | 0.824 / 0.876 | 0.749 / 0.715 |
| **Random Forest, calibrated (deployed)** | balanced | **0.607 ± 0.057 / 0.727** | 0.518 / 0.614 | 0.606 / 0.694 | **0.830 ± 0.021 / 0.887** | **0.596 / 0.518** |

How to read this table:

- The forest clearly beats the naive baselines. Balanced accuracy roughly doubles, and AUC rises from 0.50 to about 0.83.
- Calibration keeps the balanced accuracy of the class-weighted forest and markedly improves
  probability quality. CV log-loss falls from 0.749 to 0.596.
- Logistic regression is statistically indistinguishable. With five raw inputs and 617 rows, model
  choice matters much less than the data.
- The hold-out split scores above the CV mean. With only 16–17 minority examples in the test set,
  the CV means are the more reliable estimate.

### Hold-out detail (deployed model)

Confusion matrix (rows = recorded status, columns = assigned class):

| | Dead | Exited | Operating |
|---|---|---|---|
| **Dead** | 14 | 3 | 0 |
| **Exited** | 5 | 11 | 0 |
| **Operating** | 15 | 15 | 61 |

| Class | Precision | Recall | F1 | One-vs-rest AUC |
|---|---|---|---|---|
| Operating | 1.00 | 0.67 | 0.80 | 0.914 |
| Exited | 0.38 | 0.69 | 0.49 | 0.851 |
| Dead | 0.41 | 0.82 | 0.55 | 0.897 |

Macro precision is 0.597, macro recall 0.727, and the multiclass Brier score 0.285. The balanced
rule trades Operating recall for minority recall. Many Operating companies get flagged as exit- or
failure-like, which is acceptable for a screening aid but not for a verdict.

### Global importance (permutation on the hold-out set, Δ log-loss, 30 repeats)

| Input | Mean | SD |
|---|---|---|
| Batch year | 0.2351 | 0.0325 |
| Total funding | 0.0759 | 0.0307 |
| Markets | 0.0294 | 0.0118 |
| City | 0.0030 | 0.0142 |
| Session | −0.0027 | 0.0038 |

### Year-confound sensitivity

The same calibrated forest was re-run under CV with batch year replaced by a constant:

| Metric (CV mean) | With year | Year neutralised |
|---|---|---|
| Balanced accuracy | 0.607 | 0.502 |
| ROC-AUC | 0.830 | 0.691 |
| Log-loss | 0.596 | 0.697 |

Most of the model's skill comes from the timing effect. Funding and markets carry real but modest signal.

## Explanations

- **Global.** Permutation importance of each raw input on the hold-out set. This shows the model's
  reliance on an input, not causation.
- **Per company.** Interventional single-feature attribution. Each input is replaced by its value in
  50 fixed training companies, the rest of the record is held constant, and the change in average
  probability is reported in percentage points. Contributions need not sum to the prediction, and
  they describe model behaviour only. SHAP was not used: the calibrated ensemble is not a single
  tree model, and this method needs no extra dependency.

## Limitations

- One accelerator, one era, 617 companies; findings do not transfer to other populations.
- Funding is cumulative at collection time, so it partly reflects post-batch success (look-ahead).
- Missing city or funding values correlate with failure because of documentation patterns, not location.
- Calibration is fitted on 493 companies; probabilities are approximate.
- No revenue, burn, valuation, team or traction data exists, and none is inferred.
