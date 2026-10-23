# Architecture

```text
                Browser (React SPA)
                       |  same-origin /api/* (Axios)
                       v
   Gunicorn (1 worker, 4 threads) ── Flask app factory: diligence.create_app
     |-- diligence/api.py            REST routes, validation, JSON envelope
     |-- diligence/errors.py         ApiError + handlers (no stack traces to clients)
     |-- diligence/data/ingest.py    CSV parsing, exact header mapping, row validation
     |-- diligence/data/store.py     reference dataset + in-memory uploads (TTL, cap)
     |-- diligence/data/query.py     search / filter / sort / paginate / CSV export
     |-- diligence/analytics.py      dashboard aggregates
     |-- diligence/insights.py       evidence-tagged indicators + deterministic narrative
     |-- diligence/ml/schema.py      canonical input schema shared by training and serving
     |-- diligence/ml/features.py    StartupFeatureBuilder (sklearn transformer)
     |-- diligence/ml/model.py       ModelService: load, predict, explain
     |-- diligence/reports/          ReportLab PDF + Matplotlib charts, built in memory
     `-- static: frontend/dist       SPA with index.html fallback
                       |
                       v
   model/pipeline.joblib  (FeatureBuilder + calibrated Random Forest)
   model/metadata.json, metrics.json, feature_importance.csv,
   impurity_importance.csv, reference_evaluation.csv
   data/CleanStartups.csv (reference dataset)
```

## Key design decisions

**One canonical schema for training and serving.** `diligence/ml/schema.py` parses every record:
the training CSV, form input and uploads. `StartupFeatureBuilder` lives inside the persisted
pipeline, so vocabularies, medians and column order cannot drift between training and inference.
Unseen cities and markets fall into "other" buckets. Missing values are imputed and flagged rather
than rejected; only the batch year is required.

**No fuzzy column matching.** The old code matched headers by substring, which could map, for
example, a "Company Name" column into unrelated concepts. `ingest.map_columns` matches exact
normalised aliases only. It handles numbered columns (`Market1`–`Market5`) and single
comma-separated columns (`Industry`).

**Ephemeral uploads.** Uploaded CSVs are parsed as text, scored, and stored in a process-local
dictionary keyed by a 128-bit random id, with a 2-hour TTL and at most 20 datasets. Nothing is
written to disk, and no user file is ever unpickled. Gunicorn runs a single worker, so every request
sees the same store; four threads handle concurrency. The trade-off is documented: uploads vanish
when the free instance restarts or sleeps.

**Single deployable.** Flask serves the built React app and the API from one origin. This removes
CORS from the production path, avoids the static-site SPA rewrite problem, and fits on one free
Render instance. `VITE_API_BASE_URL` and `CORS_ORIGINS` exist for a split deployment if one is
ever needed.

**Reports in memory.** `build_report` returns PDF bytes that are streamed with
`Content-Disposition: attachment; filename="Due_Diligence_<Company>.pdf"`. The report is built from
the single selected record, so a report can never show another company's data. Narrative text is
deterministic and assembled from structured values. No LLM is involved.

**Evidence tagging.** Every indicator carries `source: dataset | model`. The UI and PDF show this
next to each statement, so dataset facts, descriptive statistics and model estimates stay distinct.

## Security measures

- No secrets are required or committed; `.env` is git-ignored and `.env.example` documents settings.
- Upload limits:
  - Flask's `MAX_CONTENT_LENGTH` caps size (5 MB by default).
  - The extension must be `.csv`.
  - A NUL-byte check rejects binary files.
  - Row, column and duplicate-header limits apply.
- Display names are sanitised, and the file is never saved under them, so there is no path traversal.
  Static file serving uses `send_from_directory` plus an explicit `is_relative_to(dist)` check.
- CSV exports prefix formula-like cells (`=`, `+`, `-`, `@`) with `'` to block spreadsheet formula injection.
- Security headers on every response:
  - `Content-Security-Policy`, with `script-src 'self'` and no inline scripts.
  - `X-Content-Type-Options: nosniff`.
  - `Referrer-Policy`.
  - API responses add `Cache-Control: no-store`.
- CORS is off by default, because the app is same-origin. It is enabled only for configured
  origins, or for the Vite dev server when `APP_ENV=development`.
- Production runs Gunicorn as a non-root user in the container, with Flask debug off.
- External website links in the UI are protocol-checked (http/https only) and opened with `rel="noopener noreferrer nofollow"`.
- The model pickle is a first-party artifact produced by the training script. Its scikit-learn
  version is pinned, and a mismatch is logged at start-up.

There are no user accounts. Uploads are private only through their unguessable id. Adding
authentication would be the next step if persistent, user-owned data were required.
