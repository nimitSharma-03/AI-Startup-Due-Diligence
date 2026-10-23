# Deployment

## Architecture on Render

The app runs as **one Docker web service** on Render's free plan:

- **Stage 1** (`node:22-alpine`): `npm ci` and `npm run build`, which produces `frontend/dist`.
- **Stage 2** (`python:3.13-slim`):
  - installs the pinned `requirements.txt`;
  - copies `app.py`, `diligence/`, `model/`, `data/CleanStartups.csv` and the built `frontend/dist`;
  - runs as a non-root user.
- **Start command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`.
  Render injects `PORT`. A single worker keeps the in-memory upload store consistent.
- **Health check**: `GET /api/health`.

Measured locally, with the container limited to Render free-tier resources (512 MB RAM, 0.1 CPU):

- healthy about 8 s after start;
- about 190 MB resident memory;
- a PDF report takes about 10–14 s at 0.1 CPU and under 1 s on a full core.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | set by Render (10000 in the image) | Port Gunicorn binds to |
| `APP_ENV` | `production` | `development` enables CORS for the Vite dev server |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `MAX_UPLOAD_MB` | `5` | Upload size limit |
| `UPLOAD_TTL_SECONDS` | `7200` | Lifetime of uploaded datasets |
| `MAX_UPLOADS` | `20` | Uploaded datasets held at once |
| `CORS_ORIGINS` | empty | Comma-separated origins, only needed for a split deployment |

No secrets are needed.

## Deploying

**With the Blueprint.** In the Render dashboard, choose New → Blueprint and select this repository.
`render.yaml` defines the service: Docker runtime, free plan, `main` branch, health check, environment variables.

**Manually.** Choose New → Web Service, select the repository, and set Runtime to Docker, Branch to
`main`, Dockerfile path to `./Dockerfile` and Health check path to `/api/health`. Each push to `main`
redeploys the service.

## Free-tier behaviour

- The instance sleeps after about 15 minutes without traffic, and the first request after that
  takes up to a minute while it wakes. The frontend shows a "server may be waking up" message on timeouts.
- Uploaded datasets live in memory, so they are lost when the instance sleeps or redeploys. The UI
  then offers to switch back to the reference dataset.

## Updating the model

```bash
.venv/bin/python -m diligence.ml.train     # about 4 minutes; rewrites model/*
.venv/bin/python -m pytest                 # artifacts and API checks
git add model && git commit -m "Retrain model" && git push
```

The pipeline is pickled with scikit-learn 1.9.1. `requirements.txt` pins that version so the
deployed container loads it with the same library, and the service logs a warning if the versions differ.
