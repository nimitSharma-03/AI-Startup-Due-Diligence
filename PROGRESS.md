# Engineering progress log

Working branch: `claude/relaxed-archimedes-5p9536`. This file records the audit and the
state of the overhaul so work can be resumed.

## Audit of the starting state (commit 83535bc)

Working
- Flask API with `/health`, `/predict`, `/predict/csv`, `/reports/companies`, `/reports/generate`, `/model-info`, `/metrics`.
- Report endpoint already picked an explicit row (not always the first company).
- React/Vite/Tailwind/Recharts frontend with a single dashboard page.

Broken or wrong
- Model trained on identifier columns: `Unnamed: 0` (row index), `Company` name, `Logo`, `Website`,
  CrunchBase/SeedDB profile URLs and free-text `Description`, all label-encoded as integers.
  These features cannot generalise and some leak the outcome (dead companies lose websites/logos).
- Label encoders were fitted on the whole dataset before the train/test split; unseen categories were
  silently mapped to code 0 (which is a real category).
- `metrics.json` class labels are `0/1/2` (encoded), so the UI could not show which class is which.
- The "Exited" class had 0% recall; weighted metrics hid this. No baseline comparison.
- `risk_level` mapped Exited (an acquisition or IPO, a positive outcome) to "Medium risk".
- The PDF generator produced "Strong Buy/Buy/Avoid" recommendations from a 3-class status model,
  plus SWOT text not supported by the data.
- Uploaded files missing model columns were filled with "Not Available"/0 and still scored.
- Frontend hardcoded the production API URL; only `/` and `/about` routes; no explorer, details,
  analytics, upload preview or methodology. The static site had no SPA rewrite.
- `__pycache__/`, `tmp/` (6.7 MB of renders) and `output/` PDFs were committed; requirements listed gunicorn twice.
- `debug=True` in `app.py`; CORS `*`; no tests; no deployment config in the repo.

Dataset facts (data/CleanStartups.csv)
- 617 Y Combinator companies, batches 2005–2014, columns from SeedDB/CrunchBase listings.
- Target `Fate`: Operating 452, Dead 85, Exited 80. Strongly confounded with batch year
  (2014 batch: 107/107 Operating) because younger companies have had less time to exit or fail.
- `TotalFunds` missing for 47 rows and 0 for 253 rows; heavy right tail (max $1.1B).

## Plan and status

1. [ ] Reproducible ML pipeline: sklearn Pipeline with a custom feature builder, leakage-free features,
       stratified hold-out plus repeated CV, baselines, calibration check, permutation importance.
2. [ ] Modular Flask API under `/api`, upload store, analytics, validation, errors, logging.
3. [ ] PDF reports generated per company in memory, factual narratives, disclosures.
4. [ ] React frontend: overview, explorer, detail, predict, upload, analytics, reports, methodology.
5. [ ] Tests: pytest, vitest, Playwright end-to-end.
6. [ ] Docs, cleanup, Dockerfile/render.yaml, deploy to Render, verify.
