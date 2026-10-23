# Single image: build the React app, then serve it and the Flask API with Gunicorn.

FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    APP_ENV=production \
    PORT=10000
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY app.py ./
COPY diligence/ diligence/
COPY model/ model/
COPY data/CleanStartups.csv data/CleanStartups.csv
COPY --from=frontend /app/frontend/dist frontend/dist
RUN useradd --create-home --uid 10001 appuser && mkdir -p /tmp/matplotlib && chown appuser /tmp/matplotlib
USER appuser
EXPOSE 10000
# One worker keeps uploaded datasets in a single process; threads handle concurrency.
CMD ["sh", "-c", "exec gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 --access-logfile - --error-logfile -"]
