# API reference

Base path: `/api`. All JSON responses use one envelope:

```json
{ "data": ... , "meta": { ... } }                       // success
{ "error": { "code": "...", "message": "...", "details": {...}, "request_id": "..." } }   // failure
```

Every response carries an `X-Request-ID` header. Internal exceptions are logged with that id and
returned as a generic `500 internal_error`; stack traces are never sent to clients.

Datasets: endpoints that read startups accept `?dataset=<id>`. Omit it, or pass `reference`, for the
built-in Y Combinator dataset; pass the id returned by `POST /api/datasets` for an upload.

## Health and model

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness: model loaded, training timestamp, reference row count |
| GET | `/api/model` | Model summary, hold-out and CV metrics, inputs, excluded columns, hyperparameters, form schema |
| GET | `/api/model/schema` | Input field specifications used to build the prediction form |
| GET | `/api/model/metrics` | Full `metrics.json`: data quality, CV comparison, hold-out metrics, confusion matrix, ROC curves, reliability bins, year sensitivity |
| GET | `/api/model/feature-importance` | Permutation importance (raw inputs) and impurity importance (engineered features) |

## Prediction

### `POST /api/predict`

```json
{ "data": { "year": 2012, "session": "Winter", "total_funding": "1.5M", "city": "San Francisco", "markets": "SaaS, Analytics" } }
```

- `year` is required (1990 to next year).
- `total_funding` accepts numbers and strings such as `1500000`, `$1.5M` or `750k`.
- `markets` accepts a list or a comma-separated string, with at most 10 tags.

The response contains `prediction`, `explanation`, `insights`, `summary`, `warnings` and
`missing_fields`. The `prediction` object looks like this:

```json
{
  "predicted_outcome": "Operating",
  "predicted_probability": 0.897,
  "most_likely_outcome": "Operating",
  "probabilities": { "Dead": 0.026, "Exited": 0.077, "Operating": 0.897 },
  "lift_vs_base_rate": { "Dead": 0.189, "Exited": 0.593, "Operating": 1.225 },
  "failure_signal": { "level": "Lower", "ratio_to_base_rate": 0.189, "description": "..." }
}
```

Errors:

| Status | Code | When |
|---|---|---|
| 400 | `invalid_json` | The body is not a JSON object |
| 422 | `validation_failed` | One or more fields are invalid; `details` maps each field to its message |

### `POST /api/predict/batch`

Send either `{"records": [...]}` (up to 1000 records) or a multipart CSV in the `file` field.
Add `?format=csv` to download the results as CSV. Invalid rows are returned with their `issues`
and are not scored.

## Datasets (uploads)

| Method | Path | Description |
|---|---|---|
| GET | `/api/datasets` | The reference dataset summary. Uploads are not listed, for privacy |
| POST | `/api/datasets/validate` | Multipart `file` (.csv). Parses, maps columns, scores and returns a report **without storing** it |
| POST | `/api/datasets` | Same as validate, but stores the dataset in memory and returns `201` with its `id` |
| GET | `/api/datasets/{id}` | Dataset summary |
| DELETE | `/api/datasets/{id}` | Remove an upload. The reference dataset cannot be deleted |

The upload report contains `rows`, `scorable_rows`, `rows_with_issues`, `issues`, `columns`
(concept → matched columns, with a level of required, recommended or optional),
`unused_columns`, `warnings` and `preview` (the first 25 scored rows).

Upload rules:

- `.csv` only, 5 MB by default (`413 payload_too_large` above that).
- At most 5,000 rows and 200 columns, with no duplicate headers.
- A year column is required (`422 invalid_dataset` otherwise).
- Uploads expire after 2 hours, and at most 20 are kept.

## Startups

| Method | Path | Description |
|---|---|---|
| GET | `/api/startups` | Search, filter, sort and paginate |
| GET | `/api/startups/facets` | Filter options: industries, cities, statuses, years |
| GET | `/api/startups/{id}` | Full detail: attributes, prediction, out-of-fold estimate, explanation, indicators, summary |
| GET | `/api/startups/{id}/report.pdf` | Company-specific PDF (`?inline=1` to display in the browser instead of downloading) |
| GET | `/api/startups/export.csv` | Filtered list as CSV. Formula-like cells are escaped |

Query parameters for the list and export endpoints:

- `q`: search in name, description or market.
- `industry`, `city`, `status` (recorded), `predicted` (model class) and `signal` (`Lower`, `Moderate` or `Elevated`).
- `year_min`, `year_max`, `funding_min`, `funding_max`.
- `sort`: one of `name`, `year`, `total_funding`, `p_dead`, `p_exited`, `city`, `status`; `order` is `asc` or `desc`.
- `page`, and `page_size` (at most 100).

Invalid parameters return `400 invalid_parameter`.

## Analytics

`GET /api/analytics?dataset=` returns dashboard aggregates computed from the dataset and the model:

- totals
- predicted, failure-signal and recorded-status distributions
- industry and city distributions
- funding statistics and buckets
- year × status counts
- field completeness
- predicted-vs-recorded cross-tab
- the model summary

## Frontend routes

Every non-`/api` GET path is served by `frontend/dist/index.html`, so client-side routes such as
`/startups/3` work on direct navigation and on refresh. Unknown `/api/*` paths return JSON 404s.
