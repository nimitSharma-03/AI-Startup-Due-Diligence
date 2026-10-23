# Testing

| Layer | Tool | Location | Command |
|---|---|---|---|
| Backend unit and API | pytest | `tests/` | `.venv/bin/python -m pytest` |
| Frontend unit and component | Vitest + Testing Library | `frontend/src/test/` | `cd frontend && npm test` |
| Lint | ESLint | `frontend/` | `cd frontend && npm run lint` |
| End-to-end | Playwright (Chromium) | `frontend/e2e/` | `cd frontend && npm run build && npx playwright test` |

## Backend (`tests/`, 50 tests)

- **Schema parsing**: money formats, years, sessions, market lists; every error collected per field.
- **Column mapping**: reference headers and generic headers; rejection of files with no year column
  and of empty or binary files.
- **Model artifacts**:
  - classes and inputs match the metadata;
  - leaky columns are excluded;
  - saved metrics beat the majority baseline;
  - predictions are deterministic and sum to 1;
  - unseen categories and missing values are handled.
- **Feature builder**: learns vocabularies only from fit data.
- **API**:
  - health, model info, metrics and importance;
  - list, search, filter, sort and pagination, including invalid parameters;
  - facets, detail, 404s, prediction success and 422 field errors;
  - batch JSON and CSV, including formula escaping;
  - the full upload lifecycle (validate → create → list → detail → PDF → analytics → delete → 404);
  - upload rejections (no year column, wrong type, empty file, over the size limit);
  - CSV export and analytics totals.
- **Reports**:
  - PDFs for four different reference companies each contain that company's name;
  - every required section heading is present;
  - there is no "Strong Buy" style language;
  - reports differ between companies.

## Frontend unit tests (`frontend/src/test/`, 15 tests)

- Formatting helpers, base-rate recovery, prediction-form validation and upload file checks.
- Components rendered through the real router:
  - 404 page and direct navigation to the methodology page;
  - prediction form blocking a missing year, submitting valid input and showing server-side field errors;
  - explorer links to detail pages, and search passed to the API.

## End-to-end (`frontend/e2e/`, 11 tests)

The suite starts the production stack (Gunicorn serving the API and the built SPA) unless
`E2E_BASE_URL` is set, in which case it targets that deployment.

1. API health from the same origin.
2. Workflow 1: dashboard shows the real total (617) → explorer → search → detail → download the PDF
   (checks the `%PDF-` header, its size and a company-specific filename). The test fails on any browser console error.
3. Explorer filter (status = Dead → 85), funding sort, filters kept in the URL across refresh.
4. Three different companies (Zencoder, Greplin, Submittable) each download their own PDF.
5. Workflow 2: prediction form validation (missing year, bad amount), then a valid prediction with explanation.
6. The prediction API rejects invalid input with per-field details.
7. Workflow 3: upload a CSV → validation report and row issue → preview → activate → explorer shows
   the 4 uploaded rows → detail → PDF → reports page search → second PDF → switch back to the reference dataset.
8. Upload rejects non-CSV files.
9. Workflow 4: model analytics shows the comparison, confusion matrix, importance and year confound,
   and the balanced accuracy shown matches `/api/model/metrics`.
10. Workflow 5: direct navigation and reload on every route, including 404 and an unknown startup.
11. Mobile (Pixel 7): no horizontal overflow, the drawer navigation works, the detail page fits.

## Continuous integration

`.github/workflows/ci.yml` runs all of the above on every push and pull request. You can also run
it manually from the Actions tab with an optional `base_url` input to point the E2E suite at a
deployed URL.
