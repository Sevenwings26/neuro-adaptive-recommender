# Render Deployment, Cold Start Mitigation & Keep-Alive Guide

This guide addresses **Finding 6** from the Playwright QA walkthrough report:
> **"Slow cold start with no loading feedback (HTTP 503 sat on 'Render - Application loading' for close to 90 seconds before the login page appeared)."**

---

## 1. Why Cold Starts Occur on Render Free Tier

Render's free tier provides a fully-functional container environment for development and testing, but enforces automatic resource conservation:
- **Idle Timeout**: After **15 minutes** without receiving an inbound HTTP request, the container process is placed into a sleep state (`idled`).
- **Cold Boot Latency**: When a new request arrives, Render spins up the container from scratch. This process (allocating compute, pulling image, loading Python runtime, initializing dependencies, and executing database connection checks) takes between **50 to 90 seconds**.
- **Initial 503 Screen**: Render displays a generic *"Render - Application loading"* screen or returns HTTP 503 until the application binds to the `$PORT` and passes health checks.

---

## 2. Ultra-Lightweight Health Check Endpoint

The platform provides a zero-overhead health check endpoint:

```http
GET /health
```

**Response (`200 OK`)**:
```json
{
  "status": "ok",
  "model_loaded": true,
  "model_type": "XGBoost",
  "test_accuracy": 1.0,
  "test_roc_auc": 1.0,
  "feature_cols": [...]
}
```

This endpoint executes in **< 5 milliseconds**, requires no authentication tokens, and avoids heavy database operations.

---

## 3. Keep-Alive Strategy: Automated Pinger (Free Tier)

To completely eliminate the 90-second cold start on Render's free tier, configure an external automated pinger to send an HTTP GET request to `/health` every **10 minutes**.

### Option A: Free Uptime Monitor (Recommended)
1. Create a free account at [UptimeRobot](https://uptimerobot.com/) or [cron-job.org](https://cron-job.org/).
2. Add a new monitor:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `NALR Render Healthcheck`
   - **URL**: `https://neuro-adaptive-recommender-updated-app.onrender.com/health`
   - **Monitoring Interval**: Every `10 minutes` (well within the 15-minute idle threshold).
3. Save the monitor. The instance will now remain continuously awake and serve parent/clinician requests instantaneously.

### Option B: GitHub Actions Scheduled Keep-Alive (Zero Setup)
You can commit a GitHub Actions workflow `.github/workflows/keep_alive.yml`:

```yaml
name: Render Free-Tier Keep-Alive
on:
  schedule:
    # Run every 10 minutes (cron: '*/10 * * * *')
    - cron: '*/10 * * * *'
  workflow_dispatch:

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping Health Endpoint
        run: |
          curl -s -f https://neuro-adaptive-recommender-updated-app.onrender.com/health || echo "Ping failed or waking up"
```

---

## 4. Production Cloud Deployment (Paid Tiers)

For production, clinical, and HIPAA/FERPA-aligned deployments:
1. **Render Starter Web Service ($7/mo)**:
   - Upgrading from Free to Starter tier completely disables spinning down (`Always On: Enabled`).
   - Dedicated CPU & memory; zero cold starts; instantaneous response times.
2. **Docker / Cloud Run / AWS ECS**:
   - Containerized deployment with min-instances set to 1.
