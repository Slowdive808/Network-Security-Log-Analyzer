# NetSec Log Analyzer

A full-stack network security log analysis tool. Ingest CSV, JSON, or syslog files, auto-detect anomalies, store findings in SQLite, and explore them through a React dashboard with Matplotlib-generated PDF reports.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                 │
│  React + Recharts  ──  React Router  ──  Vite dev server        │
│  Dashboard │ Upload │ Events │ Anomalies │ Reports               │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP / REST  (proxy: /api → :8000)
┌────────────────────▼────────────────────────────────────────────┐
│                   FastAPI  (uvicorn :8000)                       │
│                                                                  │
│   /api/files        upload, list, delete, stream events         │
│   /api/anomalies    list, filter, mark false-positive           │
│   /api/reports      generate PDF/PNG, download                  │
│   /api/stats        dashboard aggregates                        │
│                                                                  │
│   ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│   │  Parser  │  │   Detector   │  │       Reporter           │ │
│   │  parser  │  │  detector.py │  │     reporter.py          │ │
│   │  .py     │  │              │  │  Matplotlib PdfPages     │ │
│   │  CSV     │  │ BruteForce   │  │  multi-page PDF / PNG    │ │
│   │  JSON    │  │ PortScan     │  └──────────────────────────┘ │
│   │  Syslog  │  │ TrafficSpike │                                │
│   └──────────┘  │ OffHours     │                                │
│                 └──────────────┘                                │
│                                                                  │
│   SQLAlchemy ORM  ──  SQLite  (data/netsec.db)                  │
│   Tables: log_files │ log_events │ anomalies │ reports          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate sample log datasets (optional but recommended)
python generate_sample_data.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Workflow

1. **Upload** — drop a log file on the Upload page (or use a generated sample)
2. **Wait** — the backend parses the file and runs anomaly detection in the background (~2–10 s)
3. **Dashboard** — charts update with event timelines, anomaly types, and top IPs
4. **Events** — filter/paginate every parsed event row
5. **Anomalies** — review flagged incidents; mark false positives
6. **Reports** — generate a multi-page PDF or PNG and download it

---

## Supported Log Formats

| Format  | Auto-detected | Example file             |
|---------|---------------|--------------------------|
| CSV     | ✓             | `auth_logs.csv`          |
| JSON    | ✓             | `mixed_logs.json`        |
| Syslog  | ✓             | `auth_logs.syslog`       |

The parser normalises all formats to a common column schema before detection.

---

## Detection Rules

| Detector       | Trigger                                                     | Default Threshold       |
|----------------|-------------------------------------------------------------|-------------------------|
| Brute Force    | ≥ N failed auth attempts from same IP in a time window      | 5 failures / 5 min      |
| Port Scan      | ≥ N unique destination ports from same IP in a time window  | 15 ports / 2 min        |
| Traffic Spike  | Hourly traffic > N standard deviations above rolling mean   | 3σ                      |
| Off-Hours Login| Successful auth outside configured business hours           | 07:00 – 19:00           |

Thresholds are configurable in `.env` or `app/config.py`.

---

## Sample Datasets

Run `python backend/generate_sample_data.py` to create four files in `backend/data/samples/`:

| File                  | Events   | Injected Patterns                             |
|-----------------------|----------|-----------------------------------------------|
| `auth_logs.csv`       | ~4 100   | Brute-force (80 attempts), 3 off-hours logins |
| `network_logs.csv`    | ~5 200   | Port scan (200 ports), traffic spike          |
| `mixed_logs.json`     | ~3 500   | All patterns, mixed format                    |
| `auth_logs.syslog`    | ~3 060   | Brute-force (60 attempts) in syslog format    |

---

## API Reference

```
GET  /api/health
POST /api/files/upload
GET  /api/files
GET  /api/files/{id}
DEL  /api/files/{id}
GET  /api/files/{id}/events?skip=0&limit=200&status=&event_type=&source_ip=&username=
GET  /api/files/{id}/anomalies
GET  /api/anomalies?severity=&anomaly_type=&false_positive=
PATCH /api/anomalies/{id}      {"false_positive": true, "notes": "..."}
GET  /api/stats
POST /api/reports/{file_id}?report_type=summary|detailed&fmt=pdf|png
GET  /api/reports/{file_id}
GET  /api/reports/{file_id}/{report_id}/download
```

Full interactive docs at `http://localhost:8000/docs` (Swagger UI).

---

## Project Structure

```
NetSecLogAnalyzer/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   ├── config.py        # Settings (thresholds, paths)
│   │   ├── database.py      # SQLAlchemy engine + session
│   │   ├── models.py        # ORM models
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── parser.py        # CSV / JSON / syslog parser
│   │   ├── detector.py      # Anomaly detection engine
│   │   ├── reporter.py      # Matplotlib PDF/PNG report generator
│   │   └── routers/
│   │       ├── files.py     # Upload, list, delete, events
│   │       ├── anomalies.py # Anomaly CRUD
│   │       ├── reports.py   # Report generation + download
│   │       └── stats.py     # Dashboard aggregates
│   ├── data/
│   │   └── samples/         # Generated sample log files
│   ├── uploads/             # Uploaded log files (git-ignored)
│   ├── reports/             # Generated reports (git-ignored)
│   ├── generate_sample_data.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.js    # API fetch wrappers
│   │   ├── components/      # Layout, FileUpload, AnomalyCard
│   │   └── pages/           # Dashboard, Upload, Events, Anomalies, Reports
│   ├── index.html
│   ├── package.json
│   └── vite.config.js       # Dev proxy → :8000
├── .github/
│   └── workflows/ci.yml     # Python lint + tests + Node build
└── README.md
```

---

## Configuration

Copy `.env.example` to `.env` in the `backend/` directory to override defaults:

```env
DATABASE_URL=sqlite:///./data/netsec.db
BRUTE_FORCE_THRESHOLD=5
BRUTE_FORCE_WINDOW_MINUTES=5
PORT_SCAN_THRESHOLD=15
PORT_SCAN_WINDOW_MINUTES=2
TRAFFIC_SPIKE_THRESHOLD=3.0
BUSINESS_HOURS_START=7
BUSINESS_HOURS_END=19
CORS_ORIGINS=["http://localhost:5173"]
```

---

## CI / CD

GitHub Actions runs on every push / PR:

| Job            | What it does                                          |
|----------------|-------------------------------------------------------|
| `backend`      | Install deps, generate sample data, smoke-test import |
| `parser-tests` | Inline unit tests for parser + detectors              |
| `frontend`     | `npm install && npm run build`, upload dist artifact  |

---

## Tech Stack

| Layer       | Technology                                |
|-------------|-------------------------------------------|
| Backend     | Python 3.11, FastAPI, Uvicorn             |
| ORM / DB    | SQLAlchemy 2, SQLite                      |
| Data        | Pandas, NumPy, SciPy                      |
| Reports     | Matplotlib (PdfPages, Agg backend)        |
| Frontend    | React 18, Vite, React Router v6           |
| Charts      | Recharts                                  |
| CI          | GitHub Actions                            |
