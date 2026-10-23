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

1. [x] Reproducible ML pipeline: custom transformer + class-weighted Random Forest + sigmoid calibration,
       stratified hold-out, repeated CV, four baselines, permutation importance, year-confound check.
2. [x] Modular Flask API under `/api`: in-memory upload store, analytics, validation, JSON errors, logging, security headers.
3. [x] Company-specific PDF reports built in memory; deterministic narratives; disclosures. Verified for 4+ companies.
4. [x] React frontend: overview, explorer, detail, predict, upload, model analytics, reports, methodology; responsive.
5. [x] Tests: 50 pytest, 15 Vitest, 11 Playwright end-to-end (local production stack), all passing.
6. [x] Docs, cleanup, Dockerfile, render.yaml, CI.
7. [x] Merged PR #1 into main; created the Render Docker service; verified it live with the E2E suite on GitHub Actions: https://ai-startup-due-diligence-platform-0u70.onrender.com

Notes
- The Docker image was built and run locally under free-tier limits (512 MB, 0.1 CPU): healthy in about 8 s,
  about 190 MB RSS, PDFs in about 10–14 s.
- This sandbox cannot reach *.onrender.com directly. Live verification uses Render logs/events and the
  GitHub Actions workflow (`workflow_dispatch` with `base_url`).
